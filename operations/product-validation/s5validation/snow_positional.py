"""Processing-grid geometry for S5-02-05.

OLCI is mandatory for snow production and establishes the processing grid. The
service may replace values on that grid with optional VIIRS values, but that
does not change the grid geometry measured here.
"""
from __future__ import annotations

import io
import json
import os
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Geod

from .downloads import digest, save_json
from .credentials import downloader_credentials
from .positional_accuracy import _cached_scene_dir, _passing_revisions, _safe_part

GEOD = Geod(ellps="WGS84")
STEP = 0.0025
OLCI_RE = re.compile(r"^S3[AB]_OL_2_LFR____\d{8}T\d{6}.*\.zip$")


def _summary(values: np.ndarray, tolerance_m: float | None = None) -> dict:
    values = np.asarray(values, dtype=float)
    if not values.size:
        return {"median": None, "p95": None, "max": None, "below_tolerance_pct": None}
    result = {"median": float(np.median(values)), "p95": float(np.percentile(values, 95)), "max": float(np.max(values))}
    if tolerance_m is not None:
        result["below_tolerance_pct"] = float(np.mean(values < tolerance_m) * 100)
    return result


def _olci_scenes(folder: Path) -> list[Path]:
    scenes = sorted(p for p in folder.glob("*.zip") if OLCI_RE.match(p.name))
    for scene in scenes:
        with zipfile.ZipFile(scene) as archive:
            names = {Path(n).name for n in archive.namelist()}
            if "geo_coordinates.nc" not in names or "lqsf.nc" not in names:
                raise ValueError(f"Mandatory OLCI members missing in {scene.name}")
            if archive.testzip() is not None:
                raise ValueError(f"Corrupt OLCI archive: {scene.name}")
    return scenes


def _download_olci(day: str, folder: Path, settings: dict, config: dict, base: Path) -> list[Path]:
    """Fetch mandatory OLCI LFR archives through the external DCO contract."""
    try:
        import boto3
        from prefect_common.dco_bs3 import get_input
    except ImportError as exc:
        raise RuntimeError("DCO OLCI downloader requires boto3 and prefect_common") from exc
    creds = downloader_credentials(config, base)
    endpoint = settings.get("endpoint_url") or creds.get("DCO_ENDPOINT_URL")
    access, secret = creds.get("DCO_ACCESS_KEY"), creds.get("DCO_SECRET_KEY")
    catalog = settings.get("catalog_path") or os.environ.get("IRIDE_DCO_INPUT_PATH")
    psg_id = settings.get("psg_id") or os.environ.get("IRIDE_DCO_PSG_ID")
    ps_id = settings.get("ps_id") or os.environ.get("IRIDE_DCO_PS_ID")
    if not all((endpoint, access, secret, catalog, psg_id, ps_id)):
        raise RuntimeError("DCO OLCI download is not configured; set catalog_path, psg_id, ps_id and external DCO credentials")
    start, end = f"{day}T00:00:00Z", f"{day}T23:59:59Z"
    assets, seen = [], set()
    for scope in (None, ps_id):
        kwargs = {"activation_catalog_path": catalog.rstrip('/') + '/catalog.json', "psg_id": psg_id,
                  "start_datetime": start, "end_datetime": end}
        if scope:
            kwargs["ps_id"] = scope
        for asset in get_input(**kwargs):
            href = asset.get("href", "")
            name = href.rstrip('/').split('/')[-1]
            if href in seen or not OLCI_RE.match(name):
                continue
            seen.add(href); assets.append((href, name))
    client = boto3.client('s3', aws_access_key_id=access, aws_secret_access_key=secret, endpoint_url=endpoint, verify=False)
    folder.mkdir(parents=True, exist_ok=True); records = []
    for href, name in assets:
        bucket_key = href.removeprefix('s3://').lstrip('/').split('/', 1)
        if len(bucket_key) != 2:
            continue
        target = folder / _safe_part(name); partial = target.with_name(target.name + '.part')
        client.download_file(bucket_key[0], bucket_key[1], str(partial))
        with zipfile.ZipFile(partial) as archive:
            if archive.testzip() is not None:
                partial.unlink(missing_ok=True)
                raise ValueError(f"Corrupt downloaded OLCI archive: {name}")
        partial.replace(target)
        records.append({"name": name, "href": href, "sha256": digest(target), "bytes": target.stat().st_size})
    save_json(folder / 'download_receipt.json', {"product": "S5-02-05", "date": day,
             "retrieved_at": datetime.now(timezone.utc).isoformat(), "assets": records})
    return _olci_scenes(folder)


def _coordinates(scene: Path) -> tuple[np.ndarray, np.ndarray]:
    try:
        import xarray as xr
    except ImportError as exc:
        raise RuntimeError('OLCI positional geometry requires xarray and h5netcdf') from exc
    with zipfile.ZipFile(scene) as archive:
        member = next(n for n in archive.namelist() if Path(n).name == "geo_coordinates.nc")
        with xr.open_dataset(io.BytesIO(archive.read(member)), engine="h5netcdf") as ds:
            return (np.asarray(ds["longitude"].values, dtype=float),
                    np.asarray(ds["latitude"].values, dtype=float))


def run_grid(folder: Path, final_tif: Path, output_dir: Path, sample_limit: int = 5000, tolerance_m: float = 300.0) -> dict:
    """Measure native OLCI coordinate to final-grid-centre distances.

    This measures the official OLCI-grid processing geometry. It does not make
    a sensor-value attribution claim for cells whose value was replaced by
    optional VIIRS data.
    """
    scenes = _olci_scenes(folder)
    if not scenes:
        raise RuntimeError("No mandatory Sentinel-3 OLCI LFR archives found")
    output_dir.mkdir(parents=True, exist_ok=True)
    native_to_final = []
    native_to_written = []
    scene_records = []
    with rasterio.open(final_tif) as final:
        if final.crs is None or final.crs.to_epsg() != 4326:
            raise ValueError("S5-02-05 final raster must be EPSG:4326")
        valid_final = final.read(1, masked=True)
        assessed = int(np.ma.count(valid_final))
        for scene in scenes:
            lon, lat = _coordinates(scene)
            valid = np.isfinite(lon) & np.isfinite(lat)
            valid &= (lon >= final.bounds.left) & (lon <= final.bounds.right)
            valid &= (lat >= final.bounds.bottom) & (lat <= final.bounds.top)
            flat = np.flatnonzero(valid)
            if not flat.size:
                scene_records.append({"archive": str(scene), "sha256": digest(scene), "sampled": 0})
                continue
            stride = max(1, flat.size // sample_limit)
            sampled = flat[::stride]
            x, y = lon.ravel()[sampled], lat.ravel()[sampled]
            col, row = (~final.transform) * (x, y)
            col, row = np.rint(col - 0.5), np.rint(row - 0.5)
            fx, fy = final.transform * (col + 0.5, row + 0.5)
            _, _, distance = GEOD.inv(x, y, fx, fy)
            native_to_final.append(distance)
            xmin, ymax = float(np.nanmin(lon)), float(np.nanmax(lat))
            qcol = np.rint((x - xmin) / STEP)
            qrow = np.rint((ymax - y) / STEP)
            qx = xmin + (qcol + 0.5) * STEP
            qy = ymax - (qrow + 0.5) * STEP
            _, _, written = GEOD.inv(x, y, qx, qy)
            native_to_written.append(written)
            scene_records.append({"archive": str(scene), "sha256": digest(scene),
                                  "native_coordinates_inside_final": int(flat.size), "sampled": int(sampled.size),
                                  "native_to_nearest_final_centre_m": _summary(distance, tolerance_m),
                                  "native_to_nearest_written_tile_centre_m": _summary(written, tolerance_m)})
    if not native_to_final:
        raise RuntimeError("No OLCI native coordinates overlap the final raster")
    result = {"product": "S5-02-05", "grid_status": "MEASURED_LINEAGE", "final_tif": {"path": str(final_tif), "sha256": digest(final_tif)},
              "assessed_final_cells": assessed, "scene_count": len(scenes),
              "sampled_native_coordinates": int(sum(len(x) for x in native_to_final)),
              "tolerance_m": tolerance_m,
              "native_to_nearest_final_centre_m": _summary(np.concatenate(native_to_final), tolerance_m),
              "native_to_nearest_written_tile_centre_m": _summary(np.concatenate(native_to_written), tolerance_m),
              "scenes": scene_records,
              "interpretation": "Matched-date mandatory OLCI swath to final-grid geometry. Optional VIIRS value replacement occurs on the OLCI grid and does not alter this positional geometry measurement; this is not a sensor-value attribution claim."}
    save_json(output_dir / "result.json", result)
    return result


def run_product05_positional(registry, config: dict, base: Path, workdir: Path) -> dict:
    from .report import generate
    generate(registry, config, workdir, "S5-02-05")
    settings = config.get("positional_accuracy", {}).get("S5-02-05", {})
    if not settings.get("enabled", True):
        return {"status": "DISABLED", "dates": []}
    results = []
    for day, revision in sorted(_passing_revisions(workdir, "S5-02-05").items()):
        rows = [r for r in registry.rows("S5-02-05") if r["acquired_at"][:10] == day and r["revision"] == revision]
        if not rows:
            continue
        row = rows[-1]
        folder = _cached_scene_dir(workdir, dict(row))
        evidence_path = workdir / "positional" / "evidence" / f"S5-02-05_{day.replace('-', '')}_Whole_AOI.json"
        try:
            scenes = _olci_scenes(folder)
            if not scenes and settings.get("download", True):
                scenes = _download_olci(day, folder, settings, config, base)
            tolerance_m = float(settings["tolerance_m"])
            result = run_grid(folder, Path(row["uri"]), workdir / "positional" / "results" / "S5-02-05" / day / revision, tolerance_m=tolerance_m)
            evidence = {"product": "S5-02-05", "date": day, "area": "Whole AOI", "revision": revision,
                        "kpi_status": "OFFICIAL", "status": "MEASURED_LINEAGE", "quantity": "native_OLCI_to_final_grid_centre_m",
                        "max_m": result["native_to_nearest_final_centre_m"]["max"], "assessed_cells": result["assessed_final_cells"],
                        "tolerance_m": tolerance_m,
                        "conforming_fraction": result["native_to_nearest_final_centre_m"]["below_tolerance_pct"] / 100,
                        "centre_distance": result["native_to_nearest_final_centre_m"],
                        "mandatory_input_checksums": result["scenes"], "final_sha256": result["final_tif"]["sha256"],
                        "artifacts": [str((workdir / "positional" / "results" / "S5-02-05" / day / revision / "result.json").resolve())],
                        "campaign_sample_counted": False, "interpretation": result["interpretation"]}
            save_json(evidence_path, evidence)
            results.append({"date": day, "status": "MEASURED_LINEAGE", "assessed_cells": result["assessed_final_cells"]})
        except Exception as exc:
            save_json(evidence_path, {"product": "S5-02-05", "date": day, "area": "Whole AOI", "revision": revision,
                                      "kpi_status": "DIAGNOSTIC", "status": "UNASSESSED", "quantity": "not measured",
                                      "max_m": None, "assessed_cells": 0, "reason": str(exc), "campaign_sample_counted": False})
            results.append({"date": day, "status": "UNASSESSED", "reason": str(exc)})
    save_json(workdir / "inventory" / "positional_accuracy_S5-02-05.json", {"product": "S5-02-05", "results": results})
    return {"status": "COMPLETED", "dates": results}

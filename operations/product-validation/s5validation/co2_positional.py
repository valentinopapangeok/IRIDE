"""Official processing-grid positional KPI for S5-02-08 carbon dioxide."""
from __future__ import annotations

import calendar
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from pyproj import Geod

from .credentials import downloader_credentials
from .downloads import digest, save_json
from .positional_accuracy import _safe_part

GEOD = Geod(ellps="WGS84")


def _summary(values: np.ndarray, tolerance_m: float, target_pct: float) -> dict:
    values = np.asarray(values, dtype=float)
    pct = float(np.mean(values < tolerance_m) * 100)
    return {"median_m": float(np.median(values)), "p95_m": float(np.percentile(values, 95)),
            "max_m": float(np.max(values)), "below_tolerance_pct": pct,
            "tolerance_m": tolerance_m, "acceptance": "PASS" if pct >= target_pct else "FAIL"}


def _sources(folder: Path) -> dict[str, list[Path]]:
    try:
        import xarray as xr
    except ImportError as exc:
        raise RuntimeError("S5-02-08 positional assessment requires xarray") from exc
    found = {"OCO2": [], "OCO3": []}
    for path in sorted(folder.glob("*.nc4")):
        upper = path.name.upper()
        key = "OCO2" if "OCO2" in upper else "OCO3" if "OCO3" in upper else None
        if not key:
            continue
        with xr.open_dataset(path) as ds:
            if not {"latitude", "longitude", "xco2"} <= set(ds.variables):
                raise ValueError(f"Mandatory CO2 coordinates/observable missing in {path.name}")
        found[key].append(path)
    return found


def _download_from_dco(month: str, folder: Path, settings: dict, config: dict, base: Path) -> dict[str, list[Path]]:
    try:
        import boto3
        from prefect_common.dco_bs3 import get_input
    except ImportError as exc:
        raise RuntimeError("S5-02-08 positional download requires boto3 and prefect_common") from exc
    creds = downloader_credentials(config, base)
    endpoint = settings.get("endpoint_url") or creds.get("DCO_ENDPOINT_URL")
    access, secret = creds.get("DCO_ACCESS_KEY"), creds.get("DCO_SECRET_KEY")
    catalog = settings.get("catalog_path") or os.environ.get("IRIDE_DCO_INPUT_PATH")
    psg_id = settings.get("psg_id") or os.environ.get("IRIDE_DCO_PSG_ID")
    ps_id = settings.get("ps_id") or os.environ.get("IRIDE_DCO_PS_ID")
    if not all((endpoint, access, secret, catalog, psg_id, ps_id)):
        raise RuntimeError("S5-02-08 positional DCO download is not configured; set catalog_path, psg_id, ps_id and external DCO credentials")
    year, month_number = month.split("-"); last_day = calendar.monthrange(int(year), int(month_number))[1]
    assets, seen = [], set()
    for scope in (None, ps_id):
        kwargs = {"activation_catalog_path": catalog.rstrip("/") + "/catalog.json", "psg_id": psg_id,
                  "start_datetime": f"{month}-01T00:00:00Z", "end_datetime": f"{month}-{last_day:02d}T23:59:59Z"}
        if scope: kwargs["ps_id"] = scope
        for asset in get_input(**kwargs):
            href = asset.get("href", ""); name = href.rstrip("/").split("/")[-1]; upper = name.upper()
            if href in seen or not ("OCO2" in upper or "OCO3" in upper) or not name.lower().endswith(".nc4"):
                continue
            seen.add(href); assets.append((href, name))
    if not assets:
        raise RuntimeError(f"No mandatory OCO2/OCO3 assets found for {month}")
    client = boto3.client("s3", aws_access_key_id=access, aws_secret_access_key=secret, endpoint_url=endpoint, verify=False)
    folder.mkdir(parents=True, exist_ok=True)
    for href, name in assets:
        if not re.fullmatch(r"[A-Za-z0-9_.+\-]+", name): raise ValueError(f"Unsafe OCO asset name from DCO: {name!r}")
        parts = href.removeprefix("s3://").lstrip("/").split("/", 1)
        if len(parts) != 2: continue
        target = folder / name; partial = target.with_name(target.name + ".part")
        client.download_file(parts[0], parts[1], str(partial)); partial.replace(target)
    result = _sources(folder)
    if not result["OCO2"] or not result["OCO3"]:
        raise RuntimeError(f"Mandatory OCO2 and OCO3 inputs are required; found OCO2={len(result['OCO2'])}, OCO3={len(result['OCO3'])}")
    save_json(folder / "download_receipt.json", {"product": "S5-02-08", "month": month,
             "assets": [{"name": p.name, "sha256": digest(p)} for group in result.values() for p in group],
             "retrieved_at": datetime.now(timezone.utc).isoformat()})
    return result


def run_grid(folder: Path, final_tif: Path, output_dir: Path, tolerance_m: float = 3500.0,
             target_pct: float = 80.0) -> dict:
    try:
        import rasterio
        import xarray as xr
    except ImportError as exc:
        raise RuntimeError("S5-02-08 positional assessment requires xarray and rasterio") from exc
    sources = _sources(folder)
    if not sources["OCO2"] or not sources["OCO3"]:
        raise RuntimeError("Mandatory OCO2 and OCO3 monthly inputs are required")
    # These are the service's fixed histogram parameters from OCO_preprocessing.py.
    lat_min, lat_max, lon_min, lon_max = 35.0, 50.0, 5.0, 20.0
    lat_resolution = 2250.0 / 111320.0
    lon_resolution = 1290.0 / (np.cos(np.deg2rad(lat_max)) * 111320.0)
    n_lat = int((lat_max - lat_min) / lat_resolution)
    n_lon = int((lon_max - lon_min) / lon_resolution)
    lat_edges = np.linspace(lat_min, lat_max, n_lat)
    lon_edges = np.linspace(lon_min, lon_max, n_lon)
    occupied_occurrences = []
    checksums = []
    for group in ("OCO2", "OCO3"):
        for source in sources[group]:
            with xr.open_dataset(source) as ds:
                lat = np.asarray(ds["latitude"].values, dtype=float).ravel()
                lon = np.asarray(ds["longitude"].values, dtype=float).ravel()
                value = np.asarray(ds["xco2"].values, dtype=float).ravel()
            valid = np.isfinite(lat) & np.isfinite(lon) & np.isfinite(value)
            valid &= (lat >= lat_min) & (lat <= lat_max) & (lon >= lon_min) & (lon <= lon_max)
            li = np.searchsorted(lat_edges, lat[valid], side="right") - 1
            lj = np.searchsorted(lon_edges, lon[valid], side="right") - 1
            good = (li >= 0) & (li < n_lat - 1) & (lj >= 0) & (lj < n_lon - 1)
            unique = np.unique(li[good] * (n_lon - 1) + lj[good])
            occupied_occurrences.extend((int(item // (n_lon - 1)), int(item % (n_lon - 1))) for item in unique)
            checksums.append({"name": source.name, "sha256": digest(source), "observations_in_bounds": int(good.sum())})
    if not occupied_occurrences:
        raise RuntimeError("No valid occupied OCO histogram bins overlap the processing domain")
    with rasterio.open(final_tif) as final:
        if str(final.crs) != "EPSG:4326": raise ValueError("S5-02-08 final grid must be EPSG:4326")
        bin_rows, bin_cols = zip(*occupied_occurrences)
        bin_rows, bin_cols = np.asarray(bin_rows), np.asarray(bin_cols)
        # Match OCO_preprocessing.py exactly: np.histogram2d uses linspace
        # edges, but the written GeoTIFF uses the nominal resolution.  This
        # deterministic source-to-intermediate assignment is the retained
        # positional quantity for 08; later smoothing has no contributor map.
        hx = (lon_edges[bin_cols] + lon_edges[bin_cols + 1]) / 2
        hy = (lat_edges[bin_rows] + lat_edges[bin_rows + 1]) / 2
        wx = lon_min + (bin_cols + 0.5) * lon_resolution
        wy = lat_min + (bin_rows + 0.5) * lat_resolution
        _, _, distance = GEOD.inv(hx, hy, wx, wy)
    distance = np.abs(np.asarray(distance, dtype=float))
    result = {"product": "S5-02-08", "status": "MEASURED_LINEAGE", "quantity": "OCO_histogram_bin_to_written_intermediate_cell_centre_distance_m",
              "tolerance_m": tolerance_m, "target_conformity_pct": target_pct, "assessed_cells": int(distance.size),
              "source_to_written_intermediate_centre": _summary(distance, tolerance_m, target_pct), "occupied_bins": int(len(occupied_occurrences)),
              "final_tif": {"path": str(final_tif), "sha256": digest(final_tif)}, "mandatory_inputs": checksums,
              "interpretation": "Official OCO2/OCO3 mandatory-source histogram-bin to producer-written intermediate-cell geometry KPI. The subsequent final mosaic/smoothing does not retain a contributor map; CAMS, PRISMA and GOSAT are not used for this positional percentage.",
              "method_version": "2026-11-17-co2-oco-grid-v1"}
    save_json(output_dir / "result.json", result)
    return result


def _passing_months(workdir: Path) -> dict[str, str]:
    path = workdir / "report" / "kpi_dates.json"
    if not path.exists(): return {}
    selected = {}
    for row in json.loads(path.read_text(encoding="utf-8")):
        if row.get("product") != "S5-02-08" or row.get("passes") is not True: continue
        month = row["date"][:7]; revision = row.get("revision")
        if not revision: raise RuntimeError(f"Thematic KPI row has no delivery revision: S5-02-08 {month}")
        if month in selected and selected[month] != revision: raise RuntimeError(f"Thematic KPI revision is ambiguous for S5-02-08 {month}")
        selected[month] = revision
    return selected


def run_product08_positional(registry, config: dict, base: Path, workdir: Path) -> dict:
    from .report import generate
    generate(registry, config, workdir, "S5-02-08")
    settings = config.get("positional_accuracy", {}).get("S5-02-08", {})
    if not settings.get("enabled", True): return {"status": "DISABLED", "months": []}
    results = []; tolerance = float(settings.get("tolerance_m", 3500.0)); target = float(settings.get("target_conformity_pct", 80.0))
    for month, revision in sorted(_passing_months(workdir).items()):
        rows = [r for r in registry.rows("S5-02-08") if r["acquired_at"][:7] == month and r["revision"] == revision]
        if not rows: continue
        row = rows[-1]; folder = workdir / "positional" / "inputs" / "S5-02-08" / _safe_part(month) / _safe_part(revision)
        evidence_path = workdir / "positional" / "evidence" / f"S5-02-08_{month.replace('-', '')}_Whole_AOI.json"
        try:
            sources = _sources(folder)
            if (not sources["OCO2"] or not sources["OCO3"]) and settings.get("download", True): sources = _download_from_dco(month, folder, settings, config, base)
            result = run_grid(folder, Path(row["uri"]), workdir / "positional" / "results" / "S5-02-08" / month.replace("-", "") / revision, tolerance, target)
            method = result["source_to_written_intermediate_centre"]
            evidence = {"product": "S5-02-08", "date": month + "-01", "area": "Whole AOI", "revision": revision, "kpi_status": "OFFICIAL", "status": "MEASURED_LINEAGE",
                        "quantity": result["quantity"], "tolerance_m": tolerance, "max_m": method["max_m"], "assessed_cells": result["assessed_cells"],
                        "conforming_fraction": method["below_tolerance_pct"] / 100, "centre_distance": method, "footprint_distance": {"below_tolerance_pct": method["below_tolerance_pct"]},
                        "final_sha256": result["final_tif"]["sha256"], "mandatory_input_checksums": result["mandatory_inputs"],
                        "artifacts": [str((workdir / "positional" / "results" / "S5-02-08" / month.replace("-", "") / revision / "result.json").resolve())], "campaign_sample_counted": False,
                        "interpretation": result["interpretation"]}
            save_json(evidence_path, evidence); results.append({"month": month, "status": "MEASURED_LINEAGE", "assessed_cells": result["assessed_cells"], "conforming_fraction": evidence["conforming_fraction"]})
        except Exception as exc:
            save_json(evidence_path, {"product": "S5-02-08", "date": month + "-01", "area": "Whole AOI", "revision": revision, "kpi_status": "OFFICIAL", "status": "UNASSESSED", "quantity": "not measured", "max_m": None, "assessed_cells": 0, "reason": str(exc), "campaign_sample_counted": False})
            results.append({"month": month, "status": "UNASSESSED", "reason": str(exc)})
    save_json(workdir / "inventory" / "positional_accuracy_S5-02-08.json", {"product": "S5-02-08", "results": results})
    return {"status": "COMPLETED", "months": results}

"""Official positional KPI for S5-02-03 hourly solar deliveries.

Product 03 spatially retains the CMSAF/SARAH-3 geographic grid while fusing
time into hourly DNI outputs. This stage measures source-grid to delivered-cell
geometry only; temporal integration and ERA5 reference comparison remain
separate thematic quantities.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Geod

from .credentials import downloader_credentials
from .downloads import digest, save_json

GEOD = Geod(ellps="WGS84")
PREFIX = re.compile(r"^DNIin(?P<day>\d{8})")


def _safe(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", value or ""):
        raise ValueError(f"Unsafe positional path component: {value!r}")
    return value


def _source_folder(workdir: Path, day: str, revision: str) -> Path:
    return workdir / "positional" / "inputs" / "S5-02-03" / _safe(day) / _safe(revision)


def _validate_source(folder: Path, day: str) -> Path | None:
    expected = day.replace("-", "")
    candidates = sorted(p for p in folder.glob(f"DNIin{expected}*.nc") if p.is_file())
    if not candidates:
        return None
    if len(candidates) != 1:
        raise ValueError(f"Ambiguous CMSAF DNI source files in {folder}")
    source = candidates[0]
    receipt = folder / "download_receipt.json"
    if receipt.exists():
        data = json.loads(receipt.read_text(encoding="utf-8"))
        if data.get("sha256") != digest(source):
            raise ValueError(f"CMSAF DNI checksum mismatch: {source.name}")
    return source


def _download_from_dco(day: str, folder: Path, settings: dict, config: dict, base: Path) -> Path:
    try:
        import boto3
        from prefect_common.dco_bs3 import get_input
    except ImportError as exc:
        raise RuntimeError("DCO solar positional downloader requires boto3 and prefect_common") from exc
    creds = downloader_credentials(config, base)
    endpoint = settings.get("endpoint_url") or creds.get("DCO_ENDPOINT_URL")
    access, secret = creds.get("DCO_ACCESS_KEY"), creds.get("DCO_SECRET_KEY")
    catalog = settings.get("catalog_path") or os.environ.get("IRIDE_DCO_INPUT_PATH")
    psg_id = settings.get("psg_id") or os.environ.get("IRIDE_DCO_PSG_ID")
    ps_id = settings.get("ps_id") or os.environ.get("IRIDE_DCO_PS_ID")
    if not all((endpoint, access, secret, catalog, psg_id, ps_id)):
        raise RuntimeError("DCO positional download is not configured; set catalog_path, psg_id, ps_id and external DCO credentials")
    prefix = f"DNIin{day.replace('-', '')}"
    assets, seen = [], set()
    for scope in (None, ps_id):
        kwargs = {"activation_catalog_path": catalog.rstrip("/") + "/catalog.json",
                  "psg_id": psg_id, "start_datetime": f"{day}T00:00:00Z",
                  "end_datetime": f"{day}T23:59:59Z"}
        if scope:
            kwargs["ps_id"] = scope
        for asset in get_input(**kwargs):
            href = asset.get("href", "")
            name = href.rstrip("/").split("/")[-1]
            if href in seen or not name.startswith(prefix) or not name.endswith(".nc"):
                continue
            seen.add(href); assets.append((href, name))
    if len(assets) != 1:
        raise RuntimeError(f"Expected one CMSAF DNI source for {day}, found {len(assets)}")
    href, name = assets[0]
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / _safe(name)
    partial = target.with_name(target.name + ".part")
    bucket_key = href.removeprefix("s3://").lstrip("/").split("/", 1)
    if len(bucket_key) != 2:
        raise ValueError("DCO asset href is not an S3 object")
    client = boto3.client("s3", aws_access_key_id=access, aws_secret_access_key=secret,
                          endpoint_url=endpoint, verify=False)
    client.download_file(bucket_key[0], bucket_key[1], str(partial))
    partial.replace(target)
    save_json(folder / "download_receipt.json", {"product": "S5-02-03", "date": day,
             "name": name, "href": href, "sha256": digest(target),
             "retrieved_at": datetime.now(timezone.utc).isoformat()})
    return target


def run_grid(source: Path, final_tif: Path, output_dir: Path, target_conformity: float = 90.0) -> dict:
    try:
        import xarray as xr
    except ImportError as exc:
        raise RuntimeError("Solar positional assessment requires xarray") from exc
    with xr.open_dataset(source) as dataset, rasterio.open(final_tif) as final:
        if "lon" not in dataset.coords or "lat" not in dataset.coords:
            raise ValueError("CMSAF source lacks geographic lon/lat coordinates")
        lon = np.asarray(dataset["lon"].values, dtype=float)
        lat = np.asarray(dataset["lat"].values, dtype=float)
        if lon.ndim != 1 or lat.ndim != 1 or len(lon) < 2 or len(lat) < 2:
            raise ValueError("CMSAF source grid is not one-dimensional")
        if not np.all(np.diff(lon) > 0) or not np.all(np.diff(lat) > 0):
            raise ValueError("CMSAF source axes are not increasing")
        if str(final.crs) != "EPSG:4326":
            raise ValueError("Product 03 final grid must be EPSG:4326")
        delivered = final.read(1, masked=True)
        valid_mask = np.ma.getmaskarray(delivered)
        rows, cols = np.where(~valid_mask)
        xs, ys = final.transform * (cols + 0.5, rows + 0.5)
        source_cols = np.rint((xs - lon[0]) / np.median(np.diff(lon))).astype(int)
        source_rows = np.rint((ys - lat[0]) / np.median(np.diff(lat))).astype(int)
        inside = ((source_cols >= 0) & (source_cols < len(lon)) &
                  (source_rows >= 0) & (source_rows < len(lat)))
        if not np.all(inside):
            raise ValueError("Final grid extends outside the CMSAF source grid")
        source_x, source_y = lon[source_cols], lat[source_rows]
        _, _, centre = GEOD.inv(xs, ys, source_x, source_y)
        distances = np.abs(np.asarray(centre, dtype=float))
        threshold = 1000.0
        below = int(np.sum(distances < threshold))
        assessed = int(distances.size)
        result = {
            "experiment": "S5-02-03 source-grid to delivered-cell footprint",
            "product": "S5-02-03", "source": source.name,
            "threshold_m": threshold, "target_conformity_pct": target_conformity,
            "final_tif": {"name": final_tif.name, "sha256": digest(final_tif),
                          "crs": str(final.crs), "shape": [final.height, final.width],
                          "transform": list(final.transform)[:6], "valid_pixels": assessed},
            "source_sha256": digest(source), "assessed_cells": assessed,
            "inside_source_grid_cells": int(inside.sum()),
            "methods": {"source_grid_centre": {
                "p50_m": float(np.percentile(distances, 50)),
                "p95_m": float(np.percentile(distances, 95)),
                "max_m": float(np.max(distances)),
                "below_threshold_pct": 100.0 * below / assessed,
                "acceptance": "PASS" if 100.0 * below / assessed >= target_conformity else "FAIL"}},
            "interpretation": "The product retains the CMSAF geographic grid while fusing time. This is spatial processing lineage, not absolute geolocation accuracy and not a measure of the ERA5 thematic reference.",
            "limitations": ["Temporal source lineage is separate from spatial lineage.", "No independent absolute geolocation reference was used."],
            "method_version": "2026-11-16-solar-grid-v1"
        }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def run_product03_positional(registry, config: dict, base: Path, workdir: Path) -> dict:
    from .report import generate
    generate(registry, config, workdir, "S5-02-03")
    hourly_path = workdir / "report" / "hourly_scores.json"
    if not hourly_path.exists():
        return {"status": "COMPLETED", "hours": []}
    settings = config.get("positional_accuracy", {}).get("S5-02-03", {})
    if not settings.get("enabled", True):
        return {"status": "DISABLED", "hours": []}
    target = float(config["products"]["S5-02-03"]["positional_target"].get("percent") or 90)
    selected = [r for r in json.loads(hourly_path.read_text(encoding="utf-8"))
                if r.get("product") == "S5-02-03" and r.get("area") == "Whole AOI" and r.get("passes") is True]
    results = []
    for score in selected:
        hour = score["hour_start_utc"]
        matches = [r for r in registry.rows("S5-02-03")
                   if r["revision"] == score["revision"] and r["acquired_at"][:13] == hour[:13]]
        if len(matches) != 1:
            continue
        row = matches[0]; day = hour[:10]; folder = _source_folder(workdir, day, row["revision"])
        try:
            source = _validate_source(folder, day)
            if source is None and settings.get("download", True):
                source = _download_from_dco(day, folder, settings, config, base)
            if source is None:
                raise RuntimeError("Mandatory CMSAF DNI source is missing and DCO download is unavailable")
            output = workdir / "positional" / "results" / "S5-02-03" / hour[:13].replace(":", "") / row["revision"]
            measured = run_grid(source, Path(row["uri"]), output, target)
            method = measured["methods"]["source_grid_centre"]
            evidence = {"product": "S5-02-03", "date": day, "hour_start_utc": hour,
                        "area": "Whole AOI", "revision": row["revision"],
                        "kpi_status": "OFFICIAL", "status": "MEASURED_LINEAGE",
                        "quantity": "source_grid_to_final_cell_centre_distance_m",
                        "max_m": method["max_m"], "assessed_cells": measured["assessed_cells"],
                        "conforming_fraction": method["below_threshold_pct"] / 100,
                        "centre_distance": {**method, "below_1000_pct": method["below_threshold_pct"]},
                        "footprint_distance": {"below_1000_pct": method["below_threshold_pct"], "inside_footprint_pct": 100.0},
                        "final_sha256": measured["final_tif"]["sha256"], "mandatory_input_checksums": [{"name": source.name, "sha256": measured["source_sha256"]}],
                        "artifacts": [str((output / "result.json").resolve())], "campaign_sample_counted": False,
                        "interpretation": measured["interpretation"]}
            evidence_dir = workdir / "positional" / "evidence"; evidence_dir.mkdir(parents=True, exist_ok=True)
            save_json(evidence_dir / f"S5-02-03_{hour[:13].replace('-', '').replace('T', '').replace(':', '')}_Whole_AOI.json", evidence)
            results.append({"hour_start_utc": hour, "status": "MEASURED_LINEAGE", "assessed_cells": measured["assessed_cells"]})
        except Exception as exc:
            evidence_dir = workdir / "positional" / "evidence"; evidence_dir.mkdir(parents=True, exist_ok=True)
            save_json(evidence_dir / f"S5-02-03_{hour[:13].replace('-', '').replace('T', '').replace(':', '')}_Whole_AOI.json",
                      {"product": "S5-02-03", "date": day, "hour_start_utc": hour,
                       "area": "Whole AOI", "revision": row["revision"], "kpi_status": "OFFICIAL",
                       "status": "UNASSESSED", "quantity": "not measured", "max_m": None,
                       "assessed_cells": 0, "reason": str(exc), "campaign_sample_counted": False})
            results.append({"hour_start_utc": hour, "status": "UNASSESSED", "reason": str(exc)})
    save_json(workdir / "inventory" / "positional_accuracy_S5-02-03.json", {"product": "S5-02-03", "results": results})
    return {"status": "COMPLETED", "hours": results}

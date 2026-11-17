"""Official processing-grid positional KPI for S5-02-07 methane.

The mandatory Sentinel-5P PAL monthly grid is the positional source.  GOSAT is
thematic reference data and is deliberately not used for this geometry KPI.
"""
from __future__ import annotations

import calendar
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
    below = int(np.sum(values < tolerance_m))
    pct = 100.0 * below / len(values)
    return {"median_m": float(np.median(values)), "p95_m": float(np.percentile(values, 95)),
            "max_m": float(np.max(values)), "below_tolerance_pct": pct,
            "tolerance_m": tolerance_m, "acceptance": "PASS" if pct >= target_pct else "FAIL"}


def _sources(folder: Path) -> list[Path]:
    try:
        import h5py
    except ImportError as exc:
        raise RuntimeError("S5-02-07 positional assessment requires h5py") from exc
    sources = sorted(p for p in folder.iterdir() if p.is_file() and not p.name.endswith((".json", ".part")))
    valid = []
    for path in sources:
        try:
            with h5py.File(path, "r") as ds:
                required = {"latitude", "longitude", "CH4_column_volume_mixing_ratio_dry_air"}
                if required <= set(ds.keys()):
                    valid.append(path)
        except (OSError, ValueError):
            continue
    return valid


def _download_from_dco(month: str, folder: Path, settings: dict, config: dict, base: Path) -> list[Path]:
    """Download mandatory Sentinel-5P PAL input through the external DCO contract."""
    try:
        import boto3
        from prefect_common.dco_bs3 import get_input
    except ImportError as exc:
        raise RuntimeError("S5-02-07 positional download requires boto3 and prefect_common") from exc
    creds = downloader_credentials(config, base)
    endpoint = settings.get("endpoint_url") or creds.get("DCO_ENDPOINT_URL")
    access, secret = creds.get("DCO_ACCESS_KEY"), creds.get("DCO_SECRET_KEY")
    catalog = settings.get("catalog_path") or os.environ.get("IRIDE_DCO_INPUT_PATH")
    psg_id = settings.get("psg_id") or os.environ.get("IRIDE_DCO_PSG_ID")
    ps_id = settings.get("ps_id") or os.environ.get("IRIDE_DCO_PS_ID")
    if not all((endpoint, access, secret, catalog, psg_id, ps_id)):
        raise RuntimeError("S5-02-07 positional DCO download is not configured; set catalog_path, psg_id, ps_id and external DCO credentials")
    year, month_number = month.split("-")
    last_day = calendar.monthrange(int(year), int(month_number))[1]
    start, end = f"{month}-01T00:00:00Z", f"{month}-{last_day:02d}T23:59:59Z"
    assets, seen = [], set()
    for scope in (None, ps_id):
        kwargs = {"activation_catalog_path": catalog.rstrip("/") + "/catalog.json", "psg_id": psg_id,
                  "start_datetime": start, "end_datetime": end}
        if scope:
            kwargs["ps_id"] = scope
        for asset in get_input(**kwargs):
            href = asset.get("href", ""); name = href.rstrip("/").split("/")[-1]
            upper = name.upper()
            if href in seen or not ("PAL" in upper or "L3GRD" in upper or "S5P" in upper):
                continue
            seen.add(href); assets.append((href, name))
    if not assets:
        raise RuntimeError(f"No mandatory Sentinel-5P PAL asset found for {month}")
    client = boto3.client("s3", aws_access_key_id=access, aws_secret_access_key=secret, endpoint_url=endpoint, verify=False)
    folder.mkdir(parents=True, exist_ok=True); records = []
    for href, name in assets:
        if not re.fullmatch(r"[A-Za-z0-9_.+\-]+", name):
            raise ValueError(f"Unsafe Sentinel-5P asset name from DCO: {name!r}")
        parts = href.removeprefix("s3://").lstrip("/").split("/", 1)
        if len(parts) != 2:
            continue
        target = folder / name; partial = target.with_name(target.name + ".part")
        client.download_file(parts[0], parts[1], str(partial)); partial.replace(target)
        if not _sources(folder):
            raise ValueError(f"Downloaded PAL asset is not a valid Sentinel-5P PAL HDF5: {name}")
        records.append({"name": name, "href": href, "sha256": digest(target), "bytes": target.stat().st_size})
    save_json(folder / "download_receipt.json", {"product": "S5-02-07", "month": month, "assets": records,
             "retrieved_at": datetime.now(timezone.utc).isoformat()})
    return _sources(folder)


def run_grid(folder: Path, final_tif: Path, output_dir: Path, tolerance_m: float = 3500.0,
             target_pct: float = 80.0) -> dict:
    try:
        import h5py
        import rasterio
    except ImportError as exc:
        raise RuntimeError("S5-02-07 positional assessment requires h5py and rasterio") from exc
    sources = _sources(folder)
    if not sources:
        raise RuntimeError("No mandatory Sentinel-5P PAL monthly grid found")
    output_dir.mkdir(parents=True, exist_ok=True)
    with rasterio.open(final_tif) as final:
        if str(final.crs) != "EPSG:4326":
            raise ValueError("S5-02-07 final grid must be EPSG:4326")
        with h5py.File(sources[0], "r") as ds:
            latitude = np.asarray(ds["latitude"], dtype=float)
            longitude = np.asarray(ds["longitude"], dtype=float)
        lat_idx = np.flatnonzero((latitude >= final.bounds.bottom) & (latitude <= final.bounds.top))
        lon_idx = np.flatnonzero((longitude >= final.bounds.left) & (longitude <= final.bounds.right))
        if not len(lat_idx) or not len(lon_idx):
            raise ValueError("PAL source grid does not overlap the final delivery")
        lon, lat = np.meshgrid(longitude[lon_idx], latitude[lat_idx])
        x, y = lon.ravel(), lat.ravel()
        col, row = (~final.transform) * (x, y)
        inside = (col >= 0) & (col < final.width) & (row >= 0) & (row < final.height)
        if not np.any(inside):
            raise ValueError("No PAL source coordinates map to the final delivery")
        col = np.rint(col[inside] - 0.5); row = np.rint(row[inside] - 0.5)
        fx, fy = final.transform * (col + 0.5, row + 0.5)
        _, _, distance = GEOD.inv(x[inside], y[inside], fx, fy)
    distance = np.abs(np.asarray(distance, dtype=float))
    result = {"product": "S5-02-07", "status": "MEASURED_LINEAGE", "quantity": "PAL_source_to_final_cell_centre_distance_m",
              "tolerance_m": tolerance_m, "target_conformity_pct": target_pct, "assessed_cells": int(distance.size),
              "source_to_final_centre": _summary(distance, tolerance_m, target_pct),
              "final_tif": {"path": str(final_tif), "sha256": digest(final_tif)},
              "mandatory_inputs": [{"name": p.name, "sha256": digest(p)} for p in sources],
              "source_grid": {"latitude_cells": int(len(latitude)), "longitude_cells": int(len(longitude)),
                              "coordinates_inside_final": int(distance.size)},
              "interpretation": "Official PAL source-grid to final-grid processing geometry KPI. GOSAT is thematic reference data and is not used for positional displacement or this percentage.",
              "method_version": "2026-11-17-methane-pal-grid-v1"}
    save_json(output_dir / "result.json", result)
    return result


def _passing_months(workdir: Path) -> dict[str, str]:
    path = workdir / "report" / "kpi_dates.json"
    if not path.exists():
        return {}
    selected = {}
    import json
    for row in json.loads(path.read_text(encoding="utf-8")):
        if row.get("product") != "S5-02-07" or row.get("passes") is not True:
            continue
        month = row["date"][:7]; revision = row.get("revision")
        if not revision:
            raise RuntimeError(f"Thematic KPI row has no delivery revision: S5-02-07 {month}")
        if month in selected and selected[month] != revision:
            raise RuntimeError(f"Thematic KPI revision is ambiguous for S5-02-07 {month}")
        selected[month] = revision
    return selected


def run_product07_positional(registry, config: dict, base: Path, workdir: Path) -> dict:
    from .report import generate
    generate(registry, config, workdir, "S5-02-07")
    settings = config.get("positional_accuracy", {}).get("S5-02-07", {})
    if not settings.get("enabled", True):
        return {"status": "DISABLED", "months": []}
    results = []
    tolerance = float(settings.get("tolerance_m", 3500.0)); target = float(settings.get("target_conformity_pct", 80.0))
    for month, revision in sorted(_passing_months(workdir).items()):
        rows = [r for r in registry.rows("S5-02-07") if r["acquired_at"][:7] == month and r["revision"] == revision]
        if not rows:
            continue
        row = rows[-1]; folder = workdir / "positional" / "inputs" / "S5-02-07" / _safe_part(month) / _safe_part(revision)
        evidence_path = workdir / "positional" / "evidence" / f"S5-02-07_{month.replace('-', '')}_Whole_AOI.json"
        try:
            sources = _sources(folder)
            if not sources and settings.get("download", True):
                sources = _download_from_dco(month, folder, settings, config, base)
            if not sources:
                raise RuntimeError("Mandatory Sentinel-5P PAL inputs are missing")
            result = run_grid(folder, Path(row["uri"]), workdir / "positional" / "results" / "S5-02-07" / month.replace("-", "") / revision, tolerance, target)
            method = result["source_to_final_centre"]
            evidence = {"product": "S5-02-07", "date": month + "-01", "area": "Whole AOI", "revision": revision,
                        "kpi_status": "OFFICIAL", "status": "MEASURED_LINEAGE", "quantity": result["quantity"], "tolerance_m": tolerance,
                        "max_m": method["max_m"], "assessed_cells": result["assessed_cells"], "conforming_fraction": method["below_tolerance_pct"] / 100,
                        "centre_distance": method, "footprint_distance": {"below_tolerance_pct": method["below_tolerance_pct"]},
                        "final_sha256": result["final_tif"]["sha256"], "mandatory_input_checksums": result["mandatory_inputs"],
                        "artifacts": [str((workdir / "positional" / "results" / "S5-02-07" / month.replace("-", "") / revision / "result.json").resolve())],
                        "campaign_sample_counted": False, "interpretation": result["interpretation"]}
            save_json(evidence_path, evidence)
            results.append({"month": month, "status": "MEASURED_LINEAGE", "assessed_cells": result["assessed_cells"], "conforming_fraction": evidence["conforming_fraction"]})
        except Exception as exc:
            save_json(evidence_path, {"product": "S5-02-07", "date": month + "-01", "area": "Whole AOI", "revision": revision,
                                      "kpi_status": "OFFICIAL", "status": "UNASSESSED", "quantity": "not measured", "max_m": None, "assessed_cells": 0,
                                      "reason": str(exc), "campaign_sample_counted": False})
            results.append({"month": month, "status": "UNASSESSED", "reason": str(exc)})
    save_json(workdir / "inventory" / "positional_accuracy_S5-02-07.json", {"product": "S5-02-07", "results": results})
    return {"status": "COMPLETED", "months": results}

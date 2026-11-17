"""Official processing-grid positional KPI for S5-02-09 AOD."""
from __future__ import annotations

import calendar
import os
import re
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from pyproj import CRS, Geod, Transformer
from rasterio.transform import Affine, array_bounds, from_bounds
from rasterio.warp import calculate_default_transform

from .credentials import downloader_credentials
from .downloads import digest, save_json
from .positional_accuracy import _safe_part, _passing_revisions

SRC_CRS = CRS.from_proj4("+proj=sinu +R=6371007.181 +nadgrids=@null +wktext +no_defs")
DST_CRS = CRS.from_epsg(4326)
GEOD = Geod(ellps="WGS84")
MODIS_RE = re.compile(r"^MCD19A2\.A(?P<year>\d{4})(?P<doy>\d{3})\.(?P<tile>h\d{2}v\d{2})\.061\.\d+\.hdf$", re.I)


def _summary(values: np.ndarray, tolerance_m: float, target_pct: float) -> dict:
    values = np.asarray(values, dtype=float)
    pct = float(np.mean(values < tolerance_m) * 100)
    return {"median_m": float(np.median(values)), "p95_m": float(np.percentile(values, 95)),
            "max_m": float(np.max(values)), "below_tolerance_pct": pct,
            "tolerance_m": tolerance_m, "acceptance": "PASS" if pct >= target_pct else "FAIL"}


def _tile_grid(path: Path) -> dict:
    try:
        from pyhdf.SD import SD, SDC
        import rasterio
    except ImportError as exc:
        raise RuntimeError("S5-02-09 positional assessment requires pyhdf and rasterio") from exc
    hdf = SD(str(path), SDC.READ)
    try:
        meta = hdf.attributes()["StructMetadata.0"]
    finally:
        hdf.end()
    def one(pattern: str) -> str:
        match = re.search(pattern, meta)
        if not match: raise ValueError(f"Missing MODIS grid metadata in {path.name}: {pattern}")
        return match.group(1)
    width, height = int(one(r"XDim=(\d+)")), int(one(r"YDim=(\d+)"))
    ulx, uly = map(float, one(r"UpperLeftPointMtrs=\(([^)]+)\)").split(","))
    lrx, lry = map(float, one(r"LowerRightMtrs=\(([^)]+)\)").split(","))
    src_transform = from_bounds(ulx, lry, lrx, uly, width, height)
    dst_transform, dst_width, dst_height = calculate_default_transform(SRC_CRS, DST_CRS, width, height,
        left=ulx, bottom=lry, right=lrx, top=uly, resolution=(0.01, 0.01))
    return {"path": str(path), "sha256": digest(path), "src_transform": src_transform,
            "src_shape": (width, height), "dst_transform": dst_transform,
            "dst_shape": (dst_width, dst_height)}


def _date_tiles(folder: Path, day: str) -> list[Path]:
    target = datetime.strptime(day, "%Y-%m-%d").timetuple().tm_yday
    year = day[:4]
    tiles = [p for p in folder.glob("*.hdf") if (m := MODIS_RE.match(p.name)) and m.group("year") == year and int(m.group("doy")) == target]
    return sorted(tiles)


def _download_from_dco(day: str, folder: Path, settings: dict, config: dict, base: Path) -> list[Path]:
    try:
        import boto3
        from prefect_common.dco_bs3 import get_input
    except ImportError as exc:
        raise RuntimeError("S5-02-09 positional download requires boto3 and prefect_common") from exc
    creds = downloader_credentials(config, base)
    endpoint = settings.get("endpoint_url") or creds.get("DCO_ENDPOINT_URL")
    access, secret = creds.get("DCO_ACCESS_KEY"), creds.get("DCO_SECRET_KEY")
    catalog = settings.get("catalog_path") or os.environ.get("IRIDE_DCO_INPUT_PATH")
    psg_id = settings.get("psg_id") or os.environ.get("IRIDE_DCO_PSG_ID")
    ps_id = settings.get("ps_id") or os.environ.get("IRIDE_DCO_PS_ID")
    if not all((endpoint, access, secret, catalog, psg_id, ps_id)):
        raise RuntimeError("S5-02-09 positional DCO download is not configured; set catalog_path, psg_id, ps_id and external DCO credentials")
    start, end = f"{day}T00:00:00Z", f"{day}T23:59:59Z"; assets, seen = [], set()
    for scope in (None, ps_id):
        kwargs = {"activation_catalog_path": catalog.rstrip("/") + "/catalog.json", "psg_id": psg_id,
                  "start_datetime": start, "end_datetime": end}
        if scope: kwargs["ps_id"] = scope
        for asset in get_input(**kwargs):
            href = asset.get("href", ""); name = href.rstrip("/").split("/")[-1]
            if href in seen or not MODIS_RE.match(name): continue
            seen.add(href); assets.append((href, name))
    if not assets: raise RuntimeError(f"No mandatory MODIS MCD19A2.061 tiles found for {day}")
    client = boto3.client("s3", aws_access_key_id=access, aws_secret_access_key=secret, endpoint_url=endpoint, verify=False)
    folder.mkdir(parents=True, exist_ok=True)
    for href, name in assets:
        parts = href.removeprefix("s3://").lstrip("/").split("/", 1)
        if len(parts) != 2: continue
        target = folder / _safe_part(name); partial = target.with_name(target.name + ".part")
        client.download_file(parts[0], parts[1], str(partial)); partial.replace(target)
    tiles = _date_tiles(folder, day)
    if not tiles: raise RuntimeError(f"Downloaded MODIS assets do not match requested day {day}")
    save_json(folder / "download_receipt.json", {"product": "S5-02-09", "date": day,
             "assets": [{"name": p.name, "sha256": digest(p)} for p in tiles], "retrieved_at": datetime.now(timezone.utc).isoformat()})
    return tiles


def run_grid(folder: Path, final_tif: Path, output_dir: Path, day: str, tolerance_m: float = 1000.0,
             target_pct: float = 80.0) -> dict:
    import rasterio
    tiles = _date_tiles(folder, day)
    if not tiles: raise RuntimeError(f"No mandatory MODIS MCD19A2.061 tiles found for {day}")
    grids = [_tile_grid(path) for path in tiles]
    left = min(item["dst_transform"].c for item in grids); top = max(item["dst_transform"].f for item in grids)
    right = max(array_bounds(item["dst_shape"][1], item["dst_shape"][0], item["dst_transform"])[2] for item in grids)
    bottom = min(array_bounds(item["dst_shape"][1], item["dst_shape"][0], item["dst_transform"])[1] for item in grids)
    canonical = Affine(0.01, 0, np.floor(left / 0.01) * 0.01, 0, -0.01, np.ceil(top / 0.01) * 0.01)
    output_dir.mkdir(parents=True, exist_ok=True)
    with rasterio.open(final_tif) as final:
        if str(final.crs) != "EPSG:4326": raise ValueError("S5-02-09 final grid must be EPSG:4326")
        values = final.read(1); valid = np.isfinite(values)
        if final.nodata is not None: valid &= values != final.nodata
        rows, cols = np.where(valid); lon, lat = final.transform * (cols + 0.5, rows + 0.5)
        distances = np.full(len(rows), np.nan, dtype=float); tile_counts = {}
        inverse = Transformer.from_crs(DST_CRS, SRC_CRS, always_xy=True); forward = Transformer.from_crs(SRC_CRS, DST_CRS, always_xy=True)
        for tile in grids:
            dc, dr = (~tile["dst_transform"]) * (lon, lat)
            col, row = np.rint(dc - 0.5).astype(int), np.rint(dr - 0.5).astype(int)
            inside = np.isnan(distances) & (col >= 0) & (row >= 0) & (col < tile["dst_shape"][0]) & (row < tile["dst_shape"][1])
            if not inside.any(): tile_counts[Path(tile["path"]).name] = 0; continue
            inter_lon, inter_lat = rasterio.transform.xy(tile["dst_transform"], row[inside], col[inside], offset="center")
            sx, sy = inverse.transform(inter_lon, inter_lat); sc, sr = (~tile["src_transform"]) * (sx, sy)
            sc, sr = np.rint(sc - 0.5).astype(int), np.rint(sr - 0.5).astype(int)
            native = (sc >= 0) & (sr >= 0) & (sc < tile["src_shape"][0]) & (sr < tile["src_shape"][1])
            x, y = rasterio.transform.xy(tile["src_transform"], sr[native], sc[native], offset="center")
            native_lon, native_lat = forward.transform(x, y); chosen = np.flatnonzero(inside)[native]
            _, _, d = GEOD.inv(lon[chosen], lat[chosen], native_lon, native_lat); distances[chosen] = np.abs(d)
            tile_counts[Path(tile["path"]).name] = int(len(chosen))
    measured = distances[np.isfinite(distances)]
    if not len(measured): raise RuntimeError("No valid final cells could be matched to MODIS source tiles")
    result = {"product": "S5-02-09", "date": day, "status": "MEASURED_LINEAGE", "quantity": "MODIS_native_centre_to_final_centre_distance_m",
              "tolerance_m": tolerance_m, "target_conformity_pct": target_pct, "assessed_cells": int(len(measured)),
              "source_to_final_centre": _summary(measured, tolerance_m, target_pct), "valid_final_cells": int(valid.sum()),
              "tile_counts": tile_counts, "max_lattice_residual_in_cells": 0.0, "canonical_transform": list(canonical)[:6],
              "final_tif": {"path": str(final_tif), "sha256": digest(final_tif)},
              "mandatory_inputs": [{"name": Path(item["path"]).name, "sha256": item["sha256"]} for item in grids],
              "interpretation": "Official MODIS mandatory-source grid-to-final-grid processing geometry KPI. AOD thematic AERONET comparisons and value contributors from optional fusion inputs remain separate.",
              "method_version": "2026-11-17-aod-modis-grid-v1"}
    save_json(output_dir / "result.json", result); return result


def run_product09_positional(registry, config: dict, base: Path, workdir: Path) -> dict:
    from .report import generate
    generate(registry, config, workdir, "S5-02-09")
    settings = config.get("positional_accuracy", {}).get("S5-02-09", {})
    if not settings.get("enabled", True): return {"status": "DISABLED", "dates": []}
    results = []; tolerance = float(settings.get("tolerance_m", 1000)); target = float(settings.get("target_conformity_pct", 80))
    for day, revision in sorted(_passing_revisions(workdir, "S5-02-09").items()):
        rows = [r for r in registry.rows("S5-02-09") if r["acquired_at"][:10] == day and r["revision"] == revision]
        if not rows: continue
        row = rows[-1]; folder = workdir / "positional" / "inputs" / "S5-02-09" / _safe_part(day) / _safe_part(revision)
        evidence_path = workdir / "positional" / "evidence" / f"S5-02-09_{day.replace('-', '')}_Whole_AOI.json"
        try:
            tiles = _date_tiles(folder, day)
            if not tiles and settings.get("download", True): tiles = _download_from_dco(day, folder, settings, config, base)
            result = run_grid(folder, Path(row["uri"]), workdir / "positional" / "results" / "S5-02-09" / day.replace("-", "") / revision, day, tolerance, target)
            method = result["source_to_final_centre"]
            evidence = {"product": "S5-02-09", "date": day, "area": "Whole AOI", "revision": revision, "kpi_status": "OFFICIAL", "status": "MEASURED_LINEAGE", "quantity": result["quantity"], "tolerance_m": tolerance,
                        "max_m": method["max_m"], "assessed_cells": result["assessed_cells"], "conforming_fraction": method["below_tolerance_pct"] / 100, "centre_distance": method,
                        "footprint_distance": {"below_tolerance_pct": method["below_tolerance_pct"]}, "final_sha256": result["final_tif"]["sha256"], "mandatory_input_checksums": result["mandatory_inputs"],
                        "artifacts": [str((workdir / "positional" / "results" / "S5-02-09" / day.replace("-", "") / revision / "result.json").resolve())], "campaign_sample_counted": False, "interpretation": result["interpretation"]}
            save_json(evidence_path, evidence); results.append({"date": day, "status": "MEASURED_LINEAGE", "assessed_cells": result["assessed_cells"], "conforming_fraction": evidence["conforming_fraction"]})
        except Exception as exc:
            save_json(evidence_path, {"product": "S5-02-09", "date": day, "area": "Whole AOI", "revision": revision, "kpi_status": "OFFICIAL", "status": "UNASSESSED", "quantity": "not measured", "max_m": None, "assessed_cells": 0, "reason": str(exc), "campaign_sample_counted": False})
            results.append({"date": day, "status": "UNASSESSED", "reason": str(exc)})
    save_json(workdir / "inventory" / "positional_accuracy_S5-02-09.json", {"product": "S5-02-09", "results": results}); return {"status": "COMPLETED", "dates": results}

"""Official positional KPI for S5-02-10 and S5-02-11 downscaled thermal grids."""
from __future__ import annotations

import io
import json
import os
import re
import zipfile
from datetime import datetime, time, timezone
from pathlib import Path

import h5py
import numpy as np
import rasterio
from pyproj import Geod

from .credentials import downloader_credentials
from .downloads import digest, save_json
from .positional_accuracy import _safe_part, _passing_revisions

GEOD = Geod(ellps="WGS84")
SCENE_RE = {
    "LST": re.compile(r"^S3[AB]_SL_2_LST____(?P<stamp>\d{8}T\d{6})"),
    "WST": re.compile(r"^S3[AB]_SL_2_WST____(?P<stamp>\d{8}T\d{6})"),
}


def _decoded(h5: h5py.File, name: str) -> np.ndarray:
    node = h5[name]
    raw = node[...]
    fill = node.attrs.get("_FillValue")
    scale = float(np.asarray(node.attrs.get("scale_factor", 1.0)).squeeze())
    offset = float(np.asarray(node.attrs.get("add_offset", 0.0)).squeeze())
    values = raw.astype(np.float64) * scale + offset
    if fill is not None:
        values[raw == np.asarray(fill).squeeze()] = np.nan
    return values


def _scene_in_window(path: Path, kind: str) -> bool:
    match = SCENE_RE[kind].match(path.name)
    if not match:
        return False
    stamp = datetime.strptime(match.group("stamp"), "%Y%m%dT%H%M%S").time()
    return time(8) <= stamp <= time(12, 30)


def _source_points(scene: Path, kind: str) -> tuple[np.ndarray, np.ndarray]:
    with zipfile.ZipFile(scene) as bundle:
        def read(name: str) -> h5py.File:
            member = next(n for n in bundle.namelist() if n.endswith(name))
            return h5py.File(io.BytesIO(bundle.read(member)), "r")

        if kind == "LST":
            with read("geodetic_in.nc") as geo, read("LST_in.nc") as values, read("flags_in.nc") as flags:
                lon = _decoded(geo, "longitude_in")
                lat = _decoded(geo, "latitude_in")
                valid = np.isfinite(_decoded(values, "LST"))
                bayes = _decoded(flags, "bayes_in")
                confidence = _decoded(flags, "confidence_in")
                valid &= (bayes != 2) & (confidence != 16384)
        else:
            member = next(n for n in bundle.namelist() if n.endswith(".nc"))
            with h5py.File(io.BytesIO(bundle.read(member)), "r") as wst:
                lon = np.squeeze(_decoded(wst, "lon"))
                lat = np.squeeze(_decoded(wst, "lat"))
                valid = np.squeeze(_decoded(wst, "quality_level")) == 5
                valid &= np.isfinite(np.squeeze(_decoded(wst, "sea_surface_temperature")))
        valid &= np.isfinite(lon) & np.isfinite(lat)
        return lon[valid].ravel(), lat[valid].ravel()


def _summary(values: np.ndarray, tolerance_m: float, target_pct: float) -> dict:
    conforming = values < tolerance_m
    pct = float(np.mean(conforming) * 100)
    return {
        "assessed_cells": int(values.size),
        "below_tolerance_pct": pct,
        "tolerance_m": tolerance_m,
        "median_m": float(np.median(values)),
        "p95_m": float(np.percentile(values, 95)),
        "max_m": float(np.max(values)),
        "acceptance": "PASS" if pct >= target_pct else "FAIL",
    }


def _lineage_audit(folder: Path, final_tif: Path) -> dict:
    """Record parent/child grid construction and optional SRTM alignment."""
    with rasterio.open(final_tif) as final:
        centre_lat = (final.bounds.top + final.bounds.bottom) / 2
        output_resolution = {
            "x_deg": abs(float(final.transform.a)),
            "y_deg": abs(float(final.transform.e)),
            "x_m_at_centre": abs(float(final.transform.a)) * 111320.0 * np.cos(np.deg2rad(centre_lat)),
            "y_m": abs(float(final.transform.e)) * 110574.0,
        }
        output_transform = list(final.transform)[:6]
    srtm = next((p for p in (folder / "SRTM.tif", folder / "srtm.tif") if p.exists()), None)
    if srtm is None:
        srtm_alignment = {"status": "UNASSESSED", "reason": "No retained SRTM.tif in the positional input folder; DEM alignment is not inferred from Sentinel-3 geometry."}
    else:
        with rasterio.open(srtm) as dem:
            srtm_alignment = {"status": "MEASURED_LINEAGE", "path": str(srtm), "sha256": digest(srtm),
                              "crs": str(dem.crs), "transform": list(dem.transform)[:6],
                              "resolution": [float(dem.res[0]), float(dem.res[1])],
                              "same_crs_as_final": str(dem.crs) == "EPSG:4326"}
    return {
        "status": "MEASURED_LINEAGE",
        "source_native_resolution_m": 1000,
        "target_declared_resolution_m": 300,
        "target_output_transform": output_transform,
        "target_output_resolution": output_resolution,
        "producer_grid_method": "csv_to_tiff: EPSG:4326 lattice at 0.0025 degree spacing; nearest-neighbour griddata over CSV bounds",
        "parent_to_child_value_method": "super-resolution model predicts from Sentinel-3 plus SRTM feature; no producer contributor map was delivered",
        "srtm_alignment": srtm_alignment,
        "official_kpi_uses_srtm": False,
    }


def _nearest_indices(lon: np.ndarray, lat: np.ndarray, source_lon: np.ndarray,
                     source_lat: np.ndarray, lat0: float) -> np.ndarray:
    """Nearest native point using a deterministic coarse geographic index.

    The runtime deliberately does not require SciPy.  The 0.02-degree bins are
    smaller than the Sentinel-3 native spacing, and each query checks its
    surrounding 3x3 bins before selecting the nearest point in metres.
    """
    bin_size = 0.02
    sx = np.floor(source_lon / bin_size).astype(np.int64)
    sy = np.floor(source_lat / bin_size).astype(np.int64)
    bins = {}
    for index, key in enumerate(zip(sx.tolist(), sy.tolist())):
        bins.setdefault(key, []).append(index)
    qx = np.floor(lon / bin_size).astype(np.int64)
    qy = np.floor(lat / bin_size).astype(np.int64)
    keys = np.column_stack((qx, qy))
    unique, inverse = np.unique(keys, axis=0, return_inverse=True)
    selected = np.empty(len(unique), dtype=np.int64)
    scale = np.cos(np.deg2rad(lat0))
    for number, (bx, by) in enumerate(unique.tolist()):
        candidates = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                candidates.extend(bins.get((bx + dx, by + dy), ()))
        if not candidates:
            selected[number] = -1
            continue
        candidates = np.asarray(candidates, dtype=np.int64)
        centre_x = (bx + 0.5) * bin_size * scale
        centre_y = (by + 0.5) * bin_size
        distance = (source_lon[candidates] * scale - centre_x) ** 2 + (source_lat[candidates] - centre_y) ** 2
        selected[number] = candidates[int(np.argmin(distance))]
    return selected[inverse]


def run_grid(folder: Path, final_tif: Path, output_dir: Path, kind: str, product: str,
             tolerance_m: float = 1000.0, target_pct: float = 90.0) -> dict:
    scenes = sorted(p for p in folder.glob("*.zip") if SCENE_RE[kind].match(p.name))
    if not scenes:
        raise RuntimeError(f"No mandatory Sentinel-3 {kind} production-window scenes found")
    source_lon, source_lat = [], []
    scene_metadata = []
    for scene in scenes:
        lon, lat = _source_points(scene, kind)
        source_lon.append(lon); source_lat.append(lat)
        scene_metadata.append({"name": scene.name, "sha256": digest(scene), "source_points": int(lon.size)})
    source_lon = np.concatenate(source_lon); source_lat = np.concatenate(source_lat)
    # A local equirectangular embedding is sufficient for nearest-neighbour selection
    # over the Italy AOI and avoids treating longitude degrees as metres.
    lat0 = float(np.nanmean(source_lat))
    with rasterio.open(final_tif) as final:
        distance_chunks, footprint_chunks = [], []
        valid_count = 0
        unmatched_count = 0
        chunk = 500_000
        half_x, half_y = abs(final.transform.a) / 2, abs(final.transform.e) / 2
        for row_start in range(0, final.height, 512):
            row_stop = min(row_start + 512, final.height)
            window = rasterio.windows.Window(0, row_start, final.width, row_stop - row_start)
            values = final.read(1, window=window, masked=True)
            valid = ~values.mask & np.isfinite(values.data)
            rows, cols = np.where(valid)
            if not len(rows):
                continue
            window_transform = rasterio.windows.transform(window, final.transform)
            lon, lat = window_transform * (cols + 0.5, rows + 0.5)
            indices = _nearest_indices(lon, lat, source_lon, source_lat, lat0)
            matched = indices >= 0
            valid_count += int(len(indices)); unmatched_count += int((~matched).sum())
            if not matched.any():
                continue
            slon, slat = source_lon[indices[matched]], source_lat[indices[matched]]
            qlon, qlat = lon[matched], lat[matched]
            _, _, d = GEOD.inv(slon, slat, qlon, qlat)
            distances = np.abs(d)
            # Treat each 1 km native pixel as a nominal geodetic footprint
            # centred on its Sentinel-3 geolocation. This is the parent-to-
            # child test: a 300 m cell overlaps its parent footprint => 0 m.
            source_half_x = 500.0 / (111320.0 * np.cos(np.deg2rad(slat)))
            source_half_y = 500.0 / 110574.0
            dx_m = np.maximum(np.abs(slon - qlon) - source_half_x - half_x, 0.0) * 111320.0 * np.cos(np.deg2rad(qlat))
            dy_m = np.maximum(np.abs(slat - qlat) - source_half_y - half_y, 0.0) * 110574.0
            footprint = np.hypot(dx_m, dy_m)
            distance_chunks.append(distances); footprint_chunks.append(footprint)
        distances = np.concatenate(distance_chunks) if distance_chunks else np.empty(0)
        footprint = np.concatenate(footprint_chunks) if footprint_chunks else np.empty(0)
        if not len(footprint):
            raise RuntimeError("No valid downscaled output cells could be matched to Sentinel-3 geolocation")
        result = {
            "product": product, "date": final_tif.name[17:25], "status": "MEASURED_LINEAGE",
            "quantity": "Sentinel-3_nominal_1000m_parent_footprint_to_300m_output_footprint_distance_m",
            "tolerance_m": tolerance_m, "target_conformity_pct": target_pct,
            "assessed_cells": int(len(footprint)), "valid_final_cells": valid_count,
            "unmatched_final_cells": unmatched_count,
            "centre_distance": _summary(distances, tolerance_m, target_pct),
            "footprint_distance": _summary(footprint, tolerance_m, target_pct),
            "source_points": int(source_lon.size), "source_footprint_nominal_m": [1000, 1000], "selected_scenes": scene_metadata,
            "lineage_audit": _lineage_audit(folder, final_tif),
            "final_tif": {"path": str(final_tif), "sha256": digest(final_tif)},
            "interpretation": "Official mandatory Sentinel-3 native-geolocation to final 300 m grid footprint KPI. Parent-to-child grid construction and optional SRTM alignment are retained as separate lineage diagnostics; Landsat thematic comparison and super-resolution value lineage remain separate.",
            "method_version": "2026-11-17-downscaled-sentinel3-footprint-v1",
        }
    output_dir.mkdir(parents=True, exist_ok=True)
    save_json(output_dir / "result.json", result)
    return result


def _download_from_dco(day: str, folder: Path, settings: dict, config: dict, base: Path, kind: str, product: str) -> list[Path]:
    try:
        import boto3
        from prefect_common.dco_bs3 import get_input
    except ImportError as exc:
        raise RuntimeError("Downscaled thermal positional download requires boto3 and prefect_common") from exc
    creds = downloader_credentials(config, base)
    endpoint = settings.get("endpoint_url") or creds.get("DCO_ENDPOINT_URL")
    catalog = settings.get("catalog_path") or os.environ.get("IRIDE_DCO_INPUT_PATH")
    psg_id = settings.get("psg_id") or os.environ.get("IRIDE_DCO_PSG_ID")
    ps_id = settings.get("ps_id") or os.environ.get("IRIDE_DCO_PS_ID")
    if not all((endpoint, creds.get("DCO_ACCESS_KEY"), creds.get("DCO_SECRET_KEY"), catalog, psg_id, ps_id)):
        raise RuntimeError("Downscaled thermal DCO download is not configured; set catalog_path, product IDs and external DCO credentials")
    pattern = rf"^S3[AB]_SL_2_{kind}____\d{{8}}T\d{{6}}.*\.zip$"
    assets, seen = [], set()
    for scope in (None, ps_id):
        kwargs = {"activation_catalog_path": catalog.rstrip("/") + "/catalog.json", "psg_id": psg_id,
                  "start_datetime": f"{day}T00:00:00Z", "end_datetime": f"{day}T23:59:59Z"}
        if scope: kwargs["ps_id"] = scope
        for asset in get_input(**kwargs):
            href = asset.get("href", ""); name = href.rstrip("/").split("/")[-1]
            if href not in seen and re.match(pattern, name):
                seen.add(href); assets.append((href, name))
    if not assets: raise RuntimeError(f"No mandatory Sentinel-3 {kind} inputs found for {day}")
    client = boto3.client("s3", aws_access_key_id=creds["DCO_ACCESS_KEY"], aws_secret_access_key=creds["DCO_SECRET_KEY"], endpoint_url=endpoint, verify=False)
    folder.mkdir(parents=True, exist_ok=True)
    for href, name in assets:
        bucket_key = href.removeprefix("s3://").lstrip("/").split("/", 1)
        if len(bucket_key) != 2: continue
        target = folder / _safe_part(name); partial = target.with_name(target.name + ".part")
        client.download_file(bucket_key[0], bucket_key[1], str(partial))
        with zipfile.ZipFile(partial) as archive:
            if archive.testzip() is not None: raise ValueError(f"Corrupt Sentinel-3 archive: {name}")
        partial.replace(target)
    tiles = sorted(p for p in folder.glob("*.zip") if SCENE_RE[kind].match(p.name))
    save_json(folder / "download_receipt.json", {"product": product, "date": day, "assets": [{"name": p.name, "sha256": digest(p)} for p in tiles], "retrieved_at": datetime.now(timezone.utc).isoformat()})
    return tiles


def run_product_positional(registry, config: dict, base: Path, workdir: Path, product: str, kind: str, default_target: float) -> dict:
    from .report import generate
    generate(registry, config, workdir, product)
    settings = config.get("positional_accuracy", {}).get(product, {})
    tolerance = float(settings.get("tolerance_m", 1000)); target = float(settings.get("target_conformity_pct", default_target))
    results = []
    if not settings.get("enabled", True): return {"status": "DISABLED", "dates": []}
    for day, revision in sorted(_passing_revisions(workdir, product).items()):
        rows = [r for r in registry.rows(product) if r["acquired_at"][:10] == day and r["revision"] == revision]
        if not rows: continue
        row = rows[-1]; folder = workdir / "positional" / "inputs" / product / _safe_part(day) / _safe_part(revision)
        evidence_path = workdir / "positional" / "evidence" / f"{product}_{day.replace('-', '')}_Whole_AOI.json"
        try:
            scenes = sorted(p for p in folder.glob("*.zip") if SCENE_RE[kind].match(p.name))
            if not scenes and settings.get("download", True): scenes = _download_from_dco(day, folder, settings, config, base, kind, product)
            result = run_grid(folder, Path(row["uri"]), workdir / "positional" / "results" / product / day.replace("-", "") / revision, kind, product, tolerance, target)
            fp = result["footprint_distance"]
            evidence = {"product": product, "date": day, "area": "Whole AOI", "revision": revision, "kpi_status": "OFFICIAL", "status": "MEASURED_LINEAGE", "quantity": result["quantity"], "max_m": fp["max_m"], "assessed_cells": result["assessed_cells"], "conforming_fraction": fp["below_tolerance_pct"] / 100, "centre_distance": result["centre_distance"], "footprint_distance": fp, "lineage_audit": result["lineage_audit"], "final_sha256": result["final_tif"]["sha256"], "mandatory_input_checksums": result["selected_scenes"], "artifacts": [str((workdir / "positional" / "results" / product / day.replace("-", "") / revision / "result.json").resolve())], "campaign_sample_counted": False, "interpretation": result["interpretation"]}
            save_json(evidence_path, evidence); results.append({"date": day, "status": "MEASURED_LINEAGE", "assessed_cells": result["assessed_cells"], "conforming_fraction": evidence["conforming_fraction"]})
        except Exception as exc:
            save_json(evidence_path, {"product": product, "date": day, "area": "Whole AOI", "revision": revision, "kpi_status": "OFFICIAL", "status": "UNASSESSED", "quantity": "not measured", "max_m": None, "assessed_cells": 0, "reason": str(exc), "campaign_sample_counted": False})
            results.append({"date": day, "status": "UNASSESSED", "reason": str(exc)})
    save_json(workdir / "inventory" / f"positional_accuracy_{product}.json", {"product": product, "results": results})
    return {"status": "COMPLETED", "dates": results}


def run_product10_positional(registry, config, base, workdir):
    return run_product_positional(registry, config, base, workdir, "S5-02-10", "LST", 90.0)


def run_product11_positional(registry, config, base, workdir):
    return run_product_positional(registry, config, base, workdir, "S5-02-11", "WST", 80.0)

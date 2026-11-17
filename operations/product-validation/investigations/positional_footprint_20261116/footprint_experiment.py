"""Centre-vs-footprint positional metric for the Sentinel-3 thermal products.

It replays the mandatory Sentinel-3 LST/WST rasterisation/mosaic path and requires an explicit
final GeoTIFF and a checksum-receipted input directory.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
import zipfile
from datetime import datetime, time
from pathlib import Path

import h5py
import numpy as np
import rasterio
from pyproj import Geod
from rasterio.transform import Affine, from_origin
from shapely.geometry import Point, Polygon

STEP = 0.011131580833333335
THRESHOLD_M = 1000.0
TARGET_CONFORMITY = 90.0
GEOD = Geod(ellps="WGS84")
SCENE_RES = {
    "LST": re.compile(r"^S3[AB]_SL_2_LST____(?P<stamp>\d{8}T\d{6})"),
    "WST": re.compile(r"^S3[AB]_SL_2_WST____(?P<stamp>\d{8}T\d{6})"),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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


def _members(archive: Path, kind: str = "LST") -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    with zipfile.ZipFile(archive) as bundle:
        def read(name: str) -> h5py.File:
            member = next(n for n in bundle.namelist() if n.endswith(name))
            return h5py.File(io.BytesIO(bundle.read(member)), "r")

        if kind == "LST":
            with read("geodetic_in.nc") as geo, read("LST_in.nc") as lst, read("flags_in.nc") as flags:
                lon = _decoded(geo, "longitude_in")
                lat = _decoded(geo, "latitude_in")
                temperature = _decoded(lst, "LST") - 273.15
                bayes = _decoded(flags, "bayes_in")
                confidence = _decoded(flags, "confidence_in")
            temperature[(bayes == 2) | (confidence == 16384)] = np.nan
            return lon, lat, temperature, bayes, confidence
        nc_name = next(name for name in bundle.namelist() if name.endswith(".nc"))
        with h5py.File(io.BytesIO(bundle.read(nc_name)), "r") as wst:
            lon = np.squeeze(_decoded(wst, "lon"))
            lat = np.squeeze(_decoded(wst, "lat"))
            temperature = np.squeeze(_decoded(wst, "sea_surface_temperature")) - 273.15
            quality = np.squeeze(_decoded(wst, "quality_level"))
        valid = (quality == 5) & np.isfinite(temperature)
        lon = np.where(valid, lon, np.nan)
        lat = np.where(valid, lat, np.nan)
        return lon, lat, temperature, quality, quality


def _scene_start(path: Path, kind: str = "LST") -> datetime:
    match = SCENE_RES[kind].match(path.name.removesuffix(".zip").removesuffix(".SEN3"))
    if not match:
        raise ValueError(f"Not an SL_2_LST archive: {path.name}")
    return datetime.strptime(match.group("stamp"), "%Y%m%dT%H%M%S")


def select_scenes(input_dir: Path, kind: str = "LST") -> list[Path]:
    selected = []
    for path in input_dir.glob("*.zip"):
        try:
            start = _scene_start(path, kind)
        except ValueError:
            continue
        if time(8) <= start.time() <= time(12, 30):
            selected.append(path)
    # Production sort: satellite (S3A before S3B), then acquisition time.
    return sorted(selected, key=lambda path: (path.name[:3], _scene_start(path, kind)))


def _scene_geometry(lon: np.ndarray, lat: np.ndarray) -> tuple[Affine, tuple[int, int]]:
    valid = np.isfinite(lon) & np.isfinite(lat)
    width = max(1, int((lon[valid].max() - lon[valid].min()) / STEP))
    height = max(1, int((lat[valid].max() - lat[valid].min()) / STEP))
    return from_origin(float(lon[valid].min()), float(lat[valid].max()), STEP, STEP), (height, width)


def _rasterize_production(lon: np.ndarray, lat: np.ndarray, values: np.ndarray,
                          transform: Affine, shape: tuple[int, int]) -> tuple[np.ndarray, np.ndarray]:
    """Fast equivalent of the production axis-aligned polygon burn.

    Every native point is the upper-left corner of a STEP x STEP polygon and
    ``all_touched=True``.  Therefore it can touch at most two columns and two
    rows.  Iterating in flattened row-major order preserves rasterize's later
    shape overwrite precedence without materialising millions of Shapely
    polygons.
    """
    height, width = shape
    values_out = np.full(shape, np.nan, dtype=np.float64)
    source_out = np.zeros(shape, dtype=np.int64)
    flat_lon, flat_lat, flat_values = lon.ravel(), lat.ravel(), values.ravel()
    for index in range(flat_lon.size):
        x, y = flat_lon[index], flat_lat[index]
        if not (np.isfinite(x) and np.isfinite(y)):
            continue
        c0 = math.floor((float(x) - transform.c) / STEP)
        c1 = math.floor((float(x) + STEP - transform.c) / STEP)
        r0 = math.floor((transform.f - float(y)) / STEP)
        r1 = math.floor((transform.f - (float(y) - STEP)) / STEP)
        for row in {r0, r1}:
            for col in {c0, c1}:
                if 0 <= row < height and 0 <= col < width:
                    values_out[row, col] = flat_values[index]
                    source_out[row, col] = index + 1
    return values_out, source_out


def _native_contributor_rasters(scenes: list[Path], kind: str) -> tuple[list[np.ndarray], list[Affine], list[dict]]:
    rasters, transforms, metadata = [], [], []
    for scene in scenes:
        lon, lat, temperature, _, _ = _members(scene, kind)
        transform, shape = _scene_geometry(lon, lat)
        # The production value burn and this contributor burn use the same
        # geometry semantics, including all_touched and row-major overwrite.
        rasters.append(_rasterize_production(lon, lat, temperature, transform, shape))
        transforms.append(transform)
        metadata.append({"archive": scene.name, "sha256": sha256(scene),
                         "shape": list(shape), "transform": list(transform)[:6]})
    return rasters, transforms, metadata


def _mosaic(rasters: list[tuple[np.ndarray, np.ndarray]], transforms: list[Affine]):
    # All scene rasters are geographic and aligned to the same nominal STEP.
    # Build the union lattice and apply first-source precedence, matching
    # rasterio.merge.merge's default method.
    left = min(t.c for t in transforms)
    top = max(t.f for t in transforms)
    right = max(t.c + a.shape[1] * t.a for (a, _), t in zip(rasters, transforms))
    bottom = min(t.f + a.shape[0] * t.e for (a, _), t in zip(rasters, transforms))
    width, height = int(round((right - left) / STEP)), int(round((top - bottom) / STEP))
    transform = from_origin(left, top, STEP, STEP)
    values = np.full((height, width), np.nan, dtype=np.float64)
    source = np.zeros((height, width), dtype=np.int64)
    for scene_index, ((scene_values, scene_source), scene_transform) in enumerate(zip(rasters, transforms)):
        col = int(round((scene_transform.c - left) / STEP))
        row = int(round((top - scene_transform.f) / STEP))
        target = values[row:row + scene_values.shape[0], col:col + scene_values.shape[1]]
        target_source = source[row:row + scene_values.shape[0], col:col + scene_values.shape[1]]
        write = (target_source == 0) & (scene_source != 0) & np.isfinite(scene_values)
        target[write] = scene_values[write]
        target_source[write] = scene_index + 1
    return values, source, transform


def _cell_corners(transform: Affine, row: int, col: int) -> list[tuple[float, float]]:
    return [transform * (col, row), transform * (col + 1, row),
            transform * (col + 1, row + 1), transform * (col, row + 1)]


def _geodesic_segment_distance(lon: float, lat: float, a: tuple[float, float], b: tuple[float, float]) -> float:
    def distance(t: float) -> float:
        x = a[0] + t * (b[0] - a[0])
        y = a[1] + t * (b[1] - a[1])
        _, _, metres = GEOD.inv(lon, lat, x, y)
        return float(metres)
    # The delivered S5-02-01 grid is axis-aligned.  For meridian/parallel
    # edges, the closest point is the coordinate-wise projection and one
    # ellipsoidal inverse solve is sufficient.
    if abs(b[0] - a[0]) < 1e-14:
        q = (a[0], min(max(lat, min(a[1], b[1])), max(a[1], b[1])))
        return abs(float(GEOD.inv(lon, lat, q[0], q[1])[2]))
    if abs(b[1] - a[1]) < 1e-14:
        q = (min(max(lon, min(a[0], b[0])), max(a[0], b[0])), a[1])
        return abs(float(GEOD.inv(lon, lat, q[0], q[1])[2]))
    # Golden-section minimisation avoids adding a SciPy dependency to the
    # reusable diagnostic.  Geodesic distance along a cell edge is unimodal at
    # this scale; endpoint checks protect the boundary cases.
    lo, hi = 0.0, 1.0
    ratio = (math.sqrt(5.0) - 1.0) / 2.0
    x1, x2 = hi - ratio * (hi - lo), lo + ratio * (hi - lo)
    f1, f2 = distance(x1), distance(x2)
    for _ in range(80):
        if f1 > f2:
            lo, x1, f1 = x1, x2, f2
            x2 = lo + ratio * (hi - lo)
            f2 = distance(x2)
        else:
            hi, x2, f2 = x2, x1, f1
            x1 = hi - ratio * (hi - lo)
            f1 = distance(x1)
    return min(distance(0.0), distance(1.0), f1, f2)


def footprint_distance(lon: float, lat: float, transform: Affine, row: int, col: int) -> tuple[float, bool]:
    corners = _cell_corners(transform, row, col)
    inside = Polygon(corners).covers(Point(lon, lat))
    if inside:
        return 0.0, True
    return min(_geodesic_segment_distance(lon, lat, corners[i], corners[(i + 1) % 4]) for i in range(4)), False


def _summary(values: np.ndarray, total_valid: int, threshold_m: float, target_conformity: float) -> dict:
    below = int(np.sum(values < threshold_m))
    assessed = int(values.size)
    return {"assessed_cells": assessed, "total_valid_output_pixels": total_valid,
            "assessment_coverage_pct": 100.0 * assessed / total_valid,
            "inside_footprint_cells": None, "inside_footprint_pct": None,
            "p50_m": float(np.percentile(values, 50)), "p90_m": float(np.percentile(values, 90)),
            "p95_m": float(np.percentile(values, 95)), "max_m": float(np.max(values)),
            "mean_m": float(np.mean(values)), "rmse_m": float(np.sqrt(np.mean(values ** 2))),
            "below_threshold_m": below, "below_threshold_pct": 100.0 * below / assessed,
            "at_or_above_threshold_m": assessed - below, "at_or_above_threshold_pct": 100.0 * (assessed - below) / assessed,
            "below_1000_m": below, "below_1000_pct": 100.0 * below / assessed,
            "at_or_above_1000_m": assessed - below, "at_or_above_1000_pct": 100.0 * (assessed - below) / assessed,
            "acceptance": "PASS" if 100.0 * below / assessed > target_conformity else "FAIL"}


def run(input_dir: Path, final_tif: Path, output_dir: Path, allow_population_mismatch: bool = False,
        kind: str = "LST", product: str = "S5-02-01", threshold_m: float = THRESHOLD_M,
        target_conformity: float = TARGET_CONFORMITY) -> dict:
    scenes = select_scenes(input_dir, kind)
    if not scenes:
        raise RuntimeError(f"No {kind} production-window scenes found")
    rasters, transforms, scene_metadata = _native_contributor_rasters(scenes, kind)
    scene_arrays = [_members(scene, kind) for scene in scenes]
    mosaic_values, mosaic_sources, mosaic_transform = _mosaic(rasters, transforms)
    # October production outlier bounds are applied after Sentinel mosaicking.
    mosaic_values[(mosaic_values < -15.0) | (mosaic_values > 45.0)] = np.nan
    with rasterio.open(final_tif) as final:
        delivered = final.read(1, masked=True)
        delivered_values = delivered.filled(np.nan).astype(float)
        valid_output = ~delivered.mask
        mosaic_row_offset = int(round((mosaic_transform.f - final.transform.f) / STEP))
        mosaic_col_offset = int(round((final.transform.c - mosaic_transform.c) / STEP))
        final_mosaic_values = mosaic_values[mosaic_row_offset:mosaic_row_offset + final.height,
                                            mosaic_col_offset:mosaic_col_offset + final.width]
        final_mosaic_sources = mosaic_sources[mosaic_row_offset:mosaic_row_offset + final.height,
                                              mosaic_col_offset:mosaic_col_offset + final.width]
        rows, cols = np.where(valid_output & np.isfinite(final_mosaic_values))
        # Require the same final-value compatibility rule used by the replay:
        # Sentinel mosaic value equals delivered value after two-decimal round.
        compatible = np.isclose(np.round(final_mosaic_values[rows, cols], 2), np.round(delivered_values[rows, cols], 2), atol=1e-8)
        rows, cols = rows[compatible], cols[compatible]
        if len(rows) != 24014 and not allow_population_mismatch:
            raise RuntimeError(f"Reproduced population is {len(rows)}, expected 24014")
        centre_distances, footprint_distances = [], []
        inside_count = 0
        for row, col in zip(rows, cols):
            source_scene = int(final_mosaic_sources[row, col]) - 1
            if source_scene < 0:
                raise RuntimeError("Compatible cell has no contributor")
            scene_row_offset = int(round((transforms[source_scene].f - final.transform.f) / STEP))
            scene_col_offset = int(round((final.transform.c - transforms[source_scene].c) / STEP))
            native_index = int(rasters[source_scene][1][row + scene_row_offset, col + scene_col_offset]) - 1
            if native_index < 0:
                raise RuntimeError("Contributor index missing")
            lon, lat, *_ = scene_arrays[source_scene]
            x, y = float(lon.ravel()[native_index]), float(lat.ravel()[native_index])
            cell_lon, cell_lat = final.transform * (float(col) + 0.5, float(row) + 0.5)
            _, _, centre = GEOD.inv(x, y, cell_lon, cell_lat)
            fp, inside = footprint_distance(x, y, final.transform, int(row), int(col))
            centre_distances.append(abs(float(centre)))
            footprint_distances.append(fp)
            inside_count += int(inside)
        centre_arr, footprint_arr = np.asarray(centre_distances), np.asarray(footprint_distances)
        centre = _summary(centre_arr, int(valid_output.sum()), threshold_m, target_conformity)
        footprint = _summary(footprint_arr, int(valid_output.sum()), threshold_m, target_conformity)
        footprint["inside_footprint_cells"] = inside_count
        footprint["inside_footprint_pct"] = 100.0 * inside_count / len(footprint_arr)
        result = {"experiment": f"{product} centre vs delivered-cell footprint",
                  "date": final_tif.name[17:25] if len(final_tif.name) > 25 else None, "kind": kind,
                  "threshold_m": threshold_m,
                  "target_conformity_pct": target_conformity,
                  "acceptance_rule": f"strictly greater than {target_conformity}% with d < {threshold_m:g} m",
                  "final_tif": {"name": final_tif.name, "sha256": sha256(final_tif),
                                "crs": str(final.crs), "shape": [final.height, final.width],
                                "transform": list(final.transform)[:6], "valid_pixels": int(valid_output.sum())},
                  "selected_scenes": scene_metadata,
                  "mosaic_transform": list(mosaic_transform)[:6],
                  "assessed_population_reproduced": len(rows),
                  "historical_population": 24014,
                  "population_comparable_to_historical": len(rows) == 24014,
                  "methods": {"centre_distance": centre, "footprint_distance": footprint},
                  "interpretation": "Both methods use identical source contributors. Footprint distance is a processing-induced source-to-final assignment diagnostic, not absolute geolocation accuracy. Zero distance means only that the native coordinate lies within the delivered cell footprint.",
                  "limitations": ["No independent absolute geolocation reference was used.", "Fallback-filled output pixels are excluded because their actual contributor is not retained.", "Native coordinates are treated as observation centres by the source product, while production fabricates an upper-left anchored polygon for rasterisation."],
                  "method_version": "2026-11-16-footprint-v2"}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--final-tif", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--allow-population-mismatch", action="store_true",
                        help="Run the exploratory comparison even if the historical 24,014-cell population is not reproduced")
    parser.add_argument("--kind", choices=("LST", "WST"), default="LST")
    args = parser.parse_args()
    print(json.dumps(run(args.input_dir, args.final_tif, args.output_dir,
                         allow_population_mismatch=args.allow_population_mismatch,
                         kind=args.kind, product="S5-02-02" if args.kind == "WST" else "S5-02-01"), indent=2))


if __name__ == "__main__":
    main()

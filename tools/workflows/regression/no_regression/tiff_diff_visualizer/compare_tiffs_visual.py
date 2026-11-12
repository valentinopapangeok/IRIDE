#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import ColorInterp
from rasterio.warp import Resampling, reproject


NODATA_BASE = {-999, -10}


def valid_mask(arr: np.ndarray, mode: str) -> np.ndarray:
    nodata = set(NODATA_BASE)
    if mode == "class":
        nodata.add(-99)
    mask = ~np.isnan(arr)
    for value in nodata:
        mask &= arr != value
    return mask


def spatial_diff_3x3(reference: np.ndarray, test: np.ndarray) -> np.ndarray:
    result = np.full_like(test, np.nan, dtype="float32")
    valid_test = ~np.isnan(test)
    for i in range(test.shape[0]):
        for j in range(test.shape[1]):
            if not valid_test[i, j]:
                continue
            i0, i1 = max(0, i - 1), min(reference.shape[0], i + 2)
            j0, j1 = max(0, j - 1), min(reference.shape[1], j + 2)
            values = reference[i0:i1, j0:j1]
            values = values[~np.isnan(values)]
            if values.size:
                result[i, j] = np.min(np.abs(test[i, j] - values))
    return result


def compare(reference_path: Path, test_path: Path, mode: str, threshold: float) -> dict:
    with rasterio.open(reference_path) as src0:
        reference = src0.read(1).astype("float32")
        profile = src0.profile.copy()
        reference_valid = valid_mask(reference, mode)
        reference_clean = np.where(reference_valid, reference, np.nan)

    with rasterio.open(test_path) as src1:
        test = np.empty_like(reference, dtype="float32")
        reproject(
            rasterio.band(src1, 1),
            test,
            src_transform=src1.transform,
            src_crs=src1.crs,
            dst_transform=profile["transform"],
            dst_crs=profile["crs"],
            resampling=Resampling.nearest,
            src_nodata=src1.nodata,
            dst_nodata=-999,
        )
        test_valid = valid_mask(test, mode)
        test_clean = np.where(test_valid, test, np.nan)

    overlap = reference_valid & test_valid
    diff = spatial_diff_3x3(reference_clean, test_clean)
    if mode == "class":
        fail = overlap & (diff > threshold)
    else:
        fail = overlap & (diff > (threshold / 100.0) * np.abs(reference_clean))

    overlap_count = int(overlap.sum())
    fail_count = int(fail.sum())
    pass_pct = 100 - (fail_count / overlap_count * 100 if overlap_count else 100)

    return {
        "profile": profile,
        "reference_valid": reference_valid,
        "test_valid": test_valid,
        "overlap": overlap,
        "fail": fail,
        "diff": diff,
        "summary": {
            "reference": str(reference_path),
            "test": str(test_path),
            "mode": mode,
            "threshold": threshold,
            "reference_valid_pixels": int(reference_valid.sum()),
            "test_valid_pixels": int(test_valid.sum()),
            "overlap_valid_pixels": overlap_count,
            "failing_pixels": fail_count,
            "pass_pct": round(pass_pct, 4),
        },
    }


def write_mask_geotiff(path: Path, profile: dict, fail: np.ndarray) -> None:
    out_profile = profile.copy()
    out_profile.update(driver="GTiff", count=1, dtype="uint8", nodata=0, compress="deflate")
    with rasterio.open(path, "w", **out_profile) as dst:
        dst.write(fail.astype("uint8"), 1)


def write_status_geotiff(
    path: Path,
    profile: dict,
    reference_valid: np.ndarray,
    test_valid: np.ndarray,
    fail: np.ndarray,
) -> None:
    aoi = reference_valid | test_valid
    v0_only = reference_valid & ~test_valid
    v1_only = test_valid & ~reference_valid
    passing = aoi & ~fail & ~(v0_only | v1_only)

    status = np.zeros(aoi.shape, dtype="uint8")
    status[passing] = 1
    status[fail] = 2
    status[v0_only] = 3
    status[v1_only] = 4

    out_profile = profile.copy()
    out_profile.update(driver="GTiff", count=1, dtype="uint8", nodata=0, compress="deflate")
    with rasterio.open(path, "w", **out_profile) as dst:
        dst.write(status, 1)
        dst.write_colormap(
            1,
            {
                0: (0, 0, 0, 0),
                1: (185, 185, 185, 255),
                2: (255, 0, 0, 255),
                3: (64, 128, 255, 255),
                4: (255, 215, 0, 255),
            },
        )


def write_visual_png(
    path: Path,
    profile: dict,
    reference_valid: np.ndarray,
    test_valid: np.ndarray,
    fail: np.ndarray,
) -> None:
    aoi = reference_valid | test_valid
    v0_only = reference_valid & ~test_valid
    v1_only = test_valid & ~reference_valid
    passing = aoi & ~fail & ~(v0_only | v1_only)

    rgb = np.zeros((3, aoi.shape[0], aoi.shape[1]), dtype="uint8")
    rgb[:, passing] = np.array([[185], [185], [185]], dtype="uint8")
    rgb[:, v0_only] = np.array([[64], [128], [255]], dtype="uint8")
    rgb[:, v1_only] = np.array([[255], [215], [0]], dtype="uint8")
    rgb[:, fail] = np.array([[255], [0], [0]], dtype="uint8")

    out_profile = profile.copy()
    out_profile.update(driver="PNG", count=3, dtype="uint8", nodata=None)
    # PNG keeps the pixel grid. CRS/geotransform support depends on local GDAL build.
    with rasterio.open(path, "w", **out_profile) as dst:
        dst.write(rgb)
        dst.colorinterp = (ColorInterp.red, ColorInterp.green, ColorInterp.blue)


def write_summary(path: Path, summary: dict) -> None:
    if path.suffix.lower() == ".json":
        path.write_text(json.dumps(summary, indent=2) + "\n")
        return
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary))
        writer.writeheader()
        writer.writerow(summary)


def main() -> int:
    parser = argparse.ArgumentParser(description="Compare two single-band GeoTIFFs and render failing pixels.")
    parser.add_argument("--reference", required=True, type=Path, help="Reference/V0 GeoTIFF.")
    parser.add_argument("--test", required=True, type=Path, help="Test/V1 GeoTIFF.")
    parser.add_argument("--mode", choices=("continuous", "class"), default="continuous")
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Continuous mode: percent relative threshold. Class mode: absolute class difference.",
    )
    parser.add_argument("--out-dir", type=Path, default=Path("outputs"))
    parser.add_argument("--name", default=None, help="Output file stem. Defaults to test TIFF stem.")
    parser.add_argument("--png", action="store_true", help="Also write a non-georeferenced PNG preview.")
    args = parser.parse_args()

    threshold = args.threshold
    if threshold is None:
        threshold = 0.0 if args.mode == "class" else 5.0

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stem = args.name or args.test.stem
    result = compare(args.reference, args.test, args.mode, threshold)

    mask_tif = args.out_dir / f"{stem}_fail_mask.tif"
    status_tif = args.out_dir / f"{stem}_status_map.tif"
    summary_csv = args.out_dir / f"{stem}_summary.csv"
    summary_json = args.out_dir / f"{stem}_summary.json"

    write_mask_geotiff(mask_tif, result["profile"], result["fail"])
    write_status_geotiff(
        status_tif,
        result["profile"],
        result["reference_valid"],
        result["test_valid"],
        result["fail"],
    )
    if args.png:
        visual_png = args.out_dir / f"{stem}_fail_pixels.png"
        write_visual_png(
            visual_png,
            result["profile"],
            result["reference_valid"],
            result["test_valid"],
            result["fail"],
        )
    write_summary(summary_csv, result["summary"])
    write_summary(summary_json, result["summary"])

    print(json.dumps(result["summary"], indent=2))
    print(f"mask_tif={mask_tif}")
    print(f"status_tif={status_tif}")
    if args.png:
        print(f"visual_png={visual_png}")
    print(f"summary_csv={summary_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

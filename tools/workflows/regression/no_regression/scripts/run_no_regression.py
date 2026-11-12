#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import datetime as dt
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject


BASE = Path(__file__).resolve().parents[1]
V0_DIR = BASE / "V0_tiffs"
V1_DIR = BASE / "V1_tiffs"
RESULTS = BASE / "no_regression_results.csv"
KEY_RE = re.compile(r"^IRIDE-S_S5-02-(\d{2})_(.+)_V([01])\.tif$")


@dataclass(frozen=True)
class Mode:
    name: str
    threshold: float


def parse_key(path: Path) -> tuple[str, str, str] | None:
    match = KEY_RE.match(path.name)
    if not match:
        return None
    return match.group(1), match.group(2), match.group(3)


def expected_v1_date(product: str, v0_date: str) -> str:
    if product == "03" and re.fullmatch(r"\d{10}", v0_date):
        timestamp = dt.datetime.strptime(v0_date, "%Y%m%d%H")
        return (timestamp - dt.timedelta(hours=1)).strftime("%Y%m%d%H")
    return v0_date


def valid_mask(arr: np.ndarray, mode: Mode) -> np.ndarray:
    nodata = {-999, -10}
    if mode.name == "class":
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
            if len(values):
                result[i, j] = np.min(np.abs(test[i, j] - values))
    return result


def mode_for_product(product: str) -> Mode | None:
    if product == "04":
        return None
    if product in {"05", "06"}:
        return Mode("class", 0.0)
    return Mode("continuous", 5.0)


def compare_pair(product: str, date: str, v1_date: str, v0_path: Path, v1_path: Path) -> dict:
    mode = mode_for_product(product)
    if mode is None:
        return {
            "product": f"S5-02-{product}",
            "date": date,
            "v1_date": v1_date,
            "mode": "excluded",
            "status": "NOT_RUN",
            "no_regression_pct": "",
            "v0_valid_pixels": "",
            "v1_valid_pixels": "",
            "overlap_valid_pixels": "",
            "significant_pixels": "",
        }

    with rasterio.open(v0_path) as src0:
        reference = src0.read(1).astype("float32")
        profile = src0.profile.copy()
        reference_valid = valid_mask(reference, mode)
        reference_clean = np.where(reference_valid, reference, np.nan)

    with rasterio.open(v1_path) as src1:
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
    if mode.name == "class":
        significant = overlap & (diff > mode.threshold)
    else:
        significant = overlap & (diff > (mode.threshold / 100.0) * np.abs(reference_clean))

    overlap_count = int(overlap.sum())
    significant_count = int(significant.sum())
    pct = 100 - (significant_count / overlap_count * 100 if overlap_count else 100)
    return {
        "product": f"S5-02-{product}",
        "date": date,
        "v1_date": v1_date,
        "mode": mode.name,
        "status": "PASS" if pct > 95 else "FAIL",
        "no_regression_pct": f"{pct:.2f}",
        "v0_valid_pixels": int(reference_valid.sum()),
        "v1_valid_pixels": int(test_valid.sum()),
        "overlap_valid_pixels": overlap_count,
        "significant_pixels": significant_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v0-dir", type=Path, default=V0_DIR)
    parser.add_argument("--v1-dir", type=Path, default=V1_DIR)
    parser.add_argument("--output", type=Path, default=RESULTS)
    args = parser.parse_args()

    v0 = {parse_key(path)[:2]: path for path in args.v0_dir.glob("*_V0.tif") if parse_key(path)}
    v1 = {parse_key(path)[:2]: path for path in args.v1_dir.glob("*_V1.tif") if parse_key(path)}

    rows = []
    consumed_v1 = set()
    for product, date in sorted(v0):
        v1_date = expected_v1_date(product, date)
        consumed_v1.add((product, v1_date))
        if (product, date) not in v0:
            rows.append({"product": f"S5-02-{product}", "date": date, "mode": "", "status": "MISSING_V0"})
        elif (product, v1_date) not in v1:
            rows.append({"product": f"S5-02-{product}", "date": date, "v1_date": v1_date, "mode": "", "status": "MISSING_V1"})
        else:
            rows.append(compare_pair(product, date, v1_date, v0[(product, date)], v1[(product, v1_date)]))

    for product, date in sorted(set(v1) - consumed_v1):
        if (product, date) not in v0:
            rows.append({"product": f"S5-02-{product}", "date": "", "v1_date": date, "mode": "", "status": "EXTRA_V1"})

    fields = [
        "product",
        "date",
        "v1_date",
        "mode",
        "status",
        "no_regression_pct",
        "v0_valid_pixels",
        "v1_valid_pixels",
        "overlap_valid_pixels",
        "significant_pixels",
    ]
    with args.output.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    for row in rows:
        pct = f" - {row['no_regression_pct']}%" if row.get("no_regression_pct") else ""
        v1_date = f" v1={row['v1_date']}" if row.get("v1_date") and row.get("v1_date") != row.get("date") else ""
        print(f"{row['product']} {row['date']}{v1_date}: {row['status']}{pct}")
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

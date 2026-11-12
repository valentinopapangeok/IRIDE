#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

import numpy as np
import rasterio
from rasterio.warp import Resampling, reproject


BASE = Path(__file__).resolve().parent
DATE_RE = re.compile(r"_(202610\d{2})_V1\.tif$")
NODATA_VALUES = {-999.0, -99.0, -10.0}


def valid(data: np.ndarray, nodata: float | None) -> np.ndarray:
    mask = np.isfinite(data)
    if nodata is not None:
        mask &= data != nodata
    for value in NODATA_VALUES:
        mask &= data != value
    return mask


def read_aligned(reference_path: Path, candidate_path: Path):
    with rasterio.open(reference_path) as ref:
        reference = ref.read(1).astype("float32")
        ref_profile = {
            "crs": str(ref.crs),
            "transform": tuple(ref.transform),
            "width": ref.width,
            "height": ref.height,
            "bounds": tuple(ref.bounds),
            "nodata": ref.nodata,
            "dtype": ref.dtypes[0],
        }
        reference_valid = valid(reference, ref.nodata)

        with rasterio.open(candidate_path) as cand:
            cand_profile = {
                "crs": str(cand.crs),
                "transform": tuple(cand.transform),
                "width": cand.width,
                "height": cand.height,
                "bounds": tuple(cand.bounds),
                "nodata": cand.nodata,
                "dtype": cand.dtypes[0],
            }
            same_grid = (
                cand.crs == ref.crs
                and cand.transform.almost_equals(ref.transform)
                and cand.width == ref.width
                and cand.height == ref.height
            )
            if same_grid:
                candidate = cand.read(1).astype("float32")
            else:
                candidate = np.full(reference.shape, np.nan, dtype="float32")
                reproject(
                    source=rasterio.band(cand, 1),
                    destination=candidate,
                    src_transform=cand.transform,
                    src_crs=cand.crs,
                    src_nodata=cand.nodata,
                    dst_transform=ref.transform,
                    dst_crs=ref.crs,
                    dst_nodata=np.nan,
                    resampling=Resampling.nearest,
                )
            candidate_valid = valid(candidate, cand.nodata)

    return reference, candidate, reference_valid, candidate_valid, ref_profile, cand_profile, same_grid


def compare(product: str, date: str, prod_path: Path, uat_path: Path) -> dict:
    prod, uat, prod_valid, uat_valid, prod_profile, uat_profile, same_grid = read_aligned(prod_path, uat_path)
    overlap = prod_valid & uat_valid
    union = prod_valid | uat_valid
    row = {
        "product": product,
        "date": date,
        "same_grid": same_grid,
        "prod_valid_pixels": int(prod_valid.sum()),
        "uat_valid_pixels": int(uat_valid.sum()),
        "overlap_pixels": int(overlap.sum()),
        "coverage_iou_pct": float(100 * overlap.sum() / union.sum()) if union.any() else 100.0,
        "prod_profile": json.dumps(prod_profile, default=str),
        "uat_profile": json.dumps(uat_profile, default=str),
    }
    if not overlap.any():
        row.update(status="NO_OVERLAP")
        return row

    p = prod[overlap]
    u = uat[overlap]
    delta = u - p
    row.update(
        prod_min=float(p.min()),
        prod_mean=float(p.mean()),
        prod_max=float(p.max()),
        uat_min=float(u.min()),
        uat_mean=float(u.mean()),
        uat_max=float(u.max()),
        mean_bias=float(delta.mean()),
        mae=float(np.abs(delta).mean()),
        rmse=float(np.sqrt(np.mean(delta ** 2))),
        exact_agreement_pct=float(100 * np.mean(u == p)),
    )
    if product == "02":
        tolerance = np.maximum(np.abs(p) * 0.05, 0.1)
        within = np.abs(delta) <= tolerance
        row.update(
            comparison="continuous",
            within_5pct_or_0_1c_pct=float(100 * within.mean()),
            correlation=float(np.corrcoef(p, u)[0, 1]) if p.size > 1 and np.std(p) and np.std(u) else np.nan,
            status="PASS" if within.mean() >= 0.95 and row["coverage_iou_pct"] >= 95 else "REVIEW",
        )
    else:
        prod_classes, prod_counts = np.unique(p, return_counts=True)
        uat_classes, uat_counts = np.unique(u, return_counts=True)
        agreement = np.mean(u == p)
        row.update(
            comparison="categorical",
            prod_class_counts=json.dumps({str(float(k)): int(v) for k, v in zip(prod_classes, prod_counts)}),
            uat_class_counts=json.dumps({str(float(k)): int(v) for k, v in zip(uat_classes, uat_counts)}),
            status="PASS" if agreement >= 0.95 and row["coverage_iou_pct"] >= 95 else "REVIEW",
        )
    return row


def main() -> int:
    rows = []
    for product in ("02", "05"):
        prod_files = {DATE_RE.search(p.name).group(1): p for p in (BASE / "prod" / product).glob("DAY=*/*.tif") if DATE_RE.search(p.name)}
        uat_files = {DATE_RE.search(p.name).group(1): p for p in (BASE / "uat" / product).glob("DAY=*/*.tif") if DATE_RE.search(p.name)}
        for date in sorted(set(prod_files) & set(uat_files)):
            rows.append(compare(product, date, prod_files[date], uat_files[date]))

    output = BASE / "october_prod_uat_comparison.csv"
    fields = sorted({key for row in rows for key in row})
    with output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    for row in rows:
        metric = row.get("within_5pct_or_0_1c_pct", row.get("exact_agreement_pct", 0.0))
        print(f"S5-02-{row['product']} {row['date']}: {row['status']} metric={metric:.2f}% coverage_iou={row['coverage_iou_pct']:.2f}%")
    print(f"Wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

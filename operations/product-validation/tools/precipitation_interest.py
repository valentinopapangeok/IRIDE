"""Auditable, reference-only prioritisation of product 04 rainy hours.

Run ``select`` before ``score``. Selection never reads product predictions or
comparison metrics. All complete positive-rain gauge pairs remain in scoring.
"""

import argparse
import csv
import hashlib
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from s5validation.precipitation_core import score_pairs

AREAS = ("North", "Center", "South")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def select(results_path):
    outcomes = json.loads(results_path.read_text())
    inventory = Counter(row["status"] for row in outcomes)
    selected = []
    for outcome in outcomes:
        if outcome["status"] != "DIAGNOSTIC":
            continue
        provenance = json.loads(outcome["provenance"])
        method = provenance.get("method", "")
        if method != "regional-gauges-hourly-v3-rainy-only":
            raise ValueError(f"Unexpected comparison method: {method}")
        paths = [Path(p) for p in provenance["artifacts"] if p.endswith("paired_data.json")]
        if len(paths) != 1:
            raise ValueError(f"Expected one pair artifact for {outcome['delivery_id']}")
        path = paths[0]
        pairs = json.loads(path.read_text())
        for area in AREAS:
            # Deliberately do not inspect predicted values, existing metrics or passes.
            rows = [r for r in pairs if r["area"] == area and r["reference"] > 0]
            if not rows:
                continue
            stations = {r["station"] for r in rows}
            pixels = {(r["product_row"], r["product_col"]) for r in rows}
            maximum = max(r["reference"] for r in rows)
            # Support tier for prioritising downloads/reporting, not a replacement
            # for the existing one-pair scientific eligibility rule.
            well_supported = len(stations) >= 10 and len(pixels) >= 5 and maximum >= 1.0
            selected.append({
                "hour_utc": outcome["acquired_at"], "date_utc": outcome["acquired_at"][:10],
                "area": area, "delivery_id": outcome["delivery_id"],
                "pair_path": str(path), "pair_sha256": sha256(path),
                "rainy_pairs": len(rows), "rainy_stations": len(stations),
                "occupied_pixels": len(pixels), "max_gauge_mm": maximum,
                "tier": "well_supported" if well_supported else "limited_support",
            })
    selected.sort(key=lambda r: (r["hour_utc"], AREAS.index(r["area"])))
    return {"protocol": "precipitation-interest-v1", "source": str(results_path),
            "source_sha256": sha256(results_path), "selection_utc": datetime.now(timezone.utc).isoformat(),
            "inventory": dict(inventory), "selection": selected}


def score(manifest):
    output = []
    for item in manifest["selection"]:
        path = Path(item["pair_path"])
        if sha256(path) != item["pair_sha256"]:
            raise ValueError(f"Pair artifact changed since selection: {path}")
        rows = [r for r in json.loads(path.read_text())
                if r["area"] == item["area"] and r["reference"] > 0]
        if len(rows) != item["rainy_pairs"]:
            raise ValueError(f"Reference support changed: {path}")
        metric = score_pairs(rows)
        output.append({k: item[k] for k in ("date_utc", "hour_utc", "area", "tier",
                                           "rainy_pairs", "rainy_stations", "occupied_pixels")}
                      | {"reference_mean_mm": metric["reference_mean_mm"],
                         "rmse_mm": metric["rmse"],
                         "rrmse_pct": metric["relative_rmse_pct"],
                         "passes_20pct": metric["meets_threshold"]})
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("select", "score"))
    parser.add_argument("--results", type=Path)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--csv", type=Path)
    args = parser.parse_args()
    if args.action == "select":
        if args.results is None:
            parser.error("--results is required for select")
        if args.manifest.exists():
            parser.error("Manifest already exists; use a new path for a new frozen selection")
        args.manifest.parent.mkdir(parents=True, exist_ok=True)
        args.manifest.write_text(json.dumps(select(args.results), indent=2) + "\n")
    else:
        if args.csv is None:
            parser.error("--csv is required for score")
        if args.csv.exists():
            parser.error("Score CSV already exists; preserve prior results")
        result = score(json.loads(args.manifest.read_text()))
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with args.csv.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=("date_utc", "hour_utc", "area", "tier",
                                                   "rainy_pairs", "rainy_stations", "occupied_pixels",
                                                   "reference_mean_mm", "rmse_mm", "rrmse_pct", "passes_20pct"))
            writer.writeheader()
            writer.writerows(result)


if __name__ == "__main__":
    main()

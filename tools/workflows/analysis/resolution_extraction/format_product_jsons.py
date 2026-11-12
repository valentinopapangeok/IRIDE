#!/usr/bin/env python3
"""Build date-free formatted product JSONs from extracted product CSV data."""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
CSV_PATH = BASE_DIR / "product_extracted_data_all.csv"
EXTRACTED_JSON_PATH = BASE_DIR / "product_extracted_data_all.json"
OUTPUT_DIR = BASE_DIR / "formatted_product_jsons"
OUTPUT_ALL_PATH = BASE_DIR / "formatted_product_jsons_all.json"


DATE_IN_PRODUCT_ID_RE = re.compile(r"^(IRIDE-S_S5-\d{2}-\d{2})_\d{6,8}_(V\d+)$")


def without_date(product_id: str) -> str:
    match = DATE_IN_PRODUCT_ID_RE.match(product_id)
    if not match:
        return product_id
    return f"{match.group(1)}_{match.group(2)}"


def round_100m(value: str) -> int:
    return int(round(float(value) / 100.0) * 100)


def format_epsg(value: str) -> str:
    if value.upper().startswith("EPSG:") and " " not in value:
        return value.replace(":", ": ", 1)
    return value


def quality_flags_by_id() -> dict[str, list[dict[str, str]]]:
    if not EXTRACTED_JSON_PATH.exists():
        return {}

    extracted_products = json.loads(EXTRACTED_JSON_PATH.read_text(encoding="utf-8"))
    flags: dict[str, list[dict[str, str]]] = {}
    for product in extracted_products:
        quality_flags = product.get("iss:quality_flags")
        if not quality_flags:
            continue
        flags[product["id"]] = [
            {
                "iss:classes": str(flag.get("classes", "")),
                "iss:classes_values": flag.get("classes_values", ""),
            }
            for flag in quality_flags
        ]
    return flags


def formatted_product(row: dict[str, str], flags: list[dict[str, str]] | None) -> dict:
    proj_code = format_epsg(row["proj:code"])
    product = {
        "iss:classes": row["iss:classes"],
        "iss:classes_values": row["iss:classes_values"],
        "iss:stack": row["iss:stack"],
        "iss:spatial_resolution": {
            "max": round_100m(row["tiff_overall_resolution_m_max"]),
            "min": round_100m(row["tiff_overall_resolution_m_min"]),
        },
        "proj:code": proj_code,
        "iss:activation_mode": row["iss:activation_mode"],
        "iss:temporal_resolution": row["iss:temporal_resolution"],
        "properties": {
            "format": row["format"],
            "production_datetime": row["production_datetime"],
            "proj:code": proj_code,
        },
        "product:type": row["product:type"],
        "accuracy:geometric_rmse": row["accuracy:geometric_rmse"],
        "accuracy:measurement_relative": row["accuracy:measurement_relative"],
    }
    if flags:
        product["iss:quality_flags"] = flags
    return product


def main() -> None:
    flags = quality_flags_by_id()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for existing_json in OUTPUT_DIR.glob("*.json"):
        existing_json.unlink()

    formatted_products = {}
    with CSV_PATH.open(newline="", encoding="utf-8") as csv_file:
        for row in csv.DictReader(csv_file):
            formatted_id = without_date(row["id"])
            product = formatted_product(row, flags.get(row["id"]))
            formatted_products[formatted_id] = product
            (OUTPUT_DIR / f"{formatted_id}.json").write_text(
                json.dumps(product, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

    OUTPUT_ALL_PATH.write_text(
        json.dumps(formatted_products, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

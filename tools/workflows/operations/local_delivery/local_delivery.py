#!/usr/bin/env python3
"""Local product 04 delivery flow that mimics svc_s5-02-04 delivery step."""

from __future__ import annotations

import argparse
import asyncio
import json
import shutil
from datetime import datetime
from pathlib import Path
from xml.sax.saxutils import escape

from delivery import delivery


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_stub_metadata_xml(metadata: dict, xml_path: Path) -> None:
    xml_path.parent.mkdir(parents=True, exist_ok=True)
    item_id = escape(str(metadata.get("id", "")))
    dt = escape(str(metadata.get("datetime", "")))
    product_code = escape(str(metadata.get("product_code", "S5-02-04")))
    description = escape(str(metadata.get("description", "")))
    content = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n"
        "<metadata>\n"
        f"  <id>{item_id}</id>\n"
        f"  <product_code>{product_code}</product_code>\n"
        f"  <datetime>{dt}</datetime>\n"
        f"  <description>{description}</description>\n"
        "</metadata>\n"
    )
    xml_path.write_text(content, encoding="utf-8")


def _parse_processing_datetime(metadata: dict) -> datetime:
    raw = str(metadata.get("datetime", "")).strip()
    if not raw:
        raise ValueError("metadata datetime is required")
    normalized = raw.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def _validate_delivery_context(config: dict) -> dict:
    delivery_cfg = config.get("delivery", {})
    delivery_bucket = str(delivery_cfg.get("bucket", "")).strip()
    if not delivery_bucket:
        raise ValueError("config.delivery.bucket is required")

    upload_to = str(delivery_cfg.get("upload_to", "svc")).strip()
    if not upload_to:
        raise ValueError("config.delivery.upload_to cannot be empty")

    bucket_folder = str(delivery_cfg.get("bucket_folder", "ar_delivery")).strip()
    if not bucket_folder:
        raise ValueError("config.delivery.bucket_folder cannot be empty")

    credentials = config.get("credentials", {})
    access_key_id = str(credentials.get("access_key_id", "")).strip()
    secret_access_key = str(credentials.get("secret_access_key", "")).strip()
    if not access_key_id or not secret_access_key:
        raise ValueError("config.credentials.access_key_id and secret_access_key are required")

    style_cfg = config.get("style_assets", {})
    qml_path = Path(style_cfg.get("qml_path", "")).resolve()
    sld_path = Path(style_cfg.get("sld_path", "")).resolve()
    if not qml_path.exists():
        raise FileNotFoundError(f"QML style file not found: {qml_path}")
    if not sld_path.exists():
        raise FileNotFoundError(f"SLD style file not found: {sld_path}")

    return {
        "delivery_bucket": delivery_bucket,
        "upload_to": upload_to,
        "bucket_folder": bucket_folder,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tif", required=True, type=Path, help="Input product 04 GeoTIFF")
    parser.add_argument("--metadata", required=True, type=Path, help="Input metadata JSON")
    parser.add_argument("--config", required=True, type=Path, help="Local delivery config JSON")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).with_name("deliveries"),
        help="Output root directory for local packaged delivery",
    )
    parser.add_argument(
        "--issa-activation-identifier",
        required=True,
        help="Activation identifier used in real 04 delivery",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tif_path = args.tif.resolve()
    if not tif_path.exists():
        raise FileNotFoundError(tif_path)

    metadata = _load_json(args.metadata.resolve())
    config = _load_json(args.config.resolve())
    ctx = _validate_delivery_context(config)
    dt = _parse_processing_datetime(metadata)

    item_id = str(metadata.get("id") or tif_path.stem)
    output_cog = tif_path.name
    tif_dir = args.output_dir.resolve() / "run" / item_id / "tif"
    tif_dir.mkdir(parents=True, exist_ok=True)
    local_tif = tif_dir / output_cog
    shutil.copy2(tif_path, local_tif)

    local_xml = local_tif.with_suffix(".xml")
    _write_stub_metadata_xml(metadata, local_xml)

    xml_configs = {
        "service_frequency": metadata.get("properties", {}).get("iss:temporal_resolution", "hourly"),
        "resolution": config.get("delivery", {}).get("spatial_resolution_value", 1000),
        "uom": config.get("delivery", {}).get("spatial_resolution_uom", "m"),
        "thematic_accuracy": config.get("delivery", {}).get("thematic_accuracy_value", 20),
        "thematic_accuracy_unit": config.get("delivery", {}).get("thematic_accuracy_unit", "relative RMSE"),
        "delivery_bucket": ctx["delivery_bucket"],
        "upload_to": ctx["upload_to"],
        "bucket_folder": ctx["bucket_folder"],
    }

    package_dir = asyncio.run(
        delivery(
            dt=dt,
            tif_dir=str(tif_dir),
            output_cog=output_cog,
            xml_configs=xml_configs,
            issa_activation_identifier=args.issa_activation_identifier,
            config_path=str(args.config.resolve()),
            output_root=str(args.output_dir.resolve()),
        )
    )
    print(f"Local delivery package created: {package_dir}")


if __name__ == "__main__":
    main()

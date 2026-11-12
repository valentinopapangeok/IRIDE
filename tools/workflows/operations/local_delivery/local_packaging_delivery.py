from __future__ import annotations

import hashlib
import json
import shutil
from datetime import timezone
from pathlib import Path
from typing import Any

from local_models import LocalSvcItem


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _copy_assets(exploitation_tool_files: list[Path | str], assets_dir: Path) -> list[dict[str, Any]]:
    copied: list[dict[str, Any]] = []
    assets_dir.mkdir(parents=True, exist_ok=True)
    for raw_path in exploitation_tool_files:
        src = Path(raw_path).resolve()
        if not src.exists():
            raise FileNotFoundError(src)
        dst = assets_dir / src.name
        shutil.copy2(src, dst)
        copied.append(
            {
                "name": dst.name,
                "relative_path": f"assets/{dst.name}",
                "size": dst.stat().st_size,
                "sha256": _sha256(dst),
            }
        )
    return copied


def _build_item_json(
    svc_item: LocalSvcItem,
    copied_assets: list[dict[str, Any]],
    s3_output_bucket: str,
    s3_folder: str,
) -> dict[str, Any]:
    data_asset = next((asset for asset in copied_assets if asset["name"].endswith(".tif")), copied_assets[0])
    href_prefix = f"s3://{s3_output_bucket}/{s3_folder}".rstrip("/")
    data_href = f"{href_prefix}/{data_asset['name']}"
    start_dt, _, end_dt = svc_item.datetime_range
    item = {
        "type": "Feature",
        "stac_version": "1.0.0",
        "stac_extensions": [
            "https://stac-extensions.github.io/file/v2.1.0/schema.json",
            "https://stac-extensions.github.io/projection/v2.0.0/schema.json",
            "https://stac-extensions.github.io/raster/v1.1.0/schema.json",
        ],
        "id": svc_item.item_id,
        "collection": svc_item.collection_id,
        "geometry": svc_item.geometry,
        "bbox": list(svc_item.bbox),
        "properties": {
            "datetime": start_dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "start_datetime": start_dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "end_datetime": end_dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            "description": svc_item.marketplace_description,
            "marketplace_link_id": svc_item.marketplace_link_id,
            "exploitation_tool_link": svc_item.exploitation_tool_link,
            "issa_activation_identifier": svc_item.issa_activation_identifier,
            "issa_update_frequency": svc_item.issa_update_frequency,
            "issa_spatial_resolution": svc_item.issa_spatial_resolution,
            "issa_thematic_accuracy": svc_item.issa_thematic_accuracy,
            "proj:code": svc_item.projection_ext.code,
            "proj:wkt2": svc_item.projection_ext.wkt2,
        },
        "assets": {
            "data": {
                "href": data_href,
                "type": "image/tiff; application=geotiff",
                "roles": ["data"],
                "title": svc_item.assets["data"].title,
                "file:size": data_asset["size"],
                "checksum:sha256": data_asset["sha256"],
            }
        },
    }
    return item


def packaging_delivery(
    svc_item: LocalSvcItem,
    s3_output_bucket: str,
    s3_folder: str,
    exploitation_tool_files: list[Path | str],
    upload_to: str,
    output_root: Path,
) -> Path:
    package_dir = output_root / "deliveries" / upload_to / s3_folder / svc_item.item_id
    assets_dir = package_dir / "assets"
    copied_assets = _copy_assets(exploitation_tool_files, assets_dir)
    stac_item = _build_item_json(svc_item, copied_assets, s3_output_bucket, s3_folder)

    package_dir.mkdir(parents=True, exist_ok=True)
    with (package_dir / "item.json").open("w", encoding="utf-8") as handle:
        json.dump(stac_item, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    manifest = {
        "item_id": svc_item.item_id,
        "target_bucket": s3_output_bucket,
        "target_prefix": s3_folder,
        "upload_to": upload_to,
        "copied_assets": copied_assets,
    }
    with (package_dir / "delivery_manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, indent=2, ensure_ascii=False)
        handle.write("\n")

    return package_dir

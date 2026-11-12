from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

from stac_creation_upload import (
    create_items_to_upload,
    deliver_svc_item,
    generate_thumbnail,
)


def _extract_bbox(local_tif: str) -> tuple[float, float, float, float]:
    import rasterio
    from rasterio.warp import transform_bounds

    with rasterio.open(local_tif) as dataset:
        bounds = dataset.bounds
        if dataset.crs:
            west, south, east, north = transform_bounds(dataset.crs, "EPSG:4326", *bounds, densify_pts=21)
        else:
            west, south, east, north = bounds
        return west, south, east, north


async def delivery(
    dt: datetime,
    tif_dir: str,
    output_cog: str,
    xml_configs: dict,
    issa_activation_identifier: str,
    config_path: str,
    output_root: str,
) -> Path:
    if not issa_activation_identifier:
        raise ValueError("issa_activation_identifier is required for delivery")

    local_tif = f"{tif_dir}/{output_cog}"
    local_png = await generate_thumbnail(local_tif)
    base, _ = os.path.splitext(local_tif)
    local_xml = f"{base}.xml"
    if not os.path.isfile(local_xml):
        raise FileNotFoundError(f"Metadata XML not found: {local_xml}")

    bounding_box = _extract_bbox(local_tif)
    target_date = dt.strftime("%Y%m%d%H")
    start_date = dt
    end_date = start_date + timedelta(hours=1)
    marketplace_description = (
        "IRIDE-S_S5-02-04 Precipitation mapping over Italy with hourly temporal resolution"
    )

    svc_item = await create_items_to_upload(
        local_tif=local_tif,
        local_xml=local_xml,
        local_png=local_png,
        target_date=target_date,
        bounding_box=bounding_box,
        start_date=start_date,
        end_date=end_date,
        marketplace_description=marketplace_description,
        xml_configs=xml_configs,
        issa_activation_identifier=issa_activation_identifier,
        config_path=config_path,
    )

    exploitation_tool_files = [
        svc_item.assets["data"].path,
        svc_item.metadata.path,
        svc_item.assets["data_qml"].path,
        svc_item.assets["data_sld"].path,
        svc_item.thumbnail.path,
    ]

    s3_output_bucket = xml_configs.get("delivery_bucket")
    if not s3_output_bucket:
        raise ValueError("xml_configs.delivery_bucket is required for delivery")

    package_dir = await deliver_svc_item(
        svc_item=svc_item,
        s3_output_bucket=s3_output_bucket,
        target_date=dt,
        upload_to=xml_configs.get("upload_to", "svc"),
        bucket_folder=xml_configs.get("bucket_folder", "ar_delivery"),
        exploitation_tool_files=exploitation_tool_files,
        output_root=output_root,
    )
    return package_dir

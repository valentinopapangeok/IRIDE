from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import numpy as np
from shapely.geometry import box, mapping

from local_models import (
    LocalAsset,
    LocalMetadataAsset,
    LocalProjectionExt,
    LocalSvcItem,
    LocalThumbnailAsset,
)
from local_packaging_delivery import packaging_delivery


PRODUCT_VERSION = "V0"
PRODUCT_CODE = "S5-02-04"


async def generate_thumbnail(tiff_path: str, size: tuple[int, int] = (256, 256)) -> str:
    base, _ = os.path.splitext(tiff_path)
    thumbnail_path = f"{base}.png"
    try:
        from PIL import Image

        with Image.open(tiff_path) as img:
            arr = np.array(img)
            rgba = np.zeros((arr.shape[0], arr.shape[1], 4), dtype=np.uint8)
            nodata_mask = (arr == -999) | ~np.isfinite(arr)
            valid = np.clip(arr, 0, 10).astype(np.float32)
            norm = valid / 10.0
            rgba[:, :, 0] = 255 * (1 - norm)
            rgba[:, :, 1] = 255 * (1 - norm)
            rgba[:, :, 2] = 255
            rgba[:, :, 3] = 255
            rgba[nodata_mask, 3] = 0
            thumbnail = Image.fromarray(rgba.astype(np.uint8), mode="RGBA")
            thumbnail.thumbnail(size)
            thumbnail.save(thumbnail_path, "PNG")
    except ImportError:
        try:
            import matplotlib.pyplot as plt

            arr = np.zeros((size[1], size[0], 4), dtype=np.uint8)
            arr[:, :, 3] = 0
            plt.imsave(thumbnail_path, arr)
        except Exception:
            # Last-resort valid 1x1 transparent PNG.
            Path(thumbnail_path).write_bytes(
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01"
                b"\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
                b"\x00\x00\x00\x0bIDATx\x9cc```\x00\x00\x00\x04\x00\x01"
                b"\x0b\xe7\x02\x9d\x00\x00\x00\x00IEND\xaeB`\x82"
            )
    return thumbnail_path


def _read_json(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _resolve_style_assets(config: dict, output_dir: Path) -> tuple[str, str]:
    style = config.get("style_assets", {})
    qml_src = style.get("qml_path")
    sld_src = style.get("sld_path")
    if not qml_src or not sld_src:
        raise ValueError("config.style_assets.qml_path and config.style_assets.sld_path are required")
    qml_path = Path(qml_src).resolve()
    sld_path = Path(sld_src).resolve()
    if not qml_path.exists():
        raise FileNotFoundError(qml_path)
    if not sld_path.exists():
        raise FileNotFoundError(sld_path)
    qml_dst = output_dir / qml_path.name
    sld_dst = output_dir / sld_path.name
    qml_dst.write_bytes(qml_path.read_bytes())
    sld_dst.write_bytes(sld_path.read_bytes())
    return str(qml_dst), str(sld_dst)


async def create_items_to_upload(
    local_tif: str,
    local_xml: str,
    local_png: str,
    target_date: str,
    bounding_box: tuple[float, float, float, float],
    start_date: datetime,
    end_date: datetime,
    marketplace_description: str,
    epsg_code: str = "EPSG:4326",
    xml_configs: dict | None = None,
    issa_activation_identifier: str | None = None,
    config_path: str | None = None,
) -> LocalSvcItem:
    if not issa_activation_identifier:
        raise ValueError("issa_activation_identifier is required")
    if not xml_configs:
        raise ValueError("xml_configs is required")
    if not config_path:
        raise ValueError("config_path is required")

    config = _read_json(config_path)
    output_dir = Path(local_png).resolve().parent
    qml_file, sld_file = _resolve_style_assets(config, output_dir)

    min_lon, min_lat, max_lon, max_lat = bounding_box
    wkt_polygon = (
        f"POLYGON (({min_lon} {min_lat}, {max_lon} {min_lat}, "
        f"{max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))"
    )
    projection = LocalProjectionExt(code=epsg_code, wkt2=wkt_polygon)
    shapely_geom = box(min_lon, min_lat, max_lon, max_lat)
    geojson_geom = mapping(shapely_geom)

    item_id = f"IRIDE-S_S5-02-04_{target_date}_{PRODUCT_VERSION}"
    collection_id = config.get("delivery", {}).get("collection_id", "OU-S5-02-04")
    link_id = config.get("delivery", {}).get(
        "marketplace_link_id",
        "hydro-meteorology-climate/se-s5-02/ou-s5-02-04",
    )
    et_link = config.get("delivery", {}).get(
        "exploitation_tool_link",
        "https://replace-with-et-link.example/s5_02",
    )

    svc_item = LocalSvcItem(
        item_id=item_id,
        collection_id=collection_id,
        geometry=geojson_geom,
        bbox=shapely_geom.bounds,
        datetime_range=(start_date, start_date, end_date),
        assets={
            "data": LocalAsset(path=local_tif, title=os.path.basename(local_tif)),
            "data_qml": LocalAsset(path=qml_file, title=f"{collection_id}--QML"),
            "data_sld": LocalAsset(path=sld_file, title=f"{collection_id}--SLD"),
        },
        metadata=LocalMetadataAsset(path=local_xml, title=os.path.basename(local_xml)),
        thumbnail=LocalThumbnailAsset(
            path=local_png,
            title=os.path.basename(local_png),
            description=f"256x256 pixel PNG thumbnail of {os.path.basename(local_tif)}",
        ),
        projection_ext=projection,
        marketplace_description=marketplace_description,
        exploitation_tool_link=et_link,
        marketplace_link_id=link_id,
        issa_activation_identifier=issa_activation_identifier,
        issa_update_frequency=xml_configs.get("service_frequency", "hourly"),
        issa_spatial_resolution={
            "value": int(xml_configs.get("resolution", 1000)),
            "unit": xml_configs.get("uom", "m"),
        },
        issa_thematic_accuracy={
            "value": int(xml_configs.get("thematic_accuracy", 20)),
            "unit": xml_configs.get("thematic_accuracy_unit", "relative RMSE"),
        },
    )
    return svc_item


async def deliver_svc_item(
    svc_item: LocalSvcItem,
    s3_output_bucket: str,
    target_date: datetime,
    upload_to: str = "svc",
    bucket_folder: str = "ar_delivery",
    exploitation_tool_files: list[Path | str] | None = None,
    output_root: str | Path = ".",
) -> Path:
    if not s3_output_bucket:
        raise ValueError("s3_output_bucket is required")

    upload_to = str(upload_to).strip() or "svc"
    bucket_folder = str(bucket_folder).strip() or "ar_delivery"

    s3_folder = (
        f"{bucket_folder}/YEAR={target_date.year:04d}/"
        f"MONTH={target_date.month:02d}/DAY={target_date.day:02d}"
    )
    if exploitation_tool_files is None:
        exploitation_tool_files = [
            svc_item.assets["data"].path,
            svc_item.metadata.path,
            svc_item.assets["data_qml"].path,
            svc_item.assets["data_sld"].path,
            svc_item.thumbnail.path,
        ]
    return packaging_delivery(
        svc_item=svc_item,
        s3_output_bucket=s3_output_bucket,
        s3_folder=s3_folder,
        exploitation_tool_files=exploitation_tool_files,
        upload_to=upload_to,
        output_root=Path(output_root),
    )

#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import logging
import posixpath
import re
import warnings
import zipfile
from datetime import datetime, time, timezone
from pathlib import Path, PurePosixPath
from typing import Any

import boto3
from urllib3.exceptions import InsecureRequestWarning


warnings.simplefilter("ignore", InsecureRequestWarning)

LOGGER = logging.getLogger("local_dco_download")


def normalize_activation_catalog_path(input_path: str) -> str:
    input_path = (input_path or "").strip()
    if not input_path:
        raise ValueError("input_path is required")
    if input_path.rstrip("/").endswith("/catalog.json"):
        return input_path.rstrip("/")
    return f"{input_path.rstrip('/')}/catalog.json"


def _normalize_path(path: str) -> str:
    return path.removeprefix("/").removesuffix("/")


def _join_path(*parts: str) -> str:
    return "/".join(part.strip("/") for part in parts if part and part.strip("/"))


def _parse_activation_catalog_path(path: str) -> tuple[str, str, str]:
    normalized = path.removeprefix("s3://") if path.startswith("s3://") else _normalize_path(path)
    pure_path = PurePosixPath(normalized)
    if len(pure_path.parts) < 2:
        raise ValueError("Activation catalog path must include the bucket name and end with 'catalog.json'.")

    bucket_name = pure_path.parts[0]
    root_catalog_path = _join_path(*pure_path.parts[1:])
    root_catalog = PurePosixPath(root_catalog_path)
    if root_catalog.name != "catalog.json" or root_catalog.parent == PurePosixPath("."):
        raise ValueError("Activation catalog path must point to the activation root 'catalog.json' file.")

    activation_root = root_catalog.parent.as_posix()
    return bucket_name, root_catalog.as_posix(), activation_root


def _parse_datetime_value(value: Any, *, end_boundary: bool = False) -> datetime | None:
    if value is None:
        return None

    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        raw = value.strip()
        if not raw:
            return None
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
            date_obj = datetime.strptime(raw, "%Y-%m-%d").date()
            if end_boundary:
                return datetime.combine(date_obj, time(23, 59, 59, 999999), tzinfo=timezone.utc)
            return datetime.combine(date_obj, time.min, tzinfo=timezone.utc)
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    else:
        return None

    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _asset_intersects(
    asset: dict[str, Any],
    query_start: datetime | None,
    query_end: datetime | None,
) -> bool:
    if query_start is None and query_end is None:
        return True

    asset_start = _parse_datetime_value(asset.get("start_datetime")) or _parse_datetime_value(asset.get("datetime"))
    asset_end = _parse_datetime_value(asset.get("end_datetime")) or _parse_datetime_value(asset.get("datetime"))

    if asset_start is None and asset_end is None:
        return True

    if asset_start is None:
        asset_start = asset_end
    if asset_end is None:
        asset_end = asset_start

    if query_start is not None and asset_end is not None and asset_end < query_start:
        return False
    if query_end is not None and asset_start is not None and asset_start > query_end:
        return False
    return True


def _make_s3_client(endpoint: str, access_key_id: str, secret_access_key: str):
    return boto3.client(
        "s3",
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        endpoint_url=endpoint,
        verify=False,
    )


def _read_json_from_s3(client, bucket: str, key: str) -> dict[str, Any]:
    response = client.get_object(Bucket=bucket, Key=key)
    body = response["Body"].read()
    if isinstance(body, bytes):
        return json.loads(body.decode("utf-8"))
    return json.loads(str(body))


def _resolve_href(base_bucket_path: str, href: str) -> str:
    if "://" in href:
        return href

    normalized_base = _normalize_path(base_bucket_path)
    if href.startswith("/"):
        return _normalize_path(href)

    return _normalize_path(posixpath.normpath(posixpath.join(posixpath.dirname(normalized_base), href)))


def _child_catalog_refs(parent_bucket_path: str, parent_json: dict[str, Any], client, bucket_name: str) -> list[tuple[str, str, dict[str, Any]]]:
    refs: list[tuple[str, str, dict[str, Any]]] = []
    for link in parent_json.get("links", []):
        if link.get("rel") != "child" or link.get("href") is None:
            continue

        child_bucket_path = _resolve_href(parent_bucket_path, str(link["href"]))
        child_json = _read_json_from_s3(client, bucket_name, child_bucket_path)
        if child_json.get("type") != "Catalog":
            continue

        refs.append((PurePosixPath(child_bucket_path).parent.name, child_bucket_path, child_json))

    refs.sort(key=lambda ref: ref[0])
    return refs


def _has_item_links(catalog_json: dict[str, Any]) -> bool:
    return any(link.get("rel") == "item" for link in catalog_json.get("links", []))


def _input_container_refs(
    parent_bucket_path: str,
    parent_json: dict[str, Any],
    client,
    bucket_name: str,
) -> list[tuple[str, str, dict[str, Any]]]:
    return [ref for ref in _child_catalog_refs(parent_bucket_path, parent_json, client, bucket_name) if _has_item_links(ref[2])]


def _shared_container_refs(psg_bucket_path: str, psg_json: dict[str, Any], client, bucket_name: str) -> list[tuple[str, str, dict[str, Any]]]:
    refs: list[tuple[str, str, dict[str, Any]]] = []
    for child_name, child_bucket_path, child_json in _child_catalog_refs(psg_bucket_path, psg_json, client, bucket_name):
        if _has_item_links(child_json):
            refs.append((child_name, child_bucket_path, child_json))
            continue
        if child_name.isdigit():
            continue
        refs.extend(_input_container_refs(child_bucket_path, child_json, client, bucket_name))

    refs.sort(key=lambda ref: ref[0])
    return refs


def _container_item_refs(
    container_bucket_path: str,
    container_json: dict[str, Any],
    client,
    bucket_name: str,
) -> list[tuple[str, dict[str, Any]]]:
    refs: list[tuple[str, dict[str, Any]]] = []
    for link in container_json.get("links", []):
        if link.get("rel") != "item" or link.get("href") is None:
            continue

        item_bucket_path = _resolve_href(container_bucket_path, str(link["href"]))
        item_json = _read_json_from_s3(client, bucket_name, item_bucket_path)
        if item_json.get("type") != "Feature":
            raise TypeError(f"Expected a STAC Item at '{item_bucket_path}', got {item_json.get('type')!r}")
        refs.append((item_bucket_path, item_json))

    refs.sort(key=lambda item_ref: str(item_ref[1].get("id", "")))
    return refs


def _extract_datetime_string(item_json: dict[str, Any], key: str) -> str | None:
    value = item_json.get("properties", {}).get(key)
    if isinstance(value, str) and value:
        return value
    if key == "datetime":
        value = item_json.get("properties", {}).get("datetime") or item_json.get("datetime")
    dt = _parse_datetime_value(value)
    return None if dt is None else dt.isoformat()


def _asset_to_dict(
    *,
    bucket_name: str,
    activation_root: str,
    psg_id: str | int,
    ps_id: str | int | None,
    dataset_name: str,
    container_json: dict[str, Any],
    item_json: dict[str, Any],
    item_bucket_path: str,
    asset_key: str,
) -> dict[str, Any]:
    asset = item_json.get("assets", {}).get(asset_key, {})
    href = str(asset.get("href", ""))
    resolved_href = _resolve_href(item_bucket_path, href)
    return {
        "sm_service_request_id": activation_root,
        "bucket_name": bucket_name,
        "psg_id": str(psg_id),
        "ps_id": None if ps_id is None else str(ps_id),
        "dataset_id": dataset_name,
        "collection_id": container_json.get("id"),
        "dco_data_code": container_json.get("dco_data_code") or item_json.get("properties", {}).get("dco_data_code"),
        "item_id": item_json.get("id"),
        "asset_key": asset_key,
        "href": href,
        "resolved_href": resolved_href,
        "media_type": asset.get("media_type"),
        "title": asset.get("title"),
        "roles": list(asset.get("roles") or []),
        "datetime": _extract_datetime_string(item_json, "datetime"),
        "start_datetime": _extract_datetime_string(item_json, "start_datetime"),
        "end_datetime": _extract_datetime_string(item_json, "end_datetime"),
    }


def get_input_with_temporal_params(
    activation_catalog_path: str,
    psg_id: str | int,
    ps_id: str | int | None = None,
    start_datetime: datetime | str | None = None,
    end_datetime: datetime | str | None = None,
    *,
    endpoint: str,
    access_key_id: str,
    secret_access_key: str,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    if limit is not None and limit < 1:
        raise ValueError("limit must be greater than or equal to 1")

    bucket_name, root_catalog_path, activation_root = _parse_activation_catalog_path(activation_catalog_path)
    client = _make_s3_client(endpoint, access_key_id, secret_access_key)

    root_json = _read_json_from_s3(client, bucket_name, root_catalog_path)
    if root_json.get("type") != "Catalog":
        raise TypeError(f"Expected a STAC Catalog at '{root_catalog_path}', got {root_json.get('type')!r}")

    if ps_id is not None:
        ps_bucket_path = _join_path(activation_root, str(psg_id), str(ps_id), "catalog.json")
        ps_json = _read_json_from_s3(client, bucket_name, ps_bucket_path)
        if ps_json.get("type") != "Catalog":
            raise TypeError(f"Expected a STAC Catalog at '{ps_bucket_path}', got {ps_json.get('type')!r}")
        selected_refs = _input_container_refs(ps_bucket_path, ps_json, client, bucket_name)
        selected_ps_id: str | int | None = ps_id
    else:
        psg_bucket_path = _join_path(activation_root, str(psg_id), "catalog.json")
        psg_json = _read_json_from_s3(client, bucket_name, psg_bucket_path)
        if psg_json.get("type") != "Catalog":
            raise TypeError(f"Expected a STAC Catalog at '{psg_bucket_path}', got {psg_json.get('type')!r}")
        selected_refs = _shared_container_refs(psg_bucket_path, psg_json, client, bucket_name)
        selected_ps_id = None

    query_start = _parse_datetime_value(start_datetime, end_boundary=False)
    query_end = _parse_datetime_value(end_datetime, end_boundary=True)
    if query_start is not None and query_end is not None and query_end < query_start:
        raise ValueError("'end_datetime' must be greater than or equal to 'start_datetime'.")

    inputs: list[dict[str, Any]] = []
    for dataset_name, container_bucket_path, container_json in selected_refs:
        for item_bucket_path, item_json in _container_item_refs(container_bucket_path, container_json, client, bucket_name):
            for asset_key in sorted(item_json.get("assets", {}).keys()):
                asset_dict = _asset_to_dict(
                    bucket_name=bucket_name,
                    activation_root=activation_root,
                    psg_id=psg_id,
                    ps_id=selected_ps_id,
                    dataset_name=dataset_name,
                    container_json=container_json,
                    item_json=item_json,
                    item_bucket_path=item_bucket_path,
                    asset_key=asset_key,
                )
                if _asset_intersects(asset_dict, query_start, query_end):
                    inputs.append(asset_dict)
                    if limit is not None and len(inputs) >= limit:
                        return inputs

    inputs.sort(key=lambda asset: (asset["dataset_id"], asset["item_id"], asset["asset_key"]))
    if limit is not None:
        return inputs[:limit]
    return inputs


def split_s3_asset_href(href: str) -> tuple[str, str] | None:
    href = (href or "").strip()
    if not href:
        return None
    if href.startswith("s3://"):
        bucket_key = href.removeprefix("s3://")
    elif href.startswith("/"):
        bucket_key = href.lstrip("/")
    else:
        return None

    if "/" not in bucket_key:
        return None
    bucket, key = bucket_key.split("/", 1)
    return bucket, key


def get_local_asset_name(href: str) -> str:
    return href.rstrip("/").split("/")[-1]


def _validate_downloaded_asset(local_path: Path) -> None:
    suffix = local_path.suffix.lower()
    if not local_path.exists() or local_path.stat().st_size == 0:
        raise FileNotFoundError(f"Downloaded file is missing or empty: {local_path}")

    if suffix == ".zip":
        with zipfile.ZipFile(local_path, "r") as zf:
            bad_file = zf.testzip()
            if bad_file:
                raise zipfile.BadZipFile(f"CRC check failed for {bad_file}")
        return

    if suffix in {".h5", ".he5"}:
        import h5py

        with h5py.File(local_path, "r") as handle:
            if not handle.keys():
                raise ValueError(f"HDF5/HE5 file is empty or unreadable: {local_path}")
        return

    if suffix == ".hdf":
        from pyhdf.SD import SD, SDC

        sd = SD(str(local_path), SDC.READ)
        try:
            if not sd.datasets():
                raise ValueError(f"HDF4 file has no datasets: {local_path}")
        finally:
            sd.end()
        return

    if suffix in {".nc", ".nc4"}:
        import netCDF4

        with netCDF4.Dataset(local_path, "r") as ds:
            if not ds.variables:
                raise ValueError(f"NetCDF file has no variables: {local_path}")
        return

    if suffix in {".tif", ".tiff"}:
        import rasterio

        with rasterio.open(local_path) as ds:
            if ds.count == 0:
                raise ValueError(f"TIF file has no bands: {local_path}")
        return

    if suffix == ".gz":
        import gzip

        with gzip.open(local_path, "rb") as gz:
            gz.read(1024)
        return

    if suffix in {".grib", ".grib2", ".grb", ".grb2"}:
        try:
            import eccodes
        except ImportError:
            return

        count = 0
        with open(local_path, "rb") as handle:
            while True:
                msg_id = eccodes.codes_grib_new_from_file(handle)
                if msg_id is None:
                    break
                try:
                    eccodes.codes_get(msg_id, "edition")
                    eccodes.codes_get(msg_id, "shortName")
                    eccodes.codes_get_values(msg_id)
                    count += 1
                finally:
                    eccodes.codes_release(msg_id)
        if count == 0:
            raise ValueError(f"GRIB file contains no valid messages: {local_path}")
        return


def download_dco_inputs(
    *,
    input_path: str,
    filter_date: str,
    psg_id: str,
    ps_id: str | None,
    endpoint: str,
    access_key_id: str,
    secret_access_key: str,
    output_dir: str | Path,
    validate: bool = True,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    activation_catalog_path = normalize_activation_catalog_path(input_path)
    output_root = Path(output_dir).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    LOGGER.info("Loading DCO activation catalog: %s", activation_catalog_path)
    LOGGER.info("Filtering DCO inputs for date %s, PSG %s, PS %s", filter_date, psg_id, ps_id)

    selected_assets = get_input_with_temporal_params(
        activation_catalog_path=activation_catalog_path,
        psg_id=psg_id,
        ps_id=ps_id,
        start_datetime=filter_date,
        end_datetime=filter_date,
        endpoint=endpoint,
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
        limit=limit,
    )

    LOGGER.info("Matched %s DCO assets", len(selected_assets))
    if limit is not None:
        LOGGER.info("Applying limit=%s; downloading %s asset(s)", limit, len(selected_assets))

    s3_client = _make_s3_client(endpoint, access_key_id, secret_access_key)

    downloaded: list[dict[str, Any]] = []
    for asset in selected_assets:
        resolved_href = asset["resolved_href"]
        bucket_key = split_s3_asset_href(resolved_href)
        if bucket_key is None:
            bucket = str(asset["bucket_name"])
            key = _normalize_path(resolved_href)
        else:
            bucket, key = bucket_key
        item_folder = output_root / str(asset["dataset_id"]) / str(asset["item_id"]) / str(asset["asset_key"])
        item_folder.mkdir(parents=True, exist_ok=True)
        local_path = item_folder / get_local_asset_name(resolved_href)

        LOGGER.info("Downloading %s -> %s", resolved_href, local_path)
        s3_client.download_file(bucket, key, str(local_path))
        if validate:
            _validate_downloaded_asset(local_path)

        downloaded.append({**asset, "local_path": str(local_path)})

    manifest_path = output_root / "dco_local_download_manifest.json"
    manifest_path.write_text(json.dumps(downloaded, indent=2, ensure_ascii=False), encoding="utf-8")
    LOGGER.info("Wrote manifest: %s", manifest_path)
    return downloaded


def download_single_item_asset(
    *,
    item_json_path: str | Path,
    endpoint: str,
    access_key_id: str,
    secret_access_key: str,
    output_dir: str | Path,
    asset_key: str = "data",
    validate: bool = True,
) -> dict[str, Any]:
    item = json.loads(Path(item_json_path).read_text(encoding="utf-8"))
    asset = item.get("assets", {}).get(asset_key)
    if not asset:
        raise KeyError(f"Asset {asset_key!r} not found in item JSON")

    href = str(asset.get("href", "")).strip()
    bucket_key = split_s3_asset_href(href)
    if bucket_key is None:
        raise ValueError(f"Asset href must be an s3:// path, got {href!r}")
    bucket, key = bucket_key

    out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    local_path = out_dir / get_local_asset_name(href)

    client = _make_s3_client(endpoint, access_key_id, secret_access_key)
    LOGGER.info("Downloading item asset %s -> %s", href, local_path)
    client.download_file(bucket, key, str(local_path))
    if validate:
        _validate_downloaded_asset(local_path)

    result = {
        "item_id": item.get("id"),
        "collection": item.get("collection"),
        "asset_key": asset_key,
        "href": href,
        "local_path": str(local_path),
    }
    Path(out_dir / "single_asset_manifest.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download and validate DCO inputs locally.")
    parser.add_argument("--config", required=True, type=Path, help="Local JSON config file")
    parser.add_argument("--limit", type=int, default=None, help="Optional maximum number of assets to download")
    parser.add_argument("--item-json", type=Path, default=None, help="Optional direct STAC item JSON for single-asset download")
    parser.add_argument("--asset-key", default="data", help="Asset key to download from the item JSON")
    return parser.parse_args()


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    args = parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if args.item_json is not None:
        download_single_item_asset(
            item_json_path=args.item_json,
            endpoint=config["endpoint"],
            access_key_id=config["access_key_id"],
            secret_access_key=config["secret_access_key"],
            output_dir=config.get("output_dir", args.config.with_name("downloads")),
            asset_key=args.asset_key,
            validate=bool(config.get("validate", True)),
        )
        return 0

    download_dco_inputs(
        input_path=config["input_path"],
        filter_date=config["filter_date"],
        psg_id=str(config["psg_id"]),
        ps_id=None if config.get("ps_id") in {None, "", "null"} else str(config["ps_id"]),
        endpoint=config["endpoint"],
        access_key_id=config["access_key_id"],
        secret_access_key=config["secret_access_key"],
        output_dir=config.get("output_dir", args.config.with_name("downloads")),
        validate=bool(config.get("validate", True)),
        limit=args.limit if args.limit is not None else config.get("limit"),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

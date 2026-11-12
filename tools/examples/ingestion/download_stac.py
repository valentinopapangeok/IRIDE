import warnings
from urllib3.exceptions import InsecureRequestWarning
import os
import boto3
import pystac
from pystac import StacIO
from prefect_common import svc_task
from prefect.logging import get_run_logger
from prefect_common import capture_logs

# -----------------------------
# Disable HTTPS warnings
# -----------------------------
warnings.simplefilter('ignore', InsecureRequestWarning)

# -----------------------------
# Custom StacIO for S3
class CustomS3IO(StacIO):
    s3_client = None
    @classmethod
    def set_s3_client(cls, client):
        cls.s3_client = client

    def read_text(self, source: str) -> str:
        if source.startswith("s3://"):
            path = source.replace("s3://", "")
            bucket, key = path.split("/", 1)
            obj = self.s3_client.get_object(Bucket=bucket, Key=key)
            return obj['Body'].read().decode('utf-8')
        raise ValueError(f"Unsupported href for STAC read: {source}")


    def write_text(self, dest: str, txt: str) -> None:
        # minimal implementation to satisfy abstract base class
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as f:
            f.write(txt)


# -----------------------------
# Main download function (filter by item datetime)
# -----------------------------

@svc_task
async def download_stac(
    input_path: str,
    aws_access_key_id: str,
    aws_secret_access_key: str,
    s3_endpoint: str,
    filter_date: str,
    local_download_dir: str
):
    """
    Downloads assets from a STAC catalog stored on S3 where the STAC item `datetime`
    property matches a specified date. The function inspects the catalog recursively
    and attempts to download all matching asset HREFs to a local directory. It returns
    a boolean indicating whether any assets were successfully downloaded.

    This task is typically used to fetch remote sensing or geospatial assets filtered
    by acquisition date from a catalog-compatible S3 bucket.

    Parameters
    ----------
    input_path : str
        The S3 path (e.g. 's3://my-bucket/path/to/catalog') to the folder containing
        the root `catalog.json` file.
        The function assumes that `catalog.json` is located directly at
        ``<input_path>/catalog.json``.

    aws_access_key_id : str
        AWS access key ID with sufficient permissions to read from the bucket
        where the STAC catalog and assets reside.

    aws_secret_access_key : str
        AWS secret access key paired with `aws_access_key_id`.

    s3_endpoint : str
        The S3-compatible endpoint URL (e.g., MinIO, AWS S3, or another object
        storage service). Used by boto3 to connect to the correct S3 endpoint.

    filter_date : str
        Date string in the format ``"YYYY-MM-DD"``. Only STAC items whose
        `item.properties["datetime"]` begins with this string are considered
        for asset download.

    local_download_dir : str
        Local directory path where downloaded assets will be saved.
        The directory is created if it does not exist.

    Returns
    -------
    bool
        ``True`` if at least one asset is successfully downloaded,
        ``False`` if no matching items or assets were found or downloaded.

    Raises
    ------
    Any exception raised by:
      - `pystac.Catalog.from_file` if the catalog is inaccessible or invalid.
      - `boto3.client(...).download_file` if S3 permissions or connectivity issues occur.

    """

    logger = get_run_logger()
    downloaded_any = False

    with capture_logs(code='S5-02-MG01-MB01', products='S5-02-01', logger=logger):

        root_catalog_path = os.path.join(input_path, "catalog.json")

        s3_client = boto3.client(
            "s3",
            aws_access_key_id=aws_access_key_id,
            aws_secret_access_key=aws_secret_access_key,
            endpoint_url=s3_endpoint,
            verify=False
        )

        CustomS3IO.set_s3_client(s3_client)
        pystac.StacIO.set_default(CustomS3IO)

        logger.info(f"Loading STAC catalog: {root_catalog_path}")
        root_catalog = pystac.Catalog.from_file(root_catalog_path)

        # Helper function
        def download_asset(asset_href: str):
            nonlocal downloaded_any  # so we can update it here

            if asset_href.startswith("./"):
                path_parts = root_catalog_path.replace("s3://", "").split("/")
                bucket = path_parts[0]
                base_prefix = "/".join(path_parts[1:-1])
                key = f"{base_prefix}/{asset_href[2:]}"
            elif asset_href.startswith("s3://"):
                path = asset_href.replace("s3://", "")
                bucket, key = path.split("/", 1)
            else:
                logger.info(f"Skipping {asset_href}")
                return

            local_path = os.path.join(local_download_dir, os.path.basename(asset_href))
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            logger.info(f"Downloading {asset_href} -> {local_path}")
            s3_client.download_file(bucket, key, local_path)
            downloaded_any = True  # <-- mark that something was downloaded

        # Iterate items
        for item in root_catalog.get_all_items():
            item_datetime = item.properties.get("datetime", "")
            if not item_datetime.startswith(filter_date):
                continue

            logger.info(f"Downloading assets for item {item.id} with datetime {item_datetime}")
            for _, asset in item.assets.items():
                download_asset(asset.href)

        logger.info("Filtered assets downloaded.")
        return downloaded_any

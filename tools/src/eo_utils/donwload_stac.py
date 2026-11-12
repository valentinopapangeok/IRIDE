import warnings
from urllib3.exceptions import InsecureRequestWarning
import os
import boto3
import pystac

from pystac import StacIO
from datetime import datetime


# -----------------------------
# Disable HTTPS warnings
# -----------------------------
warnings.simplefilter('ignore', InsecureRequestWarning)

# -----------------------------
# Custom StacIO for S3
# -----------------------------
class CustomS3IO(StacIO):
    s3_client = None  # class-level variable

    @classmethod
    def set_s3_client(cls, client):
        cls.s3_client = client

    def read_text(self, source: str) -> str:
        if source.startswith("s3://"):
            path = source.replace("s3://", "")
            bucket, key = path.split("/", 1)
            obj = self.s3_client.get_object(Bucket=bucket, Key=key)
            return obj['Body'].read().decode('utf-8')
        return super().read_text(source)

    def write_text(self, dest: str, txt: str) -> None:
        super().write_text(dest, txt)


# -----------------------------
# Main download function (filter by item datetime)
# -----------------------------
def download_stac(
    input_path: str,
    aws_access_key_id: str,
    aws_secret_access_key: str,
    s3_endpoint: str,
    filter_date: str,  # format: YYYY-MM-DD
    local_download_dir: str
):
    """
    Download assets from a STAC catalog on S3 for items whose `datetime` property matches filter_date.

    Parameters:
        input_path (str): S3 folder containing catalog.json
        aws_access_key_id (str)
        aws_secret_access_key (str)
        s3_endpoint (str)
        filter_date (str): Only download items with this datetime (format 'YYYY-MM-DD')
        local_download_dir (str)
    """

    # Construct catalog path
    root_catalog_path = os.path.join(input_path, "catalog.json")

    # Set up S3 client
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        endpoint_url=s3_endpoint,
        verify=False
    )

    # Register CustomS3IO
    CustomS3IO.set_s3_client(s3_client)
    pystac.StacIO.set_default(CustomS3IO)

    # Load catalog
    print(f"Loading STAC catalog: {root_catalog_path}")
    root_catalog = pystac.Catalog.from_file(root_catalog_path)

    # -----------------------------
    # Helper function to download an asset
    # -----------------------------
    def download_asset(asset_href: str):
        # Resolve S3 bucket and key
        if asset_href.startswith("./"):
            path_parts = root_catalog_path.replace("s3://", "").split("/")
            bucket = path_parts[0]
            base_prefix = "/".join(path_parts[1:-1])
            key = f"{base_prefix}/{asset_href[2:]}"  # remove "./"
        elif asset_href.startswith("s3://"):
            path = asset_href.replace("s3://", "")
            bucket, key = path.split("/", 1)
        else:
            print(f"Skipping {asset_href}")
            return

        local_path = os.path.join(local_download_dir, os.path.basename(asset_href))
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        print(f"Downloading {asset_href} -> {local_path}")
        s3_client.download_file(bucket, key, local_path)

    # -----------------------------
    # Loop over all items and assets
    # -----------------------------
    for item in root_catalog.get_all_items():
        item_datetime = item.properties.get("datetime", "")
        if not item_datetime.startswith(filter_date):
            continue  # skip items that don't match the filter date

        print(f"Downloading assets for item {item.id} with datetime {item_datetime}")
        for asset_name, asset in item.assets.items():
            download_asset(asset.href)

    print("Filtered assets downloaded.")

processing_date = "2022-08-03T14:00:00"
dt = datetime.strptime(processing_date, "%Y-%m-%dT%H:%M:%S")
filter_date = dt.strftime('%Y-%m-%d')
print(filter_date)

download_stac(
    input_path="s3://dco/activations/ISS-domain_S5-458/svc-s5-02-03-flow/20251010T154102-174/inputData",
    aws_access_key_id="p6etHV5GcgX1SYfX8aSv",
    aws_secret_access_key="P5MNohDSdFX9EYNH3MUjMQP1qbcyPlrQImP8HrsW",
    s3_endpoint="https://dcobucket-aws.iride.earth",
    filter_date=filter_date,  # match item datetime property
    local_download_dir="/Users/valentinopapandrea/Desktop/University/GeoK/DCO/03"
)

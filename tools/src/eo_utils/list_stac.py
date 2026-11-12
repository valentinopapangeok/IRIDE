import warnings
import os
from urllib3.exceptions import InsecureRequestWarning
import boto3
import pystac
from pystac import StacIO

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
# Function to list assets and their attributes
# -----------------------------
def list_stac_assets(
    input_path: str,
    aws_access_key_id: str,
    aws_secret_access_key: str,
    s3_endpoint: str,
    filter_date: str = None
):
    """
    List all assets and their attributes from a STAC catalog on S3.

    Parameters:
        input_path (str): S3 folder containing catalog.json
        aws_access_key_id (str)
        aws_secret_access_key (str)
        s3_endpoint (str)
        filter_date (str, optional): Only list assets containing this string
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

    # Set the S3 client in CustomS3IO and register the class
    CustomS3IO.set_s3_client(s3_client)
    pystac.StacIO.set_default(CustomS3IO)

    # Load catalog
    print(f"Loading STAC catalog: {root_catalog_path}")
    root_catalog = pystac.Catalog.from_file(root_catalog_path)

    # -----------------------------
    # Loop over all items and assets
    # -----------------------------
    for item in root_catalog.get_all_items():
        print(f"\nItem ID: {item.id}")
        print(f"Properties: {item.properties}")

        for asset_name, asset in item.assets.items():
            if filter_date and filter_date not in asset.href:
                continue

            print(f"\n  Asset name: {asset_name}")
            print(f"    Href: {asset.href}")
            print(f"    Media type: {asset.media_type}")
            print(f"    Roles: {asset.roles}")
            print(f"    Title: {asset.title}")
            if asset.extra_fields:
                print(f"    Extra fields: {asset.extra_fields}")


# -----------------------------
# Usage Example
# -----------------------------
list_stac_assets(
    input_path="s3://dco/activations/ISS-domain_S5-842/svc-s5-02-08-flow/20251030T151303-360/inputData",
    aws_access_key_id="p6etHV5GcgX1SYfX8aSv",
    aws_secret_access_key="P5MNohDSdFX9EYNH3MUjMQP1qbcyPlrQImP8HrsW",
    s3_endpoint="https://dcobucket-aws.iride.earth"
)

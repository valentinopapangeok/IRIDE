import logging
import os
import zipfile
from datetime import datetime
import pandas as pd
import requests


def get_access(username: str, password: str) -> str:
    data = {
        "client_id": "cdse-public",
        "username": username,
        "password": password,
        "grant_type": "password",
    }
    try:
        r = requests.post(
            "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
            data=data,
        )
        r.raise_for_status()
    except Exception as e:
        raise Exception(
            f"Access token creation failed. Reponse from the server was: {r.json()}"
        )
    return r.json()["access_token"]


def download_and_extract_sentinel3(
    sentinel_folder,
    txt_folder,
    start_date,
    end_date,
    west_lon,
    south_lat,
    east_lon,
    north_lat,
    sentinel3_user,
    sentinel3_pwd,
):
    token = get_access(sentinel3_user, sentinel3_pwd)
    data_collection = "SENTINEL-3"
    product_type = "LST"
    # Convert the bounding box to the "POLYGON" format
    aoi = f"POLYGON(({west_lon} {south_lat}, {west_lon} {north_lat}, {east_lon} {north_lat}, {east_lon} {south_lat}, {west_lon} {south_lat}))"
    json = requests.get(
        f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq '{data_collection}' and OData.CSC.Intersects(area=geography'SRID=4326;{aoi}') and Attributes/OData.CSC.StringAttribute/any(att:att/Name eq 'productType' and att/OData.CSC.StringAttribute/Value eq '{product_type}') and ContentDate/Start gt {start_date}T08:00:00.000Z and ContentDate/Start lt {end_date}T12:30:00.000Z"
    ).json()
    df = pd.DataFrame.from_dict(json["value"]).head(n=20)

    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {token}"})

    # Initialize a set to store seen product names
    seen_names = set()

    # Iterate over each row in the DataFrame to download all products
    for index, row in df.iterrows():
        product_id = row["Id"]
        product_name = row["Name"]

        # Extract start and end times from the product name
        start_time_sentinel = product_name[16:30]
        end_time_sentinel = product_name[32:46]
        start_time1 = datetime.strptime(start_time_sentinel, "%Y%m%dT%H%M%S")
        end_time1 = datetime.strptime(end_time_sentinel, "%Y%m%dT%H%M%S")

        # Calculate the duration in minutes
        duration_minutes = (end_time1 - start_time1).total_seconds() / 60

        if duration_minutes <= 3:
            if product_name[:46] not in seen_names:
                seen_names.add(product_name[:46])

                # Download the product using its ID
                url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products({product_id})/$value"
                response = session.get(url, allow_redirects=False)

                while response.status_code in (301, 302, 303, 307):
                    url = response.headers["Location"]
                    response = session.get(url, allow_redirects=False)

                file = session.get(url, verify=False, allow_redirects=True)

                # Ensure the directory exists
                os.makedirs(sentinel_folder, exist_ok=True)

                # Specify the full path for the ZIP file using the product name
                output_path = os.path.join(sentinel_folder, f"{product_name}.zip")

                with open(output_path, "wb") as p:
                    p.write(file.content)

                logging.info(f"Downloaded ZIP file saved at: {output_path}")
            else:
                logging.info(f"Skipping duplicate product: {product_name}")
        else:
            logging.info(f"Skipping product with duration > 3 minutes: {product_name}")

    logging.info("Writing Sentinel3 input products on txt file.")
    start_times = []
    end_times = []

    output_txt_path = os.path.join(txt_folder, "sentinel.txt")

    with open(output_txt_path, "w") as txt_file:
        product_details = []

        for index, row in df.iterrows():
            product_id = row["Id"]
            product_name = row["Name"]

            # Check if the product was downloaded
            product_file_path = os.path.join(sentinel_folder, f"{product_name}.zip")
            if os.path.exists(product_file_path):
                start_time_s3 = product_name[16:30]
                end_time_s3 = product_name[32:46]
                start_time = datetime.strptime(start_time_s3, "%Y%m%dT%H%M%S")
                start_times.append(start_time)
                end_times.append(datetime.strptime(end_time_s3, "%Y%m%dT%H%M%S"))

                # Format the start and end times as required
                start_time_formatted = start_time.strftime("%d/%m/%YT%H:%M:%S")

                # Create the row for the text file
                product_details.append(
                    (
                        start_time,
                        f"[IN-S5-02-02] Sentinel-3-SLSTR L2 LST; {start_time_formatted}; 1000m",
                    )
                )

        # Sort product details by start time
        product_details.sort(key=lambda x: x[0])

        # Write the sorted product details to the text file
        for _, product_detail in product_details:
            txt_file.write(product_detail + "\n")

        if start_times and end_times:
            earliest_start_time = min(start_times)
            latest_end_time = max(end_times)
            logging.info(f"Earliest start time: {earliest_start_time}")
            logging.info(f"Latest end time: {latest_end_time}")
            logging.info(f"Text file with product details saved at: {output_txt_path}")
        else:
            logging.info("No products were downloaded, so no text file was created.")
    # Loop through all files in the directory
    for filename in os.listdir(sentinel_folder):
        file_path = os.path.join(sentinel_folder, filename)

        # Check if the file is a zip archive
        if zipfile.is_zipfile(file_path):
            # Extract the contents to the same directory
            with zipfile.ZipFile(file_path, "r") as zip_ref:
                zip_ref.extractall(sentinel_folder)

    logging.info("Extraction Sentinel3 data complete.")
    return True

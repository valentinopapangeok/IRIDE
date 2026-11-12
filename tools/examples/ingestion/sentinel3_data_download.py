import logging
import os
import zipfile
from datetime import datetime
import pandas as pd
import requests
import netCDF4 as nc
from prefect_common import svc_flow, svc_task


@svc_task
def get_access(username: str, password: str) -> str:
    if not username or not password:
        raise ValueError("Username e/o password mancanti")

    url = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"
    data = {
        "client_id": "cdse-public",
        "username": username,
        "password": password,
        "grant_type": "password",
    }
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    r = requests.post(url, data=data, headers=headers)
    print('TEST')
    try:
        print('ENTRO NEL TRY')
        r.raise_for_status()
    except requests.HTTPError:
        # Mostriamo il body per aiutare il debug
        raise Exception(f"Access token creation failed: status {r.status_code}, body: {r.text}")

    return r.json()["access_token"]

@svc_flow(name="ingestion_sentinel3")
async def download_and_extract_sentinel3(
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
    logger
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

                # Ensure the directory exists
                os.makedirs(sentinel_folder, exist_ok=True)

                # Specify the full path for the ZIP file using the product name
                output_path = os.path.join(sentinel_folder, f"{product_name}.zip")

                # Stream download to avoid memory issues with large files
                try:
                    file = session.get(url, verify=False, allow_redirects=True, stream=True, timeout=300)
                    file.raise_for_status()
                    
                    # Write in chunks to handle large files
                    total_size = 0
                    with open(output_path, "wb") as p:
                        for chunk in file.iter_content(chunk_size=8192):
                            if chunk:
                                p.write(chunk)
                                total_size += len(chunk)
                    
                    logger.info(f"Downloaded {total_size:,} bytes to: {output_path}")
                except requests.exceptions.RequestException as e:
                    logger.error(f"❌ Download failed for {product_name}: {str(e)}")
                    if os.path.exists(output_path):
                        os.remove(output_path)
                    continue

                # Validate the downloaded ZIP file
                if not zipfile.is_zipfile(output_path):
                    logger.error(f"❌ Downloaded file is not a valid ZIP: {output_path}")
                    os.remove(output_path)
                    logger.info(f"   Removed invalid file: {output_path}")
                    continue
                    
                # Check ZIP file integrity
                try:
                    with zipfile.ZipFile(output_path, "r") as test_zip:
                        bad_file = test_zip.testzip()
                        if bad_file:
                            logger.error(f"❌ Corrupted file in ZIP: {bad_file}")
                            os.remove(output_path)
                            logger.info(f"   Removed corrupted ZIP: {output_path}")
                            continue
                except zipfile.BadZipFile:
                    logger.error(f"❌ Bad ZIP file: {output_path}")
                    os.remove(output_path)
                    logger.info(f"   Removed bad ZIP: {output_path}")
                    continue

                logger.info(f"✅ Downloaded and validated ZIP file: {output_path}")
            else:
                logger.info(f"Skipping duplicate product: {product_name}")
        else:
            logger.info(f"Skipping product with duration > 3 minutes: {product_name}")

    logger.info("Writing Sentinel3 input products on txt file.")
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
            logger.info(f"Earliest start time: {earliest_start_time}")
            logger.info(f"Latest end time: {latest_end_time}")
            logger.info(f"Text file with product details saved at: {output_txt_path}")
        else:
            logger.info("No products were downloaded, so no text file was created.")
    # Loop through all files in the directory
    extracted_products = []
    for filename in os.listdir(sentinel_folder):
        file_path = os.path.join(sentinel_folder, filename)

        # Check if the file is a zip archive
        if zipfile.is_zipfile(file_path):
            # Extract the contents to the same directory
            with zipfile.ZipFile(file_path, "r") as zip_ref:
                zip_ref.extractall(sentinel_folder)
            
            # Track the extracted product name (remove .zip extension)
            product_name = filename.replace(".zip", "")
            extracted_products.append(product_name)

    logger.info("Extraction Sentinel3 data complete.")
    
    # Validate extracted NetCDF files
    logger.info("Validating extracted NetCDF files...")
    validation_passed = 0
    validation_failed = 0
    
    for product_name in extracted_products:
        sen3_folder = os.path.join(sentinel_folder, product_name)
        if not os.path.isdir(sen3_folder):
            logger.warning(f"⚠️  Extracted folder not found: {product_name}")
            validation_failed += 1
            continue
        
        required_files = ["LST_in.nc", "geodetic_in.nc", "flags_in.nc"]
        all_valid = True
        
        for nc_file in required_files:
            nc_path = os.path.join(sen3_folder, nc_file)
            
            if not os.path.exists(nc_path):
                logger.warning(f"⚠️  {product_name}: Missing {nc_file}")
                all_valid = False
                continue
            
            file_size = os.path.getsize(nc_path)
            if file_size == 0:
                logger.warning(f"⚠️  {product_name}: Empty {nc_file}")
                all_valid = False
                continue
            
            # Try to open the NetCDF file
            try:
                with nc.Dataset(nc_path, "r") as test_nc:
                    # Verify file integrity by accessing dimensions
                    _ = test_nc.dimensions
                logger.debug(f"   ✅ {product_name}: {nc_file} validated ({file_size:,} bytes)")
            except Exception as e:
                logger.error(f"❌ {product_name}: Corrupted {nc_file} - {str(e)}")
                all_valid = False

        if all_valid:
            validation_passed += 1
            logger.info(f"✅ {product_name}: All NetCDF files validated")
        else:
            validation_failed += 1
            logger.warning(f"⚠️  {product_name}: Has validation issues - may fail in preprocessing")
    
    logger.info(f"📊 Validation summary: {validation_passed} passed, {validation_failed} failed out of {len(extracted_products)} products")
    return True

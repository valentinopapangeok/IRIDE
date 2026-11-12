import os
import cdsapi
import xarray as xr
import logging

from prefect_common import svc_flow

@svc_flow(name="ingestion_era5land")
def era5land_download(start_date, era5land_folder):
    # Bounding box coordinates for the area of interest
    bbox = [50, 0, 30, 20]  # [North, West, South, East]

    # Extract year, month, and day from start_date
    year = start_date[:4]
    month = start_date[5:7]
    day = start_date[8:10]

    # Initialize the CDS API client
    c = cdsapi.Client(url="https://cds.climate.copernicus.eu/api", key="fc72d9d9-ac0e-42f7-b5c4-a873839b9fd9")

    try:
        c.retrieve(
            "reanalysis-era5-land",
            {
                "product_type": "reanalysis",
                "format": "netcdf",
                "variable": "skin_temperature",
                "area": bbox,  # Use the bounding box coordinates directly here
                "day": [day],
                "month": month,
                "year": year,
                "time": "10:00",
                "data_format": "netcdf",
            },
            "download.nc",
        )
        logging.info("ERA5 data downloaded")
        dv = xr.open_dataset("download.nc")
        data = dv.skt.to_dataframe().reset_index()
        # Save to CSV inside the era5_folder folder
        era5land_csv_path = os.path.join(era5land_folder, "era5.csv")
        data.to_csv(era5land_csv_path, index=False)
        logging.info(f"CSV saved successfully at: {era5land_csv_path}")
        return True

    except Exception as e:
        print(f"Error: {e}")
        return False

@svc_flow(name="ingestion_era5")
def era5_download(start_date, era5_folder):

    # Bounding box coordinates for the area of interest
    bbox = [50, 0, 30, 20]  # [North, West, South, East]

    # Extract year, month, and day from start_date
    year = start_date[:4]
    month = start_date[5:7]
    day = start_date[8:10]

    # Initialize the CDS API client
    c = cdsapi.Client(url="https://cds.climate.copernicus.eu/api", key="fc72d9d9-ac0e-42f7-b5c4-a873839b9fd9")

    try:
        c.retrieve(
            "reanalysis-era5-single-levels",
            {
                "product_type": "reanalysis",
                "format": "netcdf",
                "variable": "skin_temperature",
                "area": bbox,  # Use the bounding box coordinates directly here
                "day": [day],
                "month": month,
                "year": year,
                "time": "10:00",
                "data_format": "netcdf",
            },
            "download.nc",
        )
        logging.info("ERA5 data downloaded")
        dv = xr.open_dataset("download.nc")
        data = dv.skt.to_dataframe().reset_index()
        # Save to CSV inside the era5_folder folder
        era5_csv_path = os.path.join(era5_folder, "era5.csv")
        data.to_csv(era5_csv_path, index=False)
        logging.info(f"CSV saved successfully at: {era5_csv_path}")
        return True

    except Exception as e:
        print(f"Error: {e}")
        return False

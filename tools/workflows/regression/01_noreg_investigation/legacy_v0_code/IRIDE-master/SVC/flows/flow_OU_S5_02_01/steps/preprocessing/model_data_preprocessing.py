import logging
import os
import numpy as np
import pandas as pd
import rasterio
from osgeo import gdal
from rasterio.transform import Affine


def era5landcsv_to_tiff(csv_path, tiff_path):
    try:
        # Controlla se il file CSV esiste
        if not os.path.exists(csv_path):
            logging.warning(f"CSV file not found: {csv_path}. Skipping conversion.")
            return  # Esce dalla funzione ma non interrompe l'esecuzione del programma

        # Legge il file CSV
        df = pd.read_csv(csv_path)

        # Converti la temperatura da Kelvin a Celsius
        df["skt"] = df["skt"] - 273.15

        x_resolution = 0.100006103515625
        y_resolution = 0.100006103515625

        # Determina il numero di pixel in base alla risoluzione
        x_size = (
            int(round((df.longitude.max() - df.longitude.min()) / x_resolution)) + 1
        )
        y_size = int(round((df.latitude.max() - df.latitude.min()) / y_resolution)) + 1

        # Inizializza un array vuoto con NaN
        array = np.full((y_size, x_size), np.nan, dtype="float32")

        # Popola l'array con i dati di temperatura
        for _, row in df.iterrows():
            if not np.isnan(row["skt"]):
                col = int((row.longitude - df.longitude.min()) / x_resolution)
                row_idx = int((df.latitude.max() - row.latitude) / y_resolution)
                array[row_idx, col] = row["skt"]

        # Definisce la trasformazione affine
        transform = Affine(
            x_resolution, 0, df.longitude.min(), 0, -y_resolution, df.latitude.max()
        )

        # Scrive l'array su un file GeoTIFF
        with rasterio.open(
            tiff_path,
            "w",
            driver="GTiff",
            height=y_size,
            width=x_size,
            count=1,
            dtype="float32",
            crs="EPSG:4326",
            transform=transform,
        ) as dst:
            dst.write(array, 1)

        logging.info(f"GeoTIFF file saved at: {tiff_path}")
        return True

    except Exception as e:
        logging.error(f"Error in converting CSV to GeoTIFF: {e}")
        return False


def era5csv_to_geotiff(era5_csv_path, era5tiff_path):
    try:
        if not os.path.exists(era5_csv_path):
            logging.warning(
                f"CSV file not found: {era5_csv_path}. Skipping conversion."
            )
            return  # Esce dalla funzione ma non interrompe l'esecuzione del programma
        # Read the CSV file
        df = pd.read_csv(era5_csv_path)

        # Convert temperature from Kelvin to Celsius
        df["skt"] = df["skt"] - 273.15  # Kelvin to Celsius conversion

        # Determine the number of pixels in the x and y directions based on the resolution
        x_resolution = 0.25
        y_resolution = 0.25
        x_size = (
            int(round((df.longitude.max() - df.longitude.min()) / x_resolution)) + 1
        )
        y_size = int(round((df.latitude.max() - df.latitude.min()) / y_resolution)) + 1

        # Initialize an empty array with NaN values
        array = np.full((y_size, x_size), np.nan, dtype="float32")

        # Populate the array with temperature data
        for _, row in df.iterrows():
            if not np.isnan(row["skt"]):
                col = int((row.longitude - df.longitude.min()) / x_resolution)
                row_idx = int((df.latitude.max() - row.latitude) / y_resolution)
                array[row_idx, col] = row["skt"]

        # Specify the affine transformation parameters explicitly
        transform = Affine(
            x_resolution, 0, df.longitude.min(), 0, -y_resolution, df.latitude.max()
        )

        # Write the array to a GeoTIFF file
        with rasterio.open(
            era5tiff_path,
            "w",
            driver="GTiff",
            height=y_size,
            width=x_size,
            count=1,
            dtype="float32",
            crs="EPSG:4326",
            transform=transform,
        ) as dst:
            dst.write(array, 1)
        logging.info(f"GeoTIFF file saved at: {era5tiff_path}")

        # Optionally, delete the CSV file
        try:
            # os.remove(era5_csv_path)
            logging.info(f"CSV file deleted: {era5_csv_path}")
        except FileNotFoundError:
            logging.warning(f"CSV file not found: {era5_csv_path}")
            return True

    except Exception as e:
        logging.error(f"Error in converting CSV to GeoTIFF: {e}")
        return False


def resample_era5land_to_s3(product_folder):
    """
    Resample ERA5-LAND data to match Sentinel-3 resolution and save metadata to a text file.

    :param product_folder: Path to the folder containing era5land.tif
    :param txt_folder: Path to the folder where era5_land.txt will be saved
    :param day: Day of acquisition
    :param month: Month of acquisition
    :param year: Year of acquisition
    :param desired_pixel_size: Target pixel size in meters (default is 1000m)
    """
    era5landtiff_path = os.path.join(product_folder, "era5land.tif")

    # Try opening the ERA5-LAND TIFF, and if it fails, print a warning and continue
    try:
        ds = gdal.Open(era5landtiff_path)
        if ds is None:
            raise FileNotFoundError(f"Could not open {era5landtiff_path}")

        array = ds.GetRasterBand(1).ReadAsArray()
        nan_mask = np.isnan(array)
        ds.GetRasterBand(1).SetNoDataValue(-999)
        array[nan_mask] = np.nan

        original_width = ds.RasterXSize
        original_height = ds.RasterYSize

        # Calculate new width and height based on resolution scaling
        new_width = int(original_width / 0.1)
        new_height = int(original_height / 0.1)

        resampled_tiff_path = os.path.join(product_folder, "era5land_resampled.tif")
        dsRes = gdal.Warp(
            resampled_tiff_path,
            ds,
            width=new_width,
            height=new_height,
            resampleAlg="bilinear",
            callback=gdal.TermProgress_nocb,
            srcNodata=-999,
        )

        if dsRes is None:
            raise RuntimeError("Resampling failed")

        # Get resampled array
        array = dsRes.GetRasterBand(1).ReadAsArray()

        # Save metadata to text file
        print(f"Resampled ERA5-LAND saved at: {resampled_tiff_path}")

    except FileNotFoundError as e:
        print(f"Warning: {e}. Proceeding without resampling ERA5-LAND.")
        return True

    except Exception as e:
        print(f"An error occurred: {e}.")
        return False


def resample_era5_to_s3(
    era5tiff_path, product_folder, txt_folder, day, month, year, desired_pixel_size=1000
):
    try:
        # Open the original raster dataset
        ds = gdal.Open(era5tiff_path)
        array = ds.GetRasterBand(1).ReadAsArray()

        # Create a mask for NaN values
        nan_mask = np.isnan(array)

        # Set a temporary NoData value for the source dataset
        ds.GetRasterBand(1).SetNoDataValue(-999)  # Use any value you prefer

        # Set NaN values to the temporary NoData value
        array[nan_mask] = np.nan

        # Get original dimensions
        original_width = ds.RasterXSize
        original_height = ds.RasterYSize

        # Calculate the resolution in meters for the original dataset
        original_resolution_degrees = 0.25  # degrees
        original_resolution_meters = (
            original_resolution_degrees * 111000
        )  # meters/degree (approximate)

        # Calculate the factor for resizing
        factor = original_resolution_meters / desired_pixel_size

        # Calculate new width and height
        new_width = int(original_width * factor)
        new_height = int(original_height * factor)

        # Output path for the resampled TIFF
        tiff_path = os.path.join(product_folder, "era5.tif")

        # Use gdal.Warp with the mask and resampleAlg="bilinear"
        dsRes = gdal.Warp(
            tiff_path,
            ds,
            width=new_width,
            height=new_height,
            resampleAlg="bilinear",  # resampling mode
            callback=gdal.TermProgress_nocb,  # Suppress progress callback
            srcNodata=-999,
        )  # Set the temporary NoData value

        # Get the resampled array
        resampled_array = dsRes.GetRasterBand(1).ReadAsArray()
        era5land_acquisition_day = f"{day}/{month}/{year}"
        era5land_output_file_path = os.path.join(txt_folder, "era5_land.txt")
        with open(era5land_output_file_path, "w") as f:
            f.write(
                f"[IN-S5-02-20] C3S ERA5- ERA5 & ERA5-LAND/SKIN-TEMPERATURE; {era5land_acquisition_day}T10:00:00;11000m"
            )

        logging.info(f"Resampled GeoTIFF saved at: {tiff_path}")
        return True  # Optionally return the resampled array

    except Exception as e:
        logging.error(f"Error during resampling: {e}")
        return False

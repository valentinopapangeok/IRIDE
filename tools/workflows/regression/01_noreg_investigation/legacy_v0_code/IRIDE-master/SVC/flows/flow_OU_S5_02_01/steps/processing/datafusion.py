import logging
import os
from datetime import datetime
import numpy as np
import rasterio
import subprocess


def data_fusion(input_folder, output_folder):
    """
    Performs data fusion by filling missing values in Sentinel-3 data using MODIS, GCOM-C, ERA5-LAND, and ERA5.

    Parameters:
        input_folder (str): Path to the folder containing the input TIFF files.
        output_folder (str): Path to the folder where the fused output TIFF will be saved.
    """
    # Define paths to input TIFF files
    modis_tiff_path = os.path.join(input_folder, "modis.tif")
    gcomc_tiff_path = os.path.join(input_folder, "gcom.tif")
    sentinel3_tiff_path = os.path.join(input_folder, "sentinel.tif")
    era5land_tiff_path = os.path.join(input_folder, "era5land.tif")
    era5_tiff_path = os.path.join(input_folder, "era5.tif")
    output_tiff_path = os.path.join(output_folder, "datafusion.tif")

    # Ensure output folder exists
    os.makedirs(output_folder, exist_ok=True)

    # Function to load data from a TIFF file if it exists
    def load_data(tiff_path):
        if os.path.exists(tiff_path):
            with rasterio.open(tiff_path) as src:
                return src.read(1, masked=True), src.profile
        return None, None

    # Load Sentinel-3 data (must exist)
    sentinel3_data, profile = load_data(sentinel3_tiff_path)
    if sentinel3_data is None:
        logging.error("Sentinel-3 TIFF file not found. Aborting data fusion.")
        return

    # Load other datasets
    modis_data, _ = load_data(modis_tiff_path)
    gcomc_data, _ = load_data(gcomc_tiff_path)
    era5land_data, _ = load_data(era5land_tiff_path)
    era5_data, _ = load_data(era5_tiff_path)

    # Fill NaN values in Sentinel-3 using available datasets
    if modis_data is not None:
        sentinel3_data = np.where(np.isnan(sentinel3_data), modis_data, sentinel3_data)
    if gcomc_data is not None:
        sentinel3_data = np.where(
            np.isnan(sentinel3_data) & ~np.isnan(gcomc_data), gcomc_data, sentinel3_data
        )
    if era5land_data is not None:
        sentinel3_data = np.where(
            np.isnan(sentinel3_data) & ~np.isnan(era5land_data),
            era5land_data,
            sentinel3_data,
        )
    if era5_data is not None:
        sentinel3_data = np.where(
            np.isnan(sentinel3_data) & ~np.isnan(era5_data), era5_data, sentinel3_data
        )

    # Write the fused dataset to output
    with rasterio.open(output_tiff_path, "w", **profile) as dst:
        dst.write(sentinel3_data, 1)

    logging.info(f"Data Fusion successfully computed and saved to {output_tiff_path}")
    return True


def replace_nodata_value(input_folder, output_folder, nodata_value=-999):
    # Iterate over all TIFF files in the input folder
    for file in os.listdir(input_folder):
        if file.endswith(".tif") or file.endswith(".tiff"):
            input_tiff_path = os.path.join(input_folder, file)
            output_tiff_path = os.path.join(
                output_folder, file
            )  # Define the output path

            # Define the gdal_translate command
            gdal_command = [
                "gdal_translate",  # Command name
                "-a_nodata",
                str(nodata_value),  # Specify the nodata value
                input_tiff_path,  # Input GeoTIFF file
                output_tiff_path,  # Output GeoTIFF file
            ]

            # Execute the gdal_translate command
            subprocess.run(gdal_command)
    return True


def replace_nan_with_value(input_path, output_path, replace_value=-999):
    """
    Reads a raster file, replaces NaN values with a specified value (default: -999),
    explicitly marking them as no-data, and saves the modified raster to a new file.

    Parameters:
        input_path (str): Path to the input raster file.
        output_path (str): Path to save the output raster file.
        replace_value (float): Value to replace NaN pixels with. It will be set as the no-data value.
    """
    with rasterio.open(input_path) as src:
        data = src.read(1).astype(np.float32)  # Ensure float to handle NaNs
        profile = src.profile

    # Replace NaN values with the specified no-data value
    data[np.isnan(data)] = replace_value

    # Round valid values to two decimal places
    data = np.round(data, 2)

    # Update metadata to indicate the no-data value
    profile.update(nodata=replace_value, dtype=rasterio.float32)

    # Save the modified raster
    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(data.astype(rasterio.float32), 1)

    return True

def replace_values_with_constant_in_folder(
    input_folder, start_date, final_filename, constant_value=-999, output_folder=None
):
    # Assicurati che la cartella di input esista
    if not os.path.exists(input_folder):
        raise ValueError(f"La cartella di input {input_folder} non esiste.")

    # Se la cartella di output non è specificata, usa quella di input
    if output_folder is None:
        output_folder = input_folder
    else:
        os.makedirs(output_folder, exist_ok=True)  # Crea la cartella se non esiste

    # Lista di tutti i file TIFF nella cartella di input
    tiff_files = [f for f in os.listdir(input_folder) if f.endswith(".tif")]

    # Estrarre il mese dalla data di inizio
    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    month = start_date.month

    # Definizione delle soglie in base al mese
    thresholds = {
        1: (-40, 40),
        2: (-40, 40),
        3: (-30, 50),
        4: (-30, 50),
        5: (-20, 60),
        6: (-20, 60),
        7: (-10, 70),
        8: (-10, 70),
        9: (-20, 60),
        10: (-20, 60),
        11: (-30, 50),
        12: (-30, 50),
    }
    threshold_low, threshold_high = thresholds.get(month, (-30, 50))

    # Loop attraverso tutti i file TIFF nella cartella di input
    for tiff_file in tiff_files:
        input_tiff_path = os.path.join(input_folder, tiff_file)
        output_tiff_path = os.path.join(output_folder, final_filename + ".tif")

        with rasterio.open(input_tiff_path) as src:
            image = src.read(1).astype(float)  # Converti in float per gestire NaN
            image[np.isnan(image)] = (
                constant_value  # Sostituisci NaN con valore costante
            )
            image[(image < threshold_low) | (image > threshold_high)] = (
                constant_value  # Sostituisci valori fuori soglia
            )

            # Salva il nuovo TIFF
            profile = src.profile
            with rasterio.open(output_tiff_path, "w", **profile) as dst:
                dst.write(image, 1)

        print(f"File modificato salvato in: {output_tiff_path}")
    return True


def process_tiff_files(input_folder, output_folder, final_filename1, final_filename):
    """
    Replace NaN and specific values (e.g., 65535) in all TIFF files within the input folder,
    and save the processed files with the specified final filename in the output folder.

    Parameters:
        input_folder (str): Path to the folder containing TIFF files.
        output_folder (str): Path to the folder where processed TIFF files will be saved.
        final_filename (str): Final filename for the processed TIFF files.

    Returns:
        None
    """
    # Ensure the output folder exists
    os.makedirs(output_folder, exist_ok=True)

    # Get a list of TIFF files in the input folder
    tif_files = [file for file in os.listdir(input_folder) if file.endswith(".tif")]

    # Loop through all TIFF files in the input folder
    for filename in tif_files:
        input_tiff_path = os.path.join(input_folder, filename)

        # Construct the new filename
        final_filename1 = "datafusion1.tif"
        output_tiff_path1 = os.path.join(output_folder, final_filename1)

        # Open the input TIFF file
        with rasterio.open(input_tiff_path) as src:
            # Read the band as a numpy array
            band = src.read(1)

            # Replace NaN values with -999
            band = np.where(np.isnan(band), -999, band)

            # Replace specific value 65535 with -999
            band = np.where(band == 65535, -999, band)

            # Get metadata for the output TIFF
            profile = src.profile

        # Write the updated band to the output TIFF with the fixed filename
        with rasterio.open(output_tiff_path1, "w", **profile) as dst:
            dst.write(band, 1)
    print("All TIFF files in the folder have been processed.")
    return True

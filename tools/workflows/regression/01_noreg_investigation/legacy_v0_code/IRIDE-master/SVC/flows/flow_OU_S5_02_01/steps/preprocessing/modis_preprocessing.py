import logging
import os
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import rasterio
from osgeo import gdal


def julian_to_gregorian(julian_date, year):
    jan1 = datetime(year, 1, 1)
    gregorian_date = jan1 + timedelta(days=julian_date - 1)
    return gregorian_date.strftime("%Y-%m-%d")  # Modified to 'yyyy-mm-dd' format


def convert_acquisition_time(acquisition_time):
    hours = int(acquisition_time)
    minutes = int((acquisition_time - hours) * 60)
    return f"{hours:02d}:{minutes:02d}"


def modis_txt_creation(input_folder, txt_folder):
    """
    Process MODIS HDF files, extract time information, and save as CSV and TXT.
    """
    downloaded_files = [f for f in os.listdir(input_folder) if f.endswith(".hdf")]

    if downloaded_files:
        data_list = []

        for hdf_file in downloaded_files:
            logging.info(f"Processing MODIS HDF file: {hdf_file}")
            try:
                hdf_path = os.path.join(input_folder, hdf_file)
                year = int(hdf_file[9:13])
                julian_date = int(hdf_file[13:16])
                acquisition_day = julian_to_gregorian(julian_date, year)

                hdf_dataset = gdal.Open(hdf_path, gdal.GA_ReadOnly)
                band_path = hdf_dataset.GetSubDatasets()[2][
                    0
                ]  # Band 3 is typically at index 2
                ds = gdal.Open(band_path)
                band_array = ds.ReadAsArray() * 0.1

                filtered_values = band_array[band_array <= 24]

                if filtered_values.size > 0:
                    min_value = np.min(filtered_values)
                    max_value = np.max(filtered_values)
                    midpoint = (min_value + max_value) / 2

                    min_value = convert_acquisition_time(min_value)
                    max_value = convert_acquisition_time(max_value)
                    midpoint = convert_acquisition_time(midpoint)

                    data_list.append(
                        {
                            "Name": hdf_file,
                            "Acquisition Day": acquisition_day,
                            "Starting Time": min_value,
                            "Ending Time": max_value,
                            "Medium Point": midpoint,
                        }
                    )
            except Exception as e:
                logging.warning(f"Error processing MODIS HDF file {hdf_file}: {e}")

        if data_list:
            df = pd.DataFrame(data_list)
            modis_csv_path = os.path.join(input_folder, "LST_MODIS.csv")
            df.to_csv(modis_csv_path, index=False)
            logging.info(f"MODIS CSV saved successfully: {modis_csv_path}")
        else:
            logging.warning("No MODIS data available for processing.")

    csv_files = [f for f in os.listdir(input_folder) if f.endswith(".csv")]

    if len(csv_files) == 0:
        logging.warning("No MODIS CSV file found in the folder.")
        return
    elif len(csv_files) > 1:
        logging.error("More than one MODIS CSV file found in the folder.")
        return

    csv_file_path = os.path.join(input_folder, csv_files[0])
    df = pd.read_csv(csv_file_path)
    acquisition_day = (
        pd.to_datetime(df["Acquisition Day"]).dt.strftime("%d/%m/%Y").values[0]
    )
    starting_time = min(df["Starting Time"])
    ending_time = max(df["Ending Time"])

    output_file_path = os.path.join(txt_folder, "modis.txt")
    with open(output_file_path, "w") as f:
        f.write(f"[IN-S5-02-06] MODIS; {acquisition_day}T{starting_time}:00;1000m")
    logging.info(f"MODIS text file saved successfully: {output_file_path}")
    return True


def convert_modis_hdf_to_tiff(input_folder, output_folder):
    """
    Converts MODIS HDF files to TIFF format.

    Parameters:
        input_folder (str): The folder containing the MODIS HDF files.
        output_folder (str): The folder to save the output TIFF files.
    """
    logging.info(f"Converting MODIS hdf files to tiff.")

    # Create the output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # List all HDF files in the input folder
    hdf_files = [f for f in os.listdir(input_folder) if f.endswith(".hdf")]

    # Loop through each HDF file and convert it to TIFF
    for hdf_file in hdf_files:
        # Construct the full paths to the HDF and TIFF files
        hdf_path = os.path.join(input_folder, hdf_file)

        # Open the HDF dataset
        dataset = gdal.Open(hdf_path, gdal.GA_ReadOnly)

        # List all subdatasets (bands or other data) available in the HDF file
        subdatasets = dataset.GetSubDatasets()

        if len(subdatasets) < 2:
            logging.info(
                f"MODIS HDF file: {hdf_file} does not contain at least two subdatasets."
            )
            continue

        # Loop through the first and second subdatasets
        for i in range(2):
            subdataset_path = subdatasets[i][0]
            subdataset = gdal.Open(subdataset_path, gdal.GA_ReadOnly)

            # Construct the output TIFF file path
            tiff_file = os.path.splitext(hdf_file)[0] + f"_band{i + 1}.tif"
            tiff_path = os.path.join(output_folder, tiff_file)

            # gdalwarp to convert to TIFF
            kwargs = {"format": "GTiff", "dstSRS": "EPSG:4326"}
            ds = gdal.Warp(
                destNameOrDestDS=tiff_path, srcDSOrSrcDSTab=subdataset, **kwargs
            )
            del ds

            logging.info(
                f"MODIS Converted {hdf_file} subdataset {i + 1} to TIFF: {tiff_file}"
            )

    logging.info("Conversion of MODIS HDF files to TIFF completed.")
    return True


def process_modis_QA_bands(input_folder, output_folder):
    """
    Process pairs of TIFF files (band1 and band2) in the input folder, applying a transformation
    and saving the resulting new TIFF files to the output folder.

    Args:
    input_folder (str): Path to the folder containing input TIFF files.
    output_folder (str): Path to the folder where output TIFF files will be saved.
    """
    # Create the output folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # List all TIFF files in the input folder
    tiff_files = [f for f in os.listdir(input_folder) if f.endswith(".tif")]

    # Create a dictionary to store file pairs
    file_pairs = {}

    # Populate the dictionary with file pairs
    for tiff_file in tiff_files:
        if "_band1" in tiff_file:
            base_name = tiff_file.replace("_band1.tif", "")
            file_pairs[base_name] = file_pairs.get(base_name, {})
            file_pairs[base_name]["band1"] = tiff_file
        elif "_band2" in tiff_file:
            base_name = tiff_file.replace("_band2.tif", "")
            file_pairs[base_name] = file_pairs.get(base_name, {})
            file_pairs[base_name]["band2"] = tiff_file

    # Loop through each pair of TIFF files and create a new TIFF file based on the criteria
    for base_name, files in file_pairs.items():
        if "band1" not in files or "band2" not in files:
            logging.info(f"File pair incomplete for base name: {base_name}. Skipping.")
            continue

        tiff_file_band1 = files["band1"]
        tiff_file_band2 = files["band2"]

        # Construct the full paths to the TIFF files
        tiff_path_band1 = os.path.join(input_folder, tiff_file_band1)
        tiff_path_band2 = os.path.join(input_folder, tiff_file_band2)

        # Open the TIFF files
        dataset_band1 = gdal.Open(tiff_path_band1, gdal.GA_ReadOnly)
        dataset_band2 = gdal.Open(tiff_path_band2, gdal.GA_ReadOnly)

        # Read the bands
        band1 = dataset_band1.GetRasterBand(1).ReadAsArray()
        band2 = dataset_band2.GetRasterBand(1).ReadAsArray()

        # Create a new array for the output based on the criteria
        new_band = np.where(band2 == 0, band1, 0)

        # Create a new TIFF file
        driver = gdal.GetDriverByName("GTiff")
        out_tiff_path = os.path.join(output_folder, base_name + "_new.tif")
        out_dataset = driver.Create(
            out_tiff_path,
            dataset_band1.RasterXSize,
            dataset_band1.RasterYSize,
            1,
            gdal.GDT_Float32,
        )

        # Set the same geotransform and projection
        out_dataset.SetGeoTransform(dataset_band1.GetGeoTransform())
        out_dataset.SetProjection(dataset_band1.GetProjection())

        # Write the new band to the output file
        out_dataset.GetRasterBand(1).WriteArray(new_band)
        out_dataset.FlushCache()
        del out_dataset

    logging.info("Creation of new TIFF files based on the criteria completed.")
    return True


def convert_modis_dn_to_lst(input_folder, output_folder):
    """
    Converte i valori DN di MODIS in Land Surface Temperature (LST).

    Args:
        input_folder (str): Cartella di input contenente i file TIFF MODIS.
        output_folder (str): Cartella di output per salvare i file LST TIFF.
    """
    os.makedirs(output_folder, exist_ok=True)
    tif_files = [file for file in os.listdir(input_folder) if file.endswith(".tif")]

    for tif_file in tif_files:
        input_tiff = os.path.join(input_folder, tif_file)
        output_tiff = os.path.join(output_folder, tif_file)

        with rasterio.open(input_tiff) as src:
            band = src.read(1, masked=True)
            lst = band * 0.02 - 273.15
            lst[lst == -273.15] = np.nan

            profile = src.profile
            profile.update(dtype=rasterio.float32)

            with rasterio.open(output_tiff, "w", **profile) as dst:
                dst.write(lst, 1)

    logging.info("Conversione da MODIS DN a LST completata per tutti i file TIFF.")
    return True


def extract_acquisition_day(hdf_file):
    try:
        year = hdf_file[9:13]
        julian_date = hdf_file[13:16]
        gregorian_date = julian_to_gregorian(int(julian_date), int(year))
        return gregorian_date.strftime("%Y-%m-%d")
    except (IndexError, ValueError):
        return None

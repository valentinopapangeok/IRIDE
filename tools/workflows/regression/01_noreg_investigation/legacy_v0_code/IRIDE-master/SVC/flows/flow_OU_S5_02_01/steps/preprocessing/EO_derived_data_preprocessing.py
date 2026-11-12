import logging
import os
import shutil
from glob import glob

import geopandas as gpd
import numpy as np
import rasterio
from rasterio.mask import mask
from rasterio.merge import merge
from rasterio.warp import Resampling, reproject
from shapely.geometry import shape


def sentinel3_mosaic(input_folder, output_folder, output_filename):
    """
    Create a mosaic from TIFF files in the input folder and save it to the output folder with the specified filename.

    Parameters:
        input_folder (str): Path to the folder containing TIFF files.
        output_folder (str): Path to the folder where the final mosaic TIFF will be saved.
        output_filename (str): Name of the final mosaic TIFF file.
    """
    # Get a list of all TIFF files in the input folder
    input_files = [
        os.path.join(input_folder, file)
        for file in os.listdir(input_folder)
        if file.endswith(".tif")
    ]

    # Check if there are any TIFF files in the input folder
    if not input_files:
        print("No TIFF files found in the input folder.")
        return

    # List to store opened rasterio datasets
    src_files_to_mosaic = []

    try:
        # Open all TIFF files in the input folder
        for input_tiff in input_files:
            src = rasterio.open(input_tiff)
            src_files_to_mosaic.append(src)

        # Merge the datasets
        merged_data, merged_transform = merge(src_files_to_mosaic)

        # Use the profile of the first input TIFF as a template for the output profile
        output_profile = src_files_to_mosaic[0].profile

        # Update the output profile with the merged transform and dimensions
        output_profile.update(
            {
                "transform": merged_transform,
                "height": merged_data.shape[1],
                "width": merged_data.shape[2],
            }
        )

        # Specify the output path for the final mosaic TIFF
        output_tiff = os.path.join(output_folder, output_filename)

        # Write the final mosaic TIFF
        with rasterio.open(output_tiff, "w", **output_profile) as dst:
            dst.write(merged_data)

        print(f"Mosaic created and saved at: {output_tiff}")

    except Exception as e:
        print(f"An error occurred during mosaic creation: {e}")

    finally:
        # Make sure to close all opened files
        for src in src_files_to_mosaic:
            src.close()

    return True


def modis_mosaic(input_folder, output_folder, output_filename):
    """
    Create a mosaic from TIFF files in the input folder and save it to the output folder with the specified filename.
    The mosaic is only created if there are exactly 4 TIFF files in the input folder.

    Parameters:
        input_folder (str): Path to the folder containing TIFF files.
        output_folder (str): Path to the folder where the final mosaic TIFF will be saved.
        output_filename (str): Name of the final mosaic TIFF file.
    """
    # Get a list of all TIFF files in the input folder
    input_files = [
        os.path.join(input_folder, file)
        for file in os.listdir(input_folder)
        if file.endswith(".tif")
    ]

    # Check if there are exactly 4 TIFF files in the input folder
    if len(input_files) != 4:
        print("Number of TIFF files is not equal to 4. Mosaic will not be created.")
        return

    # List to store opened rasterio datasets
    src_files_to_mosaic = []

    try:
        # Open all TIFF files in the input folder
        for input_tiff in input_files:
            src = rasterio.open(input_tiff)
            src_files_to_mosaic.append(src)

        # Merge the datasets
        merged_data, merged_transform = merge(src_files_to_mosaic)

        # Use the profile of the first input TIFF as a template for the output profile
        output_profile = src_files_to_mosaic[0].profile

        # Update the output profile with the merged transform and dimensions
        output_profile.update(
            {
                "transform": merged_transform,
                "height": merged_data.shape[1],
                "width": merged_data.shape[2],
            }
        )

        # Specify the output path for the final mosaic TIFF
        output_tiff = os.path.join(output_folder, output_filename)

        # Write the final mosaic TIFF
        with rasterio.open(output_tiff, "w", **output_profile) as dst:
            dst.write(merged_data)

        print(f"Mosaic created and saved at: {output_tiff}")

    except Exception as e:
        print(f"An error occurred during mosaic creation: {e}")

    finally:
        # Make sure to close all opened files
        for src in src_files_to_mosaic:
            src.close()
    return True


def clip_tifs_with_shapefile(shape_file_path, input_folder, output_folder):
    """
    Clips all TIFF files in the specified input folder using a shapefile for clipping, and saves the result in the output folder.

    Parameters:
        shape_file_path (str): Path to the shapefile for clipping.
        input_folder (str): Folder containing the original TIFF files to clip.
        output_folder (str): Folder where the clipped TIFF files will be saved.
    """

    logging.info(f"Loading shapefile ({shape_file_path}) for clipping.")

    try:
        gdf = gpd.read_file(shape_file_path)
    except Exception as e:
        logging.error(f"Error loading shapefile: {e}")
        return

    # Check if the shapefile is empty
    if gdf.empty:
        logging.error("Shapefile is empty.")
        return

    # Check if the geometry column is empty
    if gdf.geometry.is_empty.any():
        logging.error("Geometry column is empty.")
        return

    clip_geometry = gdf.geometry.iloc[0]

    # Get the extent (bounding box) of the shapefile geometry
    shapefile_extent = clip_geometry.bounds

    # Use glob to get a list of all TIFF files in the input folder
    tiff_files = glob(os.path.join(input_folder, "*.tif"))

    # Create the output folder for the clipped TIFFs if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)

    # Loop through each TIFF file and clip based on the shapefile geometry
    for tiff_file in tiff_files:
        try:
            # Open the TIFF file
            with rasterio.open(tiff_file) as src:
                # Clip the TIFF using the shapefile geometry
                clipped_data, clipped_transform = mask(
                    src, [shape(clip_geometry)], crop=True
                )

                # Explicitly set the data type to float32
                clipped_data = clipped_data.astype(np.float32)

                # Use masked array to set values outside the geometry to NaN
                clipped_data = np.ma.masked_where(
                    clipped_data == 0, clipped_data, copy=False
                )
                clipped_data[clipped_data.mask] = np.nan

                # Update the metadata for the clipped TIFF
                clipped_meta = src.meta
                clipped_meta.update(
                    {
                        "dtype": "float32",  # Update data type to float32
                        "height": clipped_data.shape[1],
                        "width": clipped_data.shape[2],
                        "transform": clipped_transform,
                    }
                )

                base_filename = os.path.splitext(os.path.basename(tiff_file))[0]
                # Combine it with the name for the subset
                output_tiff = os.path.join(output_folder, f"{base_filename}.tif")

                # Write the clipped TIFF
                with rasterio.open(output_tiff, "w", **clipped_meta) as dst:
                    dst.write(clipped_data)

            logging.info(f"Clipped TIFF saved: {output_tiff}")
        except Exception as e:
            logging.error(f"Error processing {tiff_file}: {e}")

    logging.info("Clipping completed. Clipped TIFFs saved to the output folder.")
    return True


def reproject_tiffs(input_folder, output_folder, sentinel_tiff_path):
    """
    Reprojects all TIFF files in the specified folder to match the projection of a reference TIFF file
    (sentinel_tiff_path), and saves the reprojected TIFFs in the output folder.

    Parameters:
        input_folder (str): Folder containing the cropped TIFF files to reproject.
        output_folder (str): Folder where the reprojected TIFF files will be saved.
        sentinel_tiff_path (str): Path to the reference TIFF file (sentinel) used for reprojection.
    """

    logging.info(f"Reprojecting TIFFs based on the projection of {sentinel_tiff_path}.")

    # Create the output folder for the reprojected TIFFs
    os.makedirs(output_folder, exist_ok=True)

    # Read the projection information from "sentinel.tif"
    with rasterio.open(sentinel_tiff_path) as sentinel_src:
        sentinel_crs = sentinel_src.crs
        sentinel_transform = sentinel_src.transform
        sentinel_shape = (sentinel_src.height, sentinel_src.width)

    # List all cropped TIFF files in the specified folder
    tiff_files = glob(os.path.join(input_folder, "*.tif"))

    # Loop through each cropped TIFF file and reproject based on "sentinel.tif" projection
    for tiff_file in tiff_files:
        try:
            # Open the cropped TIFF file
            with rasterio.open(tiff_file) as src:
                # Reproject the cropped data to match the "sentinel.tif" projection
                reprojected_data = np.empty(sentinel_shape, dtype=np.float32)
                reproject(
                    source=rasterio.band(src, 1),
                    destination=reprojected_data,
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=sentinel_transform,
                    dst_crs=sentinel_crs,
                    resampling=Resampling.nearest,
                )

                # Update the metadata for the reprojected TIFF
                reprojected_meta = src.meta.copy()
                reprojected_meta.update(
                    {
                        "dtype": "float32",  # Update data type to float32
                        "height": sentinel_shape[0],
                        "width": sentinel_shape[1],
                        "transform": sentinel_transform,
                        "crs": sentinel_crs,  # Update CRS
                        "nodata": np.nan,  # Update nodata value
                    }
                )

                # Write the reprojected TIFF
                output_tiff = os.path.join(output_folder, os.path.basename(tiff_file))
                with rasterio.open(output_tiff, "w", **reprojected_meta) as dst:
                    dst.write(reprojected_data, 1)

            logging.info(f"Reprojected TIFF saved: {output_tiff}")
        except Exception as e:
            logging.error(f"Error processing {tiff_file}: {e}")

    logging.info(
        "Reprojection completed. Reprojected TIFFs saved to the reprojected folder."
    )

    # Optionally, copy the sentinel.tif to the output folder
    shutil.copy2(sentinel_tiff_path, output_folder)
    logging.info(f"Sentinel reference TIFF copied to {output_folder}.")
    return True


def remove_sentinel3_outlier(
    input_folder, start_date, constant_value=np.nan, output_folder=None
):
    # List all TIFF files in the input folder
    tiff_files = [f for f in os.listdir(input_folder) if f.endswith(".tif")]

    # Extract month from start_date
    month = int(start_date.split("-")[1])

    # Define thresholds based on month
    if month in [1, 2]:
        threshold_low = -15
        threshold_high = 40
    elif month in [3, 4]:
        threshold_low = -10
        threshold_high = 50
    elif month in [5, 6]:
        threshold_low = -5
        threshold_high = 60
    elif month in [7, 8]:
        threshold_low = 0
        threshold_high = 60
    elif month in [9, 10]:
        threshold_low = -15
        threshold_high = 45
    else:
        threshold_low = 0
        threshold_high = 30

    # If no output folder is provided, use the input folder
    if output_folder is None:
        output_folder = input_folder

    # Loop through all TIFF files in the input folder
    for tiff_file in tiff_files:
        input_tiff_path = os.path.join(input_folder, tiff_file)
        output_tiff_path = os.path.join(output_folder, tiff_file)  # New file path

        # Open the input TIFF file
        with rasterio.open(input_tiff_path) as src:
            # Read the raster data
            image = src.read(1)

            # Replace NaN values with constant_value
            image = image.astype(float)  # Convert to float to allow NaN values
            image[np.isnan(image)] = constant_value

            # Replace values less than threshold_low or greater than threshold_high with constant_value
            image[(image < threshold_low) | (image > threshold_high)] = constant_value

            # Get metadata for the output TIFF
            profile = src.profile

            # Write the modified raster data to the output GeoTIFF file
            with rasterio.open(output_tiff_path, "w", **profile) as dst:
                dst.write(image, 1)

            print(f"Modified TIFF file saved at: {output_tiff_path}")
    return True

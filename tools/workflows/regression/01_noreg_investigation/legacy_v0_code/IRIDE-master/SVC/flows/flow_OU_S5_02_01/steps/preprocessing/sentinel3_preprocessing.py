
import os
from glob import glob
import netCDF4 as nc
import numpy as np
import pandas as pd
import rasterio
from rasterio import features
from shapely.geometry import Polygon


def process_sentinel3_files(input_folder, output_dir, target_x_pixel_size):
    file_paths = glob(os.path.join(input_folder, "*.SEN3"))
    for file_path in file_paths:
        # Extract file name and date
        file_name = os.path.basename(file_path)
        product_name = file_name  # Extract product name from file name

        # Read latitude, longitude, LST, bayes_in, and confidence_in from NetCDF files
        climate_filepath = os.path.join(file_path, "LST_in.nc")
        cart_filepath = os.path.join(file_path, "geodetic_in.nc")
        flags_filepath = os.path.join(file_path, "flags_in.nc")

        with nc.Dataset(cart_filepath, "r") as ncfile:
            latitude = ncfile.variables["latitude_in"][:]
            longitude = ncfile.variables["longitude_in"][:]

        with nc.Dataset(climate_filepath, "r") as ncfile:
            lst = ncfile.variables["LST"][:]

        with nc.Dataset(flags_filepath, "r") as ncfile:
            bayes_in = ncfile.variables["bayes_in"][:].flatten()
            confidence_in = ncfile.variables["confidence_in"][:].flatten()

        # Convert Kelvin to Celsius
        lst = lst - 273.15

        # Create a DataFrame
        LST_DF = pd.DataFrame(
            {
                "lon": longitude.flatten(),
                "lat": latitude.flatten(),
                "LST": lst.flatten(),
            }
        )

        # Set LST values to NaN where bayes_in equals 2 or confidence_in equals 16384
        mask = (bayes_in == 2) | (confidence_in == 16384)
        LST_DF.loc[mask, "LST"] = np.nan
        mask_ocean = (confidence_in & 0b1) == 0b1

        # Calculate the pixel size based on the target_x_pixel_size
        y_pixel_size = target_x_pixel_size
        x_pixel_size = target_x_pixel_size

        # Calculate ncol based on the x pixel size
        ncol = int((longitude.max() - longitude.min()) / x_pixel_size)
        nrow = int((latitude.max() - latitude.min()) / y_pixel_size)

        # Create the 'geometry' column based on the latitude and longitude
        LST_DF["geometry"] = [
            Polygon(
                [
                    (lon, lat),
                    (lon + x_pixel_size, lat),
                    (lon + x_pixel_size, lat - y_pixel_size),
                    (lon, lat - y_pixel_size),
                ]
            )
            for lon, lat in zip(LST_DF["lon"], LST_DF["lat"])
        ]

        # Set up a raster using rasterio with correct pixel sizes
        output_raster = f"{product_name}.tif"
        output_path = os.path.join(
            output_dir, output_raster
        )  # Full path to output raster
        with rasterio.open(
            output_path,  # Save in the specified output directory
            "w",
            driver="GTiff",
            height=nrow,
            width=ncol,
            count=1,
            dtype=rasterio.float64,
            crs="EPSG:4326",
            transform=rasterio.transform.from_origin(
                longitude.min(), latitude.max(), x_pixel_size, y_pixel_size
            ),
            # Use correct pixel sizes
        ) as dst:
            shapes = (
                (geom, val) for geom, val in zip(LST_DF["geometry"], LST_DF["LST"])
            )
            burned = features.rasterize(
                shapes=shapes,
                out_shape=(nrow, ncol),
                transform=rasterio.transform.from_origin(
                    longitude.min(), latitude.max(), x_pixel_size, y_pixel_size
                ),
                # Use correct pixel sizes
                all_touched=True,
            )
            dst.write(burned, 1)

        print(f"Processed file: {file_name}")
    return True

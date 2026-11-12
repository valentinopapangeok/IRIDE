import os
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import from_bounds
from rasterio.transform import from_origin
import numpy as np
import geopandas as gpd
from rasterio.mask import mask
import h5py
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
from sklearn.metrics import mean_squared_error


def convert_gosat(gosat_file: str, var):
    """
    Convert a GOSAT HDF5 file to a georeferenced TIFF raster.

    Parameters
    ----------
    gosat_file : str
        Path to the input GOSAT HDF5 file.
    var : str
        Variable to extract from the file (e.g., 'CH4' or 'CO2').

    Returns
    -------
    str
        Path to the created georeferenced TIFF file.

    Notes
    -----
    - Missing values (-9999) are replaced with -999.
    - Values are scaled by 1000 (e.g., CH4 from ppm to ppb).
    - Output raster uses EPSG:4326 CRS.
    """
    with h5py.File(gosat_file, "r") as f:
        data = f[f"Data/mixingRatio/X{var}BiasCorrected"][:]
        lat_data = f["Data/geolocation/latitude"][:]
        lon_data = f["Data/geolocation/longitude"][:]

    data[data == -9999.0] = -999
    data = data * 1000  # CH4: ppm -> ppb

    lat_min, lat_max = np.nanmin(lat_data), np.nanmax(lat_data)
    lon_min, lon_max = np.nanmin(lon_data), np.nanmax(lon_data)

    res_x = (lon_max - lon_min) / data.shape[1]
    res_y = (lat_max - lat_min) / data.shape[0]

    transform = from_origin(lon_min, lat_max, res_x, res_y)
    tiff_path = gosat_file.replace('.h5', '.tif')
    with rasterio.open(
            tiff_path,
            "w",
            driver="GTiff",
            height=data.shape[0],
            width=data.shape[1],
            count=1,
            dtype=str(data.dtype),
            crs="EPSG:4326",
            transform=transform,
            nodata=-999
    ) as dst:
        dst.write(data, 1)
    return tiff_path


def mask_with_shapefile(raster_path, shapefile_path):
    """
    Clip and mask a raster using geometries from a shapefile.

    Parameters
    ----------
    raster_path : str
        Path to the input raster file.
    shapefile_path : str
        Path to the shapefile for masking.

    Returns
    -------
    numpy.ndarray
        Masked raster array (cropped to shapefile bounds).
    """
    with rasterio.open(raster_path) as src:
        shape = gpd.read_file(shapefile_path)
        shape = shape.to_crs(src.crs)
        geometries = shape.geometry.values

        out_image, out_transform = mask(src, geometries, crop=True)
        out_image = out_image[0]
    return out_image


def calculate_statistics(low_res_data, high_res_data, year, month):
    """
    Calculate and print RMSE, min-max difference, and relative RMSE between two datasets.

    Parameters
    ----------
    low_res_data : numpy.ndarray
        Low-resolution raster data (e.g., GOSAT).
    high_res_data : numpy.ndarray
        High-resolution raster data (e.g., IRIDE).
    year : int
        Year of the data.
    month : int
        Month of the data.

    Notes
    -----
    - Only valid pixels (non-NaN and not nodata) are used.
    - Prints RMSE, min-max difference, and rRMSE as percentages.
    """
    mask = (
            (~np.isnan(low_res_data)) &
            (~np.isnan(high_res_data)) &
            (low_res_data != -999000) &  # GOSAT nodata corrected
            (high_res_data != -999)  # IRIDE nodata
    )
    x = low_res_data[mask].flatten()
    y = high_res_data[mask].flatten()
    rmse = np.sqrt(mean_squared_error(x, y))
    print(f"RMSE: {year}-{month:02d} - {rmse:.2f} ppb")
    print(f"minmax: {year}-{month:02d} - {(np.max(np.concatenate([x, y])) - np.min(np.concatenate([x, y]))):.2f} ppb")
    print(f"rRMSE: {year}-{month:02d} - {rmse / (np.mean(y)) * 100:.2f}%")


def clip_and_resample(global_tiff, high_res_tiff, output_tiff, prod_id):
    """
    Crop a global low-resolution raster to the bounds of a high-resolution raster
    and resample the high-resolution raster to match the low-resolution grid.

    Parameters
    ----------
    global_tiff : str
        Path to the global low-resolution raster (e.g., GOSAT).
    high_res_tiff : str
        Path to the high-resolution raster (e.g., IRIDE).
    output_tiff : str
        Path to save the resampled high-resolution raster.
    prod_id : str
        Product identifier (e.g., 'S5-02-07' or 'S5-02-08').

    Returns
    -------
    tuple of numpy.ndarray
        low_res_cropped : Cropped low-resolution raster array.
        high_res_resampled : Resampled high-resolution raster array.

    Raises
    ------
    ValueError
        If CRS do not match or rasters do not overlap.
    """
    with rasterio.open(high_res_tiff) as high_res:
        high_res_bounds = high_res.bounds
        high_res_crs = high_res.crs

    with rasterio.open(global_tiff) as low_res:
        if low_res.crs != high_res_crs:
            raise ValueError("CRS mismatch.")

        if prod_id in high_res_tiff:
            minx = max(low_res.bounds.left, high_res_bounds.left)
            miny = max(low_res.bounds.bottom, high_res_bounds.bottom)
            maxx = min(low_res.bounds.right, high_res_bounds.right)
            maxy = min(low_res.bounds.top, high_res_bounds.top)
            transform_fix = lambda t: t._replace(e=t.e, f=high_res_bounds.top)
        else:
            raise ValueError("Variabile non riconosciuta.")

        if minx >= maxx or miny >= maxy:
            print(miny, maxy, minx, maxx)
            raise ValueError("Raster non si sovrappongono.")

        window = from_bounds(minx, miny, maxx, maxy, transform=low_res.transform)
        window = window.round_offsets().round_lengths()
        low_res_cropped = low_res.read(1, window=window)
        low_res_transform = low_res.window_transform(window)

        low_res_profile = low_res.profile.copy()
        low_res_profile.update({
            "height": low_res_cropped.shape[0],
            "width": low_res_cropped.shape[1],
            "transform": transform_fix(low_res_transform)
        })

    low_res_cropped_tiff = output_tiff.replace(".tif", "_lowres_cropped.tif")
    with rasterio.open(low_res_cropped_tiff, "w", **low_res_profile) as dst_low:
        dst_low.write(low_res_cropped, 1)

    with rasterio.open(high_res_tiff) as high_res:
        data_resampled = high_res.read(
            out_shape=(1, low_res_cropped.shape[0], low_res_cropped.shape[1]),
            resampling=Resampling.average
        )

    with rasterio.open(output_tiff, "w", **low_res_profile) as dst:
        dst.write(data_resampled[0], 1)

    return low_res_cropped, data_resampled[0]


def extract_valid_pixels(low_res_data, high_res_data):
    """
    Extract valid pixels from low- and high-resolution datasets for comparison.

    Parameters
    ----------
    low_res_data : numpy.ndarray
        Low-resolution raster array (e.g., GOSAT).
    high_res_data : numpy.ndarray
        High-resolution raster array (e.g., IRIDE).

    Returns
    -------
    tuple of numpy.ndarray
        Flattened arrays of valid low-res and high-res pixels.

    Notes
    -----
    - Valid pixels are those that are not NaN and not nodata (-999000 for GOSAT, -999 for IRIDE).
    """
    mask = (
            (~np.isnan(low_res_data)) &
            (~np.isnan(high_res_data)) &
            (low_res_data != -999000) &
            (high_res_data != -999)
    )
    return low_res_data[mask].flatten(), high_res_data[mask].flatten()


import os
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
from sklearn.metrics import mean_squared_error


def run_iride_gosat_validation_methane(base_workdir: str):
    """
    Run the full IRIDE vs GOSAT validation workflow:
    - Iterates over years and months
    - Converts GOSAT HDF5 files to TIFF
    - Clips/resamples high- and low-resolution rasters
    - Calculates statistics (RMSE, rRMSE)
    - Extracts valid pixels for each region
    - Saves a CSV with all pixel comparisons
    - Plots scatter of low-res vs high-res data with density coloring

    Parameters
    ----------
    base_workdir : str
        Base path to the IRIDE validation directory.
        Expected subfolders: 'IRIDE/output', 'validation_dataset'

    Notes
    -----
    - The function uses previously defined helper functions:
      convert_gosat, clip_and_resample, calculate_statistics,
      mask_with_shapefile, extract_valid_pixels.
    - Only supports the 'Italia_intera' region if shapefiles are not provided.
    - Handles missing IRIDE files by using the fallback to the same month.
    """
    base_path = Path(base_workdir)
    iride_output = base_path / "IRIDE" / "output"
    validation_dataset = base_path / "validation_dataset"

    regions = {
        "Italia_intera": None,
    }

    all_data = []

    for year in [2024, 2025]:
        start_month = 3 if year == 2024 else 1
        end_month = 2 if year == 2025 else 12

        for month in range(start_month, end_month + 1):
            try:
                # Determine IRIDE month
                if month == 12:
                    year_iride = year + 1
                    month_iride = 1
                else:
                    year_iride = year
                    month_iride = month + 1

                # Fallback if next month's IRIDE doesn't exist
                high_res_next = iride_output / f"IRIDE-S_S5-02-07_{year_iride}{month_iride:02d}_V0" / \
                                f"IRIDE-S_S5-02-07_{year_iride}{month_iride:02d}_V0.tif"
                if not high_res_next.exists():
                    year_iride = year
                    month_iride = month

                date_iride = f"{year_iride}{month_iride:02d}"
                date = f"{year}{month:02d}"

                high_res_tiff = iride_output / f"IRIDE-S_S5-02-07_{date_iride}_V0" / \
                                f"IRIDE-S_S5-02-07_{date_iride}_V0.tif"
                if not high_res_tiff.exists():
                    print(f"[{date}] File not found: {high_res_tiff}. Skipping.")
                    continue

                prod_id = high_res_tiff.stem.split('_')[1]
                var = 'CH4' if prod_id == 'S5-02-07' else 'CO2' if prod_id == 'S5-02-08' else None
                if var is None:
                    print(f"[{date}] Unknown product.")
                    continue

                folder = validation_dataset / f"SWIRL3{var}_{date}_V03.05" / f"SWIRL3{var}"
                gosat_files = [f for f in os.listdir(folder) if f.endswith('.h5')]
                if not gosat_files:
                    print(f"[{date}] No HDF5 files found in {folder}")
                    continue

                gosat_file = folder / gosat_files[0]
                gosat_tif = convert_gosat(str(gosat_file), var)

                output_tiff = validation_dataset / f"validation_{var}_{date}_resampled.tif"
                low_res_data, high_res_data = clip_and_resample(str(gosat_tif), str(high_res_tiff),
                                                                str(output_tiff), prod_id)

                calculate_statistics(low_res_data, high_res_data, year_iride, month_iride)

                for nome_regione, shapefile in regions.items():
                    try:
                        if shapefile:
                            low_res_masked = mask_with_shapefile(str(output_tiff), shapefile)
                            high_res_masked = mask_with_shapefile(str(high_res_tiff), shapefile)
                        else:
                            low_res_masked = low_res_data
                            high_res_masked = high_res_data

                        x, y = extract_valid_pixels(low_res_masked, high_res_masked)

                        for val_x, val_y in zip(x, y):
                            all_data.append({
                                "low_res": val_x,
                                "high_res": val_y,
                                "month": date,
                                "region": nome_regione
                            })

                        print(f"[{date} - {nome_regione}] Valid pixels: {len(x)}")

                    except Exception as e:
                        print(f"[{date} - {nome_regione}] Masking error: {e}")
                        continue

            except Exception as e:
                print(f"[{date}] Error: {e}")
                continue

    # Save final CSV
    df = pd.DataFrame(all_data)
    output_csv = validation_dataset / "all_months_validation_pixels_by_region_CH4.csv"
    df.to_csv(output_csv, index=False)
    print(f"Saved final CSV with {len(df)} rows: {output_csv}")

    # === PLOT ===
    df = pd.read_csv(output_csv)

    lower = np.percentile(df['high_res'], 0)
    upper = np.percentile(df['high_res'], 100)
    filtered_df = df[(df['high_res'] >= lower) & (df['high_res'] <= upper)]
    x = filtered_df['low_res'].values
    y = filtered_df['high_res'].values

    rmse = np.sqrt(mean_squared_error(y, x))
    maxmin = np.max(y) - np.min(y)
    rrmse = round(rmse / maxmin * 100, 2)
    print(rmse, maxmin)
    print('RMSE:', rmse)
    print('Min,Mean,Max:', np.min(np.concatenate([x, y])), np.mean(np.concatenate([x, y])),
          np.max(np.concatenate([x, y])))
    print('rRMSE:', rrmse, '%')
    print('N punti:', len(x))

    # Density for color
    xy = np.vstack([x, y])
    z = gaussian_kde(xy)(xy)
    idx = z.argsort()
    x, y, z = x[idx], y[idx], z[idx]

    lim = max(np.max(x), np.max(y)) + 0.02 * max(np.max(x), np.max(y))

    plt.figure(figsize=(10, 10))
    sc = plt.scatter(x, y, c=z, s=30, cmap='magma', alpha=0.7)
    plt.plot([0, lim], [0, lim], '--', color='red')
    plt.axis('equal')
    plt.autoscale()
    plt.title('Validation IRIDE vs GOSAT')
    plt.xlabel('GOSAT-XCH4 [ppb]')
    plt.ylabel('S5-02-07-XCH4 [ppb]')
    cbar = plt.colorbar(sc, label='Density')
    plt.xlim(1500, 2500)
    plt.ylim(1500, 2500)
    plt.text(1500 + (2500 - 1500) * 0.05, 2500 - (2500 - 1500) * 0.05, f'rRMSE: {rrmse:.2f}%', fontsize=12)
    plt.text(1500 + (2500 - 1500) * 0.05, 2500 - (2500 - 1500) * 0.10, f'N: {len(x)}', fontsize=12)
    plt.grid(True)
    plt.tight_layout()
    plt.show()

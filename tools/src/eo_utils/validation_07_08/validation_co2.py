import os
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import from_bounds
from rasterio.transform import from_origin
from rasterio.mask import mask
import h5py
import numpy as np
import geopandas as gpd
import pandas as pd
from pathlib import Path
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
from sklearn.metrics import mean_squared_error


# ------------------------
# Helper functions
# ------------------------

def convert_gosat(gosat_file: str, var, scale=1, nodata=-999):
    """Convert GOSAT HDF5 to georeferenced TIFF."""
    with h5py.File(gosat_file, "r") as f:
        data = f[f"Data/mixingRatio/X{var}BiasCorrected"][:]
        lat_data = f["Data/geolocation/latitude"][:]
        lon_data = f["Data/geolocation/longitude"][:]

    data[data == -9999.0] = nodata
    data = data * scale

    lat_min, lat_max = np.nanmin(lat_data), np.nanmax(lat_data)
    lon_min, lon_max = np.nanmin(lon_data), np.nanmax(lon_data)

    res_x = (lon_max - lon_min) / data.shape[1]
    res_y = (lat_max - lat_min) / data.shape[0]

    transform = from_origin(lon_min, lat_max, res_x, res_y)
    tiff_path = gosat_file.replace('.h5', '.tif')
    with rasterio.open(
        tiff_path, "w", driver="GTiff",
        height=data.shape[0], width=data.shape[1],
        count=1, dtype=str(data.dtype),
        crs="EPSG:4326", transform=transform,
        nodata=nodata
    ) as dst:
        dst.write(data, 1)
    return tiff_path


def clip_and_resample(global_tiff, high_res_tiff, output_tiff):
    """Clip GOSAT to IRIDE bounds and resample IRIDE to GOSAT resolution."""
    with rasterio.open(high_res_tiff) as hi:
        hi_bounds = hi.bounds
        hi_crs = hi.crs

    with rasterio.open(global_tiff) as lo:
        if lo.crs != hi_crs:
            raise ValueError("CRS mismatch")

        minx = max(lo.bounds.left, hi_bounds.left)
        miny = max(lo.bounds.bottom, hi_bounds.bottom)
        maxx = min(lo.bounds.right, hi_bounds.right)
        maxy = min(lo.bounds.top, hi_bounds.top)

        if minx >= maxx or miny >= maxy:
            raise ValueError("Rasters do not overlap")

        window = from_bounds(minx, miny, maxx, maxy, lo.transform).round_offsets().round_lengths()
        low_res_cropped = lo.read(1, window=window)
        transform = lo.window_transform(window)
        profile = lo.profile.copy()
        profile.update(height=low_res_cropped.shape[0], width=low_res_cropped.shape[1], transform=transform)

    with rasterio.open(high_res_tiff) as hi:
        high_res_resampled = hi.read(
            out_shape=(1, low_res_cropped.shape[0], low_res_cropped.shape[1]),
            resampling=Resampling.average
        )[0]

    with rasterio.open(output_tiff, "w", **profile) as dst:
        dst.write(high_res_resampled, 1)

    return low_res_cropped, high_res_resampled


def extract_valid_pixels(low_res_data, high_res_data, nodata_low=-999, nodata_high=-999):
    mask = (~np.isnan(low_res_data)) & (~np.isnan(high_res_data)) & (low_res_data != nodata_low) & (high_res_data != nodata_high)
    return low_res_data[mask].flatten(), high_res_data[mask].flatten()


# ------------------------
# Main function
# ------------------------

def run_iride_gosat_validation_CO2(base_workdir):
    """
    Full workflow for S5-02-08 (CO2)
    """
    base = Path(base_workdir)
    iride_out = base / "IRIDE" / "output"
    val_ds = base / "validation_dataset"

    regions = {"Italia_intera": None}
    all_data = []

    for year in [2024, 2025]:
        start_month = 3 if year == 2024 else 1
        end_month = 2 if year == 2025 else 12

        for month in range(start_month, end_month + 1):
            date = f"{year}{month:02d}"
            high_res_tiff = iride_out / f"IRIDE-S_S5-02-08_{date}_V0" / f"IRIDE-S_S5-02-08_{date}_V0.tif"
            if not high_res_tiff.exists():
                print(f"[{date}] IRIDE file not found. Skipping.")
                continue

            gosat_folder = val_ds / f"SWIRL3CO2_{date}_V03.05" / "SWIRL3CO2"
            gosat_files = list(gosat_folder.glob("*.h5"))
            if not gosat_files:
                print(f"[{date}] No GOSAT files found. Skipping.")
                continue

            gosat_tif = convert_gosat(str(gosat_files[0]), var="CO2", scale=1, nodata=-999)
            output_tiff = val_ds / f"validation_CO2_{date}_resampled.tif"
            low_res_data, high_res_data = clip_and_resample(str(gosat_tif), str(high_res_tiff), str(output_tiff))
            x, y = extract_valid_pixels(low_res_data, high_res_data, nodata_low=-999, nodata_high=-999)

            for nome_regione, shapefile in regions.items():
                if shapefile:
                    low_res_masked = mask_with_shapefile(str(output_tiff), shapefile)
                    high_res_masked = mask_with_shapefile(str(high_res_tiff), shapefile)
                    x, y = extract_valid_pixels(low_res_masked, high_res_masked)

                for vx, vy in zip(x, y):
                    all_data.append({"low_res": vx, "high_res": vy, "month": date, "region": nome_regione})

            print(f"[{date}] Valid pixels: {len(x)}")

    # Save CSV
    df = pd.DataFrame(all_data)
    output_csv = val_ds / "all_months_validation_pixels_CO2.csv"
    df.to_csv(output_csv, index=False)
    print(f"Saved CSV: {output_csv}")

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
    print('RMSE:', rmse)
    print('rRMSE:', rrmse, '%')
    print('N punti:', len(x))

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
    plt.xlabel('GOSAT-XCO2 [ppm]')
    plt.ylabel('S5-02-08-XCO2 [ppm]')
    plt.colorbar(sc, label='Density')
    plt.xlim(400, 450)
    plt.ylim(400, 450)
    plt.text(400 + (450 - 400) * 0.05, 450 - (450 - 400) * 0.05, f'rRMSE: {rrmse:.2f}%', fontsize=12)
    plt.text(400 + (450 - 400) * 0.05, 450 - (450 - 400) * 0.10, f'N: {len(x)}', fontsize=12)
    plt.grid(True)
    plt.tight_layout()
    plt.show()

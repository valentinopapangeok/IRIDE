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


def convert_gosat(gosat_file: str, var):
    with h5py.File(gosat_file, "r") as f:
        data = f[f"Data/mixingRatio/X{var}BiasCorrected"][:]
        lat_data = f["Data/geolocation/latitude"][:]
        lon_data = f["Data/geolocation/longitude"][:]

    data[data == -9999.0] = -999

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
    with rasterio.open(raster_path) as src:
        shape = gpd.read_file(shapefile_path)
        shape = shape.to_crs(src.crs)
        geometries = shape.geometry.values

        out_image, out_transform = mask(src, geometries, crop=True)
        out_image = out_image[0]
    return out_image


def calculate_statistics(low_res_data, high_res_data, year, month):
    from sklearn.metrics import mean_squared_error
    mask = (~np.isnan(low_res_data) & ~np.isnan(high_res_data) &
            (low_res_data != -999) & (high_res_data != -999))
    x = low_res_data[mask].flatten()
    y = high_res_data[mask].flatten()
    rmse = np.sqrt(mean_squared_error(x, y))
    print(f"RMSE: {year}-{month:02d} - {rmse:.2f} ppm")
    print(f"minmax: {year}-{month:02d} - {(np.max(np.concatenate([x, y]))-np.min(np.concatenate([x, y]))):.2f} ppb")
    print(f"rRMSE: {year}-{month:02d} - {rmse/(np.mean(y))*100:.2f}%")


def clip_and_resample(global_tiff, high_res_tiff, output_tiff, prod_id):
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
            print(miny, maxy, minx,maxx)
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
    mask = (~np.isnan(low_res_data) & ~np.isnan(high_res_data) &
            (low_res_data != -999) & (high_res_data != -999))
    x = low_res_data[mask].flatten()
    y = high_res_data[mask].flatten()
    return x, y


all_data = []

regions = {
    "Italia_intera": None,
    "Nord_Italia": r"D:\PhD\IRIDE\CH4_production\common\shapefiles\Nord_Italia\nord_italia.shp",
    "Centro_Italia": r"C:\Users\danie\Downloads\shps\centro_italia.shp",
    "Sud_Italia": r"C:\Users\danie\Downloads\shps\sud.shp"
}

# for year in [2024, 2025]:
#     start_month = 3 if year == 2024 else 1
#     end_month = 2 if year == 2025 else 12
#
#     for month in range(start_month, end_month + 1):
#         try:
#             if month == 12:
#                 year_iride = year + 1
#                 month_iride = 1
#             else:
#                 year_iride = year
#                 month_iride = month + 1
#             date_iride = f"{year_iride}{month_iride:02d}"
#             date = f"{year}{month:02d}"
#
#             high_res_tiff = fr"D:\IRIDE\output\IRIDE-S_S5-02-08_{date_iride}_V0\IRIDE-S_S5-02-08_{date_iride}_V0.tif"
#             if not os.path.exists(high_res_tiff):
#                 print(f"[{date}] File non trovato: {high_res_tiff}. Si salta l'iterazione.")
#                 continue
#             prod_id = os.path.basename(high_res_tiff).split('_')[1]
#             if prod_id == 'S5-02-07':
#                 var = 'CH4'
#             elif prod_id == 'S5-02-08':
#                 var = 'CO2'
#             else:
#                 print(f"[{date}] Prodotto non riconosciuto.")
#                 continue
#
#             folder = fr"D:\PhD\IRIDE\Validation_dataset\SWIRL3{var}_{date}_V03.05\SWIRL3{var}"
#             gosat_files = [f for f in os.listdir(folder) if f.endswith('.h5')]
#             if not gosat_files:
#                 print(f"[{date}] Nessun file HDF5 trovato.")
#                 continue
#
#             gosat_file = os.path.join(folder, gosat_files[0])
#             gosat_tif = convert_gosat(gosat_file, var)
#
#             output_tiff = fr"D:\PhD\IRIDE\Validation_dataset\validation_{var}_{date}_resampled.tif"
#             low_res_data, high_res_data = clip_and_resample(gosat_tif, high_res_tiff, output_tiff, prod_id)
#
#
#             calculate_statistics(low_res_data, high_res_data, year_iride, month_iride)
#             for nome_regione, shapefile in regions.items():
#                 try:
#                     if shapefile:
#                         low_res_masked = mask_with_shapefile(output_tiff, shapefile)
#                         high_res_masked = mask_with_shapefile(high_res_tiff, shapefile)
#                     else:
#                         low_res_masked = low_res_data
#                         high_res_masked = high_res_data
#
#                     x, y = extract_valid_pixels(low_res_masked, high_res_masked)
#
#                     for val_x, val_y in zip(x, y):
#                         all_data.append({
#                             "low_res": val_x,
#                             "high_res": val_y,
#                             "month": date,
#                             "region": nome_regione
#                         })
#
#                     print(f"[{date} - {nome_regione}] Pixel validi: {len(x)}")
#
#                 except Exception as e:
#                     print(f"[{date} - {nome_regione}] Errore durante la maschera: {e}")
#                     continue
#
#         except Exception as e:
#             print(f"[{date}] Errore: {e}")
#             continue

# === SALVATAGGIO FINALE ===
df = pd.DataFrame(all_data)
from scipy.stats import pearsonr

output_csv = r"D:\PhD\IRIDE\Validation_dataset\all_months_validation_pixels_by_region_CO2.csv"
# df.to_csv(output_csv, index=False)
# print(f"Salvato CSV finale con {len(df)} righe: {output_csv}")

# === PLOT ===
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde
from sklearn.metrics import mean_squared_error
import pandas as pd


df = pd.read_csv(output_csv)

plt.figure(figsize=(8, 6))
df['low_res'] = df['low_res']
lower = np.percentile(df['high_res'], 0)
upper = np.percentile(df['high_res'], 100)
# lower_low = np.percentile(df['low_res'], 5)
# upper_low = np.percentile(df['low_res'], 95)
filtered_df = df[(df['high_res'] >= lower) & (df['high_res'] <= upper)]
#  & (df['low_res'] >= lower_low) & (df['low_res'] <= upper_low)
x = filtered_df['low_res'].values
y = filtered_df['high_res'].values

# RMSE e rRMSE
rmse = mean_squared_error(y, x, squared=False)
maxmin = np.max(y) - np.min(y)
rrmse = round(rmse / maxmin * 100, 2)
print(rmse, maxmin)
print('RMSE:', rmse)
print('Min,Mean,Max:', np.min(np.concatenate([x, y])), np.mean(np.concatenate([x, y])), np.max(np.concatenate([x, y])))
print('rRMSE:', rrmse,'%')
print('N punti:', len(x))

# Density per colore punti
xy = np.vstack([x, y])
z = gaussian_kde(xy)(xy)

# Ordino per densità
idx = z.argsort()
x, y, z = x[idx], y[idx], z[idx]

# Limiti per asse (fare limiti simmetrici basati su min max dei dati)
lim = max(np.max(x), np.max(y)) + 0.02 * max(np.max(x), np.max(y))

plt.figure(figsize=(10, 10))
sc = plt.scatter(x, y, c=z, s=30, cmap='magma', alpha=0.7)

# Linea 1:1
plt.plot([0, lim], [0, lim], '--', color='red')
plt.xlim(400, lim)
plt.ylim(400, lim)
plt.title('Validation IRIDE vs GOSAT')
plt.xlabel('GOSAT-XC02 [ppm]')
plt.ylabel('S5-02-08-XC02 [ppm]')
cbar = plt.colorbar(sc, label='Density')
xmin, xmax = 400, lim
ymin, ymax = 400, lim
# Testo statistiche sul grafico (posiziona in alto a sinistra)
plt.text(xmin + (xmax - xmin)*0.05, ymax - (ymax - ymin)*0.05, f'rRMSE: {rrmse}', fontsize=12)
plt.text(xmin + (xmax - xmin)*0.05, ymax - (ymax - ymin)*0.10, f'N: {len(x)}', fontsize=12)

plt.grid(True)
plt.tight_layout()
plt.show()
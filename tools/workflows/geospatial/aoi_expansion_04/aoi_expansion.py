import xarray as xr
import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import rasterio.features
from shapely.geometry import shape
import numpy as np
import warnings
import os
from pathlib import Path

warnings.filterwarnings('ignore')

# ==========================================
# SET YOUR MAIN FOLDER DIRECTORY HERE
# ==========================================
BASE_DIR = Path(__file__).resolve().parent

# ==========================================
# 1. LOAD YOUR LAND AND SEA SHAPEFILES
# ==========================================
italy_land_gdf = gpd.read_file(BASE_DIR / 'data/Italia/italia.shp')
italy_sea_gdf = gpd.read_file(BASE_DIR / 'data/Italia_sst/central_Mediterranean_sea.shp')

# Ensure Coordinate Reference Systems (CRS) match
if italy_sea_gdf.crs != italy_land_gdf.crs:
    italy_sea_gdf = italy_sea_gdf.to_crs(italy_land_gdf.crs)

# ==========================================
# 2. SHOW TOTAL AOI (LAND + SEA) & EXPORT
# ==========================================
print("Generating Total Land and Sea AOI...")
total_land_and_sea = pd.concat([italy_land_gdf, italy_sea_gdf], ignore_index=True).dissolve()

fig, ax = plt.subplots(figsize=(8, 8))
fig.canvas.manager.set_window_title('01_Total_Possible_AOI')
total_land_and_sea.plot(ax=ax, color='lightblue', edgecolor='blue')
italy_land_gdf.plot(ax=ax, color='orange', edgecolor='red')
plt.title("Step 1: Total Possible AOI (Italy Land + Official Sea)")

plt.savefig(f'{BASE_DIR}/plot_01_total_possible_aoi.png', bbox_inches='tight', dpi=300)
plt.show()

# --- NEW: Create folder and save the Total AOI shapefile ---
total_aoi_name = 'italy_total_land_and_sea_aoi'
total_aoi_folder = f'{BASE_DIR}/{total_aoi_name}'
os.makedirs(total_aoi_folder, exist_ok=True)

total_aoi_output = f'{total_aoi_folder}/{total_aoi_name}.shp'
total_land_and_sea.to_file(total_aoi_output)
print(f"Success! Total Land + Sea AOI saved to:\n{total_aoi_folder}/")

# ==========================================
# 3. RECREATE EMPIRICAL RADAR FOOTPRINT
# ==========================================
grib_path = f'{BASE_DIR}/data/data-20260313T020000Z-4fd1b93d-81fd-428a-85dd-acbe286a7197.grib'
ds = xr.open_dataset(grib_path, engine='cfgrib', backend_kwargs={'indexpath': ''})

# Check which variable name the file uses
if 'tprate' in ds:
    precip_name = 'tprate'
elif 'rdpr' in ds:
    precip_name = 'rdpr'
else:
    raise ValueError(f"Could not find precipitation data! Available variables: {list(ds.keys())}")

# Orient, squeeze, and mask using the detected variable
tprate = ds[precip_name].sortby('latitude', ascending=False).sortby('longitude', ascending=True)

if len(tprate.dims) > 2:
    tprate = tprate.isel({dim: 0 for dim in tprate.dims if dim not in ['latitude', 'longitude']})

mask_da = tprate.notnull().astype(int)
mask_array = mask_da.values
lons = mask_da['longitude'].values
lats = mask_da['latitude'].values

# Vectorize into a polygon
from rasterio.transform import from_bounds
transform = from_bounds(lons.min(), lats.min(), lons.max(), lats.max(), len(lons), len(lats))
shapes = rasterio.features.shapes(mask_array.astype(np.int16), mask=(mask_array == 1), transform=transform)
polygons = [shape(geom) for geom, value in shapes]

radar_gdf = gpd.GeoDataFrame(geometry=polygons, crs="EPSG:4326").dissolve()

# Align CRS before the intersection
if radar_gdf.crs != italy_sea_gdf.crs:
    radar_gdf = radar_gdf.to_crs(italy_sea_gdf.crs)

# ==========================================
# 4. INTERSECT AND MERGE
# ==========================================
# This keeps ONLY the parts of the radar that overlap with the Italy Sea AOI
radar_sea_intersection = gpd.overlay(radar_gdf, italy_sea_gdf, how='intersection')

# Merge the Land and the restricted Radar Sea area
final_custom_aoi = pd.concat([italy_land_gdf, radar_sea_intersection], ignore_index=True).dissolve()

# ==========================================
# 5. PLOT FINAL RESULT AND EXPORT
# ==========================================
fig, ax = plt.subplots(figsize=(8, 8))
fig.canvas.manager.set_window_title('02_Final_Product_Intersection')
final_custom_aoi.plot(ax=ax, color='lightgreen', edgecolor='black')
italy_land_gdf.plot(ax=ax, color='none', edgecolor='red', linewidth=1)
plt.title("Final Product AOI: Italy Land + Radar/Sea Intersection")

plt.savefig(f'{BASE_DIR}/plot_02_radar_sea_intersection.png', bbox_inches='tight', dpi=300)
plt.show()

# --- Create folder and save the Custom AOI shapefile ---
custom_aoi_name = 'italy_land_and_radar_sea_aoi'
custom_aoi_folder = f'{BASE_DIR}/{custom_aoi_name}'
os.makedirs(custom_aoi_folder, exist_ok=True)

output_path = f'{custom_aoi_folder}/{custom_aoi_name}.shp'
final_custom_aoi.to_file(output_path)
print(f"Success! Final custom AOI saved to:\n{custom_aoi_folder}/")

# ==========================================
# 6. CREATE ITALY + 12 NM TERRITORIAL WATERS
# ==========================================
print("\nCalculating official 12 Nautical Mile territorial waters...")

# 1. Reproject to metric (UTM Zone 32N) for accurate distance math
italy_metric = italy_land_gdf.to_crs("EPSG:32632")

# 2. Buffer by exactly 12 Nautical Miles (1 NM = 1852 meters)
territorial_buffer_metric = italy_metric.buffer(22224)

# 3. Convert back to Lat/Lon
territorial_buffer_gdf = gpd.GeoDataFrame(geometry=territorial_buffer_metric, crs="EPSG:32632").to_crs("EPSG:4326")

# 4. Restrict to Official Borders
italy_territorial_aoi = gpd.overlay(territorial_buffer_gdf, total_land_and_sea, how='intersection')
italy_territorial_aoi = italy_territorial_aoi.dissolve()

# ==========================================
# PLOT: ITALY + TERRITORIAL WATERS
# ==========================================
fig, ax = plt.subplots(figsize=(8, 8))
fig.canvas.manager.set_window_title('03_Territorial_Waters_12NM')
italy_territorial_aoi.plot(ax=ax, color='teal', edgecolor='black', label='12 NM Territorial Waters')
italy_land_gdf.plot(ax=ax, color='none', edgecolor='red', linewidth=1, label='Italy Coastline')

plt.title("Final AOI: Italy Land + 12 NM Territorial Waters")
plt.legend()

plt.savefig(f'{BASE_DIR}/plot_03_territorial_waters.png', bbox_inches='tight', dpi=300)
plt.show()

# --- Create folder and save the Territorial AOI shapefile ---
territorial_name = 'italy_territorial_waters_aoi'
territorial_folder = f'{BASE_DIR}/{territorial_name}'
os.makedirs(territorial_folder, exist_ok=True)

territorial_output = f'{territorial_folder}/{territorial_name}.shp'
italy_territorial_aoi.to_file(territorial_output)
print(f"Success! Territorial Waters AOI saved to:\n{territorial_folder}/")

# ==========================================
# 7. EXPORT RAW RADAR FOOTPRINT & RADAR SITES
# ==========================================
print("\nExporting raw radar footprint and radar site centers...")

# 1. Define known coastal radar sites (Longitude, Latitude)
coastal_radars = {
    'Monte Settepani (Liguria)': (8.195, 44.238),
    'Capo Caccia (Sardinia)': (8.163, 40.562),
    'Monte Rasu (Sardinia)': (8.991, 40.395),
    'Il Telegrafo (Livorno)': (9.940, 43.140),
    'Fiumicino (Lazio)': (12.210, 41.800),
    'Fossalon di Grado (Friuli)': (13.480, 45.720),
    'San Pietro Capofiume (Emilia)': (11.624, 44.654),
    'Pescara (Abruzzo)': (14.180, 42.430),
    'Gargano (Puglia)': (15.960, 41.740),
    'Ruvo di Puglia (Puglia)': (16.420, 41.110),
    'Torchiarolo (Puglia)': (18.040, 40.480),
    'Ischia (Campania)': (13.900, 40.730),
    'Monte Lauro (Sicily)': (14.830, 37.110),
    'Pettinengo (Piedmont)': (8.030, 45.610),
    'Gatttopardo (Calabria/Lazio)': (12.200, 41.800) # Re-calibrated approximation
}

# 2. Convert dictionary into a Point GeoDataFrame
from shapely.geometry import Point

points = [Point(lon, lat) for lon, lat in coastal_radars.values()]
radar_names = list(coastal_radars.keys())
sites_gdf = gpd.GeoDataFrame({'Radar_Name': radar_names}, geometry=points, crs="EPSG:4326")

# 3. Plot everything together
fig, ax = plt.subplots(figsize=(8, 8))
fig.canvas.manager.set_window_title('04_Raw_Radar_Coverage')

# Plot the raw blue footprint
radar_gdf.plot(ax=ax, color='blue', alpha=0.4, edgecolor='blue', label='Raw Radar Footprint')

# Plot the Italian Coastline
italy_land_gdf.plot(ax=ax, color='none', edgecolor='red', linewidth=1, label='Italy Coastline')

# Plot the Radar Centers as Yellow Stars
sites_gdf.plot(ax=ax, color='red', edgecolor='black', marker='.', markersize=150, zorder=5, label='Radar Sites')

plt.title("Reference AOI: Raw MISTRAL Radar Footprint with Site Centers")
plt.legend()

plt.savefig(f'{BASE_DIR}/plot_04_raw_radar_coverage.png', bbox_inches='tight', dpi=300)
plt.show()

# --- Create folder and save the Raw Radar Area shapefile ---
raw_radar_name = 'raw_radar_coverage_aoi'
raw_radar_folder = f'{BASE_DIR}/{raw_radar_name}'
os.makedirs(raw_radar_folder, exist_ok=True)

raw_radar_output = f'{raw_radar_folder}/{raw_radar_name}.shp'
radar_gdf.to_file(raw_radar_output)

# --- Create folder and save the Radar Point Centers shapefile ---
radar_points_name = 'radar_site_centers'
radar_points_folder = f'{BASE_DIR}/{radar_points_name}'
os.makedirs(radar_points_folder, exist_ok=True)

radar_points_output = f'{radar_points_folder}/{radar_points_name}.shp'
sites_gdf.to_file(radar_points_output)

print(f"Success! Raw Radar Coverage AOI saved to:\n{raw_radar_folder}/")
print(f"Success! Radar Site Points saved to:\n{radar_points_folder}/")

# ==========================================
# 8. CREATE ULTIMATE GUARANTEED AOI (TERRITORIAL + RADAR)
# ==========================================
print("\nCreating gap-proof AOI: 12 NM Territorial Minimum + Radar Expansion...")

# Merge the Territorial AOI (which includes land and the 12 NM gap-proof buffer)
# with the Radar/Sea intersection (which pushes out further where radar is available)
ultimate_aoi = pd.concat([italy_territorial_aoi, radar_sea_intersection], ignore_index=True).dissolve()

# ==========================================
# PLOT: THE ULTIMATE GUARANTEED AOI
# ==========================================
fig, ax = plt.subplots(figsize=(8, 8))
fig.canvas.manager.set_window_title('05_Ultimate_Guaranteed_AOI')

# Plot the new gap-proof boundary
ultimate_aoi.plot(ax=ax, color='mediumpurple', edgecolor='black', label='Ultimate Guaranteed AOI')

# Overlay the coastline for reference
italy_land_gdf.plot(ax=ax, color='none', edgecolor='red', linewidth=1, label='Italy Coastline')

plt.title("Ultimate AOI: 12 NM Minimum Guarantee + Radar Expansion")
plt.legend()

# Auto-save the plot
plt.savefig(f'{BASE_DIR}/plot_05_ultimate_guaranteed_aoi.png', bbox_inches='tight', dpi=300)
plt.show()

# --- Create folder and save the Ultimate AOI shapefile ---
ultimate_aoi_name = 'italy_guaranteed_min12nm_radar_aoi'
ultimate_aoi_folder = f'{BASE_DIR}/{ultimate_aoi_name}'
os.makedirs(ultimate_aoi_folder, exist_ok=True)

ultimate_aoi_output = f'{ultimate_aoi_folder}/{ultimate_aoi_name}.shp'
ultimate_aoi.to_file(ultimate_aoi_output)
print(f"Success! Ultimate Guaranteed AOI saved to:\n{ultimate_aoi_folder}/")

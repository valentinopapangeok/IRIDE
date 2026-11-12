import xarray as xr
import geopandas as gpd
from shapely.geometry import shape
import rasterio.features
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import warnings
from pathlib import Path

# Suppress some common GeoPandas/Shapely warnings to keep your terminal clean
warnings.filterwarnings('ignore')
BASE_DIR = Path(__file__).resolve().parent

# ==========================================
# 1. LOAD AND PREP THE RADAR DATA
# ==========================================
grib_path = BASE_DIR / 'data/data-20250820T094735Z-4290906a-dea1-47d6-a78b-0d03d748ec21.grib'

# Open the file, bypassing the .idx cache to avoid IOProblemErrors
ds = xr.open_dataset(grib_path, engine='cfgrib', backend_kwargs={'indexpath': ''})
tprate = ds['tprate']

# Fix geographic orientation (Row 0 must be North, Col 0 must be West)
tprate = tprate.sortby('latitude', ascending=False).sortby('longitude', ascending=True)

# Squeeze down to strictly 2D (Latitude x Longitude)
if len(tprate.dims) > 2:
    tprate = tprate.isel({dim: 0 for dim in tprate.dims if dim not in ['latitude', 'longitude']})

# Create the binary mask (1 for radar coverage, 0 for open ocean/no data)
mask_da = tprate.notnull().astype(int)
mask_array = mask_da.values
lons = mask_da['longitude'].values
lats = mask_da['latitude'].values

# DEBUG PLOT 1: THE RASTER MASK
plt.figure(figsize=(8, 6))
plt.imshow(mask_array, cmap='gray')
plt.title("DEBUG 1: Raster Mask Array\n(Properly oriented North-to-South)")
plt.show()

# ==========================================
# 2. VECTORIZE THE RADAR COVERAGE
# ==========================================
from rasterio.transform import from_bounds
transform = from_bounds(lons.min(), lats.min(), lons.max(), lats.max(), len(lons), len(lats))

# Extract the polygons from the 1s in the array
shapes = rasterio.features.shapes(mask_array.astype(np.int16), mask=(mask_array == 1), transform=transform)
polygons = [shape(geom) for geom, value in shapes]

if len(polygons) == 0:
    raise ValueError("ERROR: No polygons generated. The mask array might be empty.")

# Convert to a GeoDataFrame and merge all adjacent radar circles into one polygon
radar_gdf = gpd.GeoDataFrame(geometry=polygons, crs="EPSG:4326")
radar_gdf = radar_gdf.dissolve()

# ==========================================
# 3. SPATIAL CLIPPING (REMOVE FOREIGN LAND)
# ==========================================
# Load your high-resolution Italy shapefile
italy_land_gdf = gpd.read_file(BASE_DIR / 'data/Italia/italia.shp')

# Ensure CRS matches
if italy_land_gdf.crs != radar_gdf.crs:
    italy_land_gdf = italy_land_gdf.to_crs(radar_gdf.crs)

# Load a built-in global map to act as our "cookie cutter"
try:
    world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
except AttributeError:
    # Fallback for newer versions of GeoPandas
    import geodatasets
    world = gpd.read_file(geodatasets.get_path('naturalearth.land'))

# Filter to nearby continents and align CRS
europe_africa = world[world.continent.isin(['Europe', 'Africa'])] if 'continent' in world.columns else world
europe_africa = europe_africa.to_crs(radar_gdf.crs)

# Subtract ALL land from the radar coverage.
# This leaves ONLY the radar coverage that falls over the sea.
sea_only_radar = radar_gdf.overlay(europe_africa, how='difference')

# DEBUG PLOT 2: SEA-ONLY COVERAGE
fig, ax = plt.subplots(figsize=(8, 6))
sea_only_radar.plot(ax=ax, color='blue', alpha=0.5, edgecolor='blue')
italy_land_gdf.plot(ax=ax, color='none', edgecolor='red', linewidth=1)
plt.title("DEBUG 2: Erased Foreign Land\n(Blue = Sea Radar Coverage, Red = Italy)")
plt.show()

# ==========================================
# 4. MERGE AND EXPORT FINAL AOI
# ==========================================
# Combine the high-res Italy Land map with the Sea-Only radar map
combined_gdf = pd.concat([italy_land_gdf, sea_only_radar], ignore_index=True)

# Dissolve them together into one single, continuous boundary
final_aoi_gdf = combined_gdf.dissolve()

# DEBUG PLOT 3: FINAL PRODUCT
fig, ax = plt.subplots(figsize=(8, 6))
final_aoi_gdf.plot(ax=ax, color='green', edgecolor='black')
plt.title("DEBUG 3: Final Trimmed AOI\n(Ready for QGIS!)")
plt.show()

# Save out the finished shapefile
output_path = BASE_DIR / 'italy_land_and_sea_aoi.shp'
final_aoi_gdf.to_file(output_path)
print(f"Success! Expanded AOI saved to:\n{output_path}")

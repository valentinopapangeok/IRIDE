import xarray as xr
import geopandas as gpd
import matplotlib.pyplot as plt
import rasterio.features
from shapely.geometry import shape
import numpy as np
import warnings
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from pathlib import Path

warnings.filterwarnings('ignore')
BASE_DIR = Path(__file__).resolve().parent

# ==========================================
# 1. LOAD YOUR SAVED SHAPEFILES
# ==========================================
smooth_aoi = gpd.read_file(BASE_DIR / 'italy_smooth_buffer_aoi.shp')
italy_land = gpd.read_file(BASE_DIR / 'data/Italia/italia.shp')

# ==========================================
# 2. QUICKLY RECREATE EMPIRICAL RADAR FOOTPRINT
# ==========================================
grib_path = BASE_DIR / 'data/data-20250820T094735Z-4290906a-dea1-47d6-a78b-0d03d748ec21.grib'
ds = xr.open_dataset(grib_path, engine='cfgrib', backend_kwargs={'indexpath': ''})

# Orient, squeeze, and mask
tprate = ds['tprate'].sortby('latitude', ascending=False).sortby('longitude', ascending=True)
if len(tprate.dims) > 2:
    tprate = tprate.isel({dim: 0 for dim in tprate.dims if dim not in ['latitude', 'longitude']})

mask_da = tprate.notnull().astype(int)
mask_array = mask_da.values
lons = mask_da['longitude'].values
lats = mask_da['latitude'].values

# Vectorize
from rasterio.transform import from_bounds
transform = from_bounds(lons.min(), lats.min(), lons.max(), lats.max(), len(lons), len(lats))
shapes = rasterio.features.shapes(mask_array.astype(np.int16), mask=(mask_array == 1), transform=transform)
polygons = [shape(geom) for geom, value in shapes]

empirical_radar = gpd.GeoDataFrame(geometry=polygons, crs="EPSG:4326").dissolve()

# ==========================================
# 3. PLOT THE OVERLAP
# ==========================================
fig, ax = plt.subplots(figsize=(10, 10))

# A. The actual data footprint (Solid Blue, slightly transparent)
empirical_radar.plot(ax=ax, color='blue', alpha=0.4)

# B. Your new 120km boundary (Thick Green Outline)
smooth_aoi.plot(ax=ax, color='none', edgecolor='limegreen', linewidth=2.5)

# C. The Italian Coastline (Red Outline)
italy_land.to_crs("EPSG:4326").plot(ax=ax, color='none', edgecolor='red', linewidth=1)

# Custom Legend
legend_elements = [
    Patch(facecolor='blue', alpha=0.4, label='Actual Radar Footprint (Empirical)'),
    Line2D([0], [0], color='limegreen', lw=2.5, label='120km Theoretical Boundary'),
    Line2D([0], [0], color='red', lw=1, label='Italy Coastline')
]

ax.legend(handles=legend_elements, loc='upper right')
plt.title("Sanity Check: 120km Buffer vs. Actual Radar Coverage")
plt.show()

import geopandas as gpd
from shapely.geometry import shape, Point
import json
import matplotlib.pyplot as plt

# --- Paths ---
shapefile_path = "/Users/valentinopapandrea/Desktop/University/GeoK/tif_comparison/italia.shp"
json_geom_path = "/Users/valentinopapandrea/Desktop/University/GeoK/tif_comparison/AOI_S5-02-01,03,04,05,06,07,08,09,10.geojson"

# --- Load shapefile ---
gdf = gpd.read_file(shapefile_path)

# --- Load GeoJSON FeatureCollection ---
with open(json_geom_path) as f:
    geojson_data = json.load(f)

# --- Take the first geometry ---
first_geom = shape(geojson_data["features"][0]["geometry"])

# --- Ensure CRS alignment ---
if gdf.crs is None:
    gdf.set_crs(epsg=4326, inplace=True)

# --- Compute difference ---
gdf['diff'] = gdf.geometry.apply(lambda x: x.difference(first_geom))

# --- Convert difference polygons to points for plotting X's ---
diff_points = []
for geom in gdf['diff']:
    if geom.is_empty:
        continue
    if geom.geom_type == 'Polygon':
        x, y = geom.exterior.xy
        for xi, yi in zip(x, y):
            diff_points.append((xi, yi))
    elif geom.geom_type == 'MultiPolygon':
        for poly in geom.geoms:
            x, y = poly.exterior.xy
            for xi, yi in zip(x, y):
                diff_points.append((xi, yi))

# --- Plot ---
fig, ax = plt.subplots(figsize=(10, 10))
gdf.plot(ax=ax, color='lightblue', edgecolor='black', alpha=0.5)  # original shapefile
gpd.GeoSeries([first_geom]).plot(ax=ax, color='green', alpha=0.5)  # AOI

# Plot X's for differences
if diff_points:
    x_coords, y_coords = zip(*diff_points)
    ax.scatter(x_coords, y_coords, color='red', marker='x', s=20, label='Difference')


ax.legend()
plt.title("Differences between Shapefile and AOI (marked with X)")
plt.show()

from shapely.ops import nearest_points

def max_distance_diff(poly, ref_geom):
    if poly.is_empty:
        return 0
    # For MultiPolygon, take the max of all sub-polygons
    if poly.geom_type == 'MultiPolygon':
        return max(max_distance_diff(p, ref_geom) for p in poly.geoms)
    # Take the maximum distance from exterior points to AOI
    points = [Point(coord) for coord in poly.exterior.coords]
    return max(p.distance(ref_geom) for p in points)

gdf['max_diff'] = gdf['diff'].apply(lambda x: max_distance_diff(x, first_geom))
print("Maximum difference:", gdf['max_diff'].max())

def mean_distance_diff(poly, ref_geom):
    if poly.is_empty:
        return 0
    if poly.geom_type == 'MultiPolygon':
        return max(mean_distance_diff(p, ref_geom) for p in poly.geoms)
    points = [Point(coord) for coord in poly.exterior.coords]
    return sum(p.distance(ref_geom) for p in points) / len(points)

gdf['mean_diff'] = gdf['diff'].apply(lambda x: mean_distance_diff(x, first_geom))
print("Mean difference:", gdf['mean_diff'].mean())

num_diff_points = len(diff_points)

# Optionally, total points in shapefile
total_points = 0
for geom in gdf.geometry:
    if geom.geom_type == 'Polygon':
        total_points += len(geom.exterior.coords)
    elif geom.geom_type == 'MultiPolygon':
        for poly in geom.geoms:
            total_points += len(poly.exterior.coords)

print(f"Points with differences: {num_diff_points} / {total_points} ({num_diff_points/total_points*100:.2f}%)")

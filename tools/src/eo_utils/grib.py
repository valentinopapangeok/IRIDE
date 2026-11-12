import xarray as xr

# File path
file_path = "/Users/valentinopapandrea/Desktop/University/GeoK/tif_comparison/04/data-20250820T094735Z-4290906a-dea1-47d6-a78b-0d03d748ec21.grib"

def explore_grib(file_path):
    # Open the GRIB file with cfgrib
    ds = xr.open_dataset(file_path, engine="cfgrib", decode_timedelta=True)

    # Variables
    print("Variables:", list(ds.data_vars))

    # Dimensions
    print("\nDimensions:", dict(ds.sizes))

    # Coordinates
    print("\nCoordinates:", list(ds.coords))

    # Global attributes
    print("\nGlobal attributes:")
    for k, v in ds.attrs.items():
        print(f"  {k}: {v}")

    # Time coverage (if available)
    if "time" in ds:
        print("\nTime coverage:")
        print(str(ds.time.values[0]), "→", str(ds.time.values[-1]), f"({len(ds.time)} steps)")

# Run the function
explore_grib(file_path)




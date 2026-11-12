from eo_utils.file_readers import read_nc_gz_xarray, read_tif


# Example: read a HSAF NC.GZ file
nc_file = "/Users/valentinopapandrea/Desktop/University/GeoK/eo-utils/data/h40_20251214_1100_fdk.nc.gz"
ds = read_nc_gz_xarray(nc_file)
print(ds)
print(ds.attrs)

import gzip
import io
from typing import Tuple

from netCDF4 import Dataset
import rasterio


# -------------------------
# NC.GZ Files (HSAF)
# -------------------------
import gzip
import tempfile
import xarray as xr
from pathlib import Path

def read_nc_gz_xarray(file_path: str) -> xr.Dataset:
    """
    Read a .nc.gz file using xarray with netCDF4 backend.
    Decompresses the file to a temporary location first.
    """
    file_path = Path(file_path)
    with gzip.open(file_path, "rb") as f:
        with tempfile.NamedTemporaryFile(suffix=".nc") as tmp:
            tmp.write(f.read())
            tmp.flush()
            ds = xr.open_dataset(tmp.name, engine="netcdf4")
    return ds



def read_nc_gz_netCDF4(file_path: str) -> Dataset:
    """
    Read a .nc.gz file using netCDF4 and return a Dataset object.

    Args:
        file_path (str): Path to the .nc.gz file.

    Returns:
        netCDF4.Dataset: NetCDF dataset object.
    """
    with gzip.open(file_path, "rb") as f:
        nc_bytes = io.BytesIO(f.read())
        ds = Dataset('dummy', mode='r', memory=nc_bytes.read())
    return ds


# -------------------------
# GeoTIFF / Raster Files
# -------------------------
def read_tif(file_path: str) -> Tuple:
    """
    Read a GeoTIFF file using rasterio.

    Args:
        file_path (str): Path to the GeoTIFF file.

    Returns:
        Tuple: (data ndarray [bands, rows, cols], metadata dictionary)
    """
    with rasterio.open(file_path) as src:
        data = src.read()
        meta = src.meta
    return data, meta


# -------------------------
# Future extensions
# -------------------------
# Add more functions here for other file types:
# - HDF5
# - NetCDF (.nc)
# - JSON / STAC metadata
# - etc.

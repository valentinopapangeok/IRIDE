import os
import gzip
import zipfile
import logging
import re
from typing import Callable, Dict, List

import h5py
import numpy as np
from PIL import Image

try:
    import netCDF4
    HAS_NETCDF4 = True
except ImportError:
    HAS_NETCDF4 = False

try:
    import cfgrib
    HAS_CFGRIB = True
except ImportError:
    HAS_CFGRIB = False

logger = logging.getLogger(__name__)


class CorruptFileError(Exception):
    """Raised when a file is detected as corrupted."""


# -------------------------
# Validator implementations
# -------------------------

def _validate_gzip(path: str, deep: bool):
    with gzip.open(path, "rb") as f:
        if deep:
            for _ in iter(lambda: f.read(1024 * 1024), b""):
                pass
        else:
            f.read(1)


def _validate_zip(path: str, deep: bool):
    with zipfile.ZipFile(path, "r") as zf:
        if deep:
            bad = zf.testzip()
            if bad is not None:
                raise IOError(f"Corrupted ZIP member: {bad}")
        else:
            zf.infolist()  # header check only


def _validate_tiff(path: str, deep: bool):
    # Structural validation
    with Image.open(path) as img:
        img.verify()

    if deep:
        # Full decode validation
        with Image.open(path) as img:
            img.load()


def _validate_hdf5(path: str, deep: bool):
    if not h5py.is_hdf5(path):
        raise IOError("Not a valid HDF5 file")

    with h5py.File(path, "r") as f:

        def _visit(_, obj):
            if isinstance(obj, h5py.Dataset):
                if deep:
                    # memory-safe: read a single element
                    obj[tuple(0 for _ in obj.shape)]
                else:
                    obj.shape  # metadata only

        f.visititems(_visit)


def _validate_netcdf(path: str, deep: bool):
    """Validate NetCDF (.nc) files."""
    if not HAS_NETCDF4:
        logger.warning("netCDF4 not installed, skipping NetCDF validation for: %s", path)
        return
    
    try:
        with netCDF4.Dataset(path, "r") as ds:
            if deep:
                # Read metadata from all variables
                for var_name in ds.variables:
                    var = ds.variables[var_name]
                    # Read first element if possible
                    if var.size > 0:
                        var[0] if var.ndim == 1 else var[tuple(0 for _ in range(var.ndim))]
            else:
                # Just access variables (metadata check)
                _ = ds.variables
    except Exception as err:
        raise IOError(f"Invalid or corrupted NetCDF file: {err}") from err


def _validate_grib(path: str, deep: bool):
    """Validate GRIB (.grib, .grb) files."""
    if not HAS_CFGRIB:
        logger.warning("cfgrib not installed, skipping GRIB validation for: %s", path)
        return
    
    try:
        import cfgrib
        with cfgrib.open_datasets(path) as datasets:
            if deep:
                # Attempt to read data from datasets
                for ds in datasets:
                    for var in ds.variables:
                        if ds[var].size > 0:
                            _ = ds[var].values
            else:
                # Just open and verify structure
                pass
    except Exception as err:
        raise IOError(f"Invalid or corrupted GRIB file: {err}") from err


def _validate_nrt(path: str, deep: bool):
    """Validate NRT (EUMETSAT) format files.
    
    NRT files are typically binary satellite data.
    Perform basic file structure checks.
    """
    # Basic checks: file exists and is readable
    try:
        with open(path, "rb") as f:
            # Read first 1KB to check file is readable
            data = f.read(1024)
            if not data:
                raise IOError("NRT file is empty")
            
            if deep:
                # Read entire file to validate integrity
                f.seek(0)
                while f.read(1024 * 1024):
                    pass
    except Exception as err:
        raise IOError(f"Invalid or corrupted NRT file: {err}") from err


# -------------------------
# Validator registry
# -------------------------

VALIDATORS: Dict[str, Callable[[str, bool], None]] = {
    ".gz": _validate_gzip,
    ".zip": _validate_zip,
    ".tif": _validate_tiff,
    ".tiff": _validate_tiff,
    ".hdf": _validate_hdf5,
    ".he5": _validate_hdf5,
    ".h5": _validate_hdf5,
    ".nc": _validate_netcdf,
    ".grib": _validate_grib,
    ".grb": _validate_grib,
    ".nrt": _validate_nrt,
}

MANDATORY_FILES : Dict[str, List[str]] = {
    "01": [
        r"S3B_SL_2_LST____\d{8}T\d{6}_\d{8}T\d{6}_*", #"S3B_SL_2_LST____20230101T000000_20230101T235959_0001.NRT", 
        r"SRTM.tif", 
        r"IRIDE_S_S5-02-\d{2}_\d{8}_*.tif"
    ],
    "02": [
        r"S3B_SL_2_WST____\d{8}T\d{6}_\d{8}T\d{6}_*.zip", #"S3B_SL_2_WST____20220611T090704_20220611T091004_20220611T111543_0179_067_050_2340_MAR_O_NR_003.zip", 
        r"IRIDE_S_S5-02-\d{2}_\d{8}_*.tif"
    ], 
    "03": [
        r"DNIin\d{14}42310001I1MA.nc"
    ],
    "04": [
        r"data-\d{8}T\d{6}Z-*.grib", 
        r"h40_\d{8}_\d{4}_*.gz"
    ], 
    "05": [
        r"S3B_OL_2_LFR____\d{8}T\d{6}_\d{8}T\d{6}_*.zip",
        r"VNP10A1F*.h5"
    ], 
    "06": [
        r"W_XX-EUMETSAT-*-NC4E_C_EUMT_\d{14}_L2PF_OPE_\d{14}_\d{14}_*.nc"
    ],
    "07": [
        r"s5p-l3grd-ch4-*-\d{8}-\d{8}.nc",
    ],
    "08": [
        r"oco2_LtCO2_*\d{12}s.nc4",
        r"oco3_LtCO2_*\d{12}s.nc4"
    ],
    "09": [
        r"MCD19A2.A*.hdf"
    ]
}

def validate_if_mandatory(
    local_path: str,
    product_id: str, 
    deep: bool = True,
    max_size_mb: int | None = None, 
):
    """
    Validate a file if it matches mandatory file patterns for a given product.
    
    Parameters
    ----------
    local_path : str
        Path to the file to validate.
    product_id : str
        Product ID (e.g., "01", "02", etc.) to look up in MANDATORY_FILES.
    deep : bool
        If True, fully decode/read file contents.
        If False, perform fast structural checks only.
    max_size_mb : int | None
        Optional size limit to avoid validating extremely large files.
        
    Raises
    ------
    ValueError
        If product_id is not found in MANDATORY_FILES.
    RuntimeError
        If the file does not match any mandatory file pattern for the product.
    CorruptFileError
        If the file is corrupted (via validate_file_integrity).
    """
    # Get product's mandatory file patterns
    if product_id not in MANDATORY_FILES:
        raise ValueError(f"Product ID '{product_id}' not found in MANDATORY_FILES")
    
    mandatory_patterns = MANDATORY_FILES[product_id]
    filename = os.path.basename(local_path)
    
    # Check if filename matches any mandatory pattern
    matched = False
    for pattern in mandatory_patterns:
        try:
            # Treat pattern as regex
            if re.match(pattern, filename):
                matched = True
                logger.info(f"File '{filename}' matches mandatory pattern '{pattern}' for product {product_id}")
                break
        except re.error as e:
            logger.error(f"Invalid regex pattern '{pattern}': {e}")
            continue
    
    if not matched:
        raise RuntimeError(
            f"File '{filename}' does not match any mandatory pattern for product {product_id}. "
            f"Expected patterns: {mandatory_patterns}"
        )
    
    # File matches a mandatory pattern, validate its integrity
    validate_file_integrity(local_path, deep=deep, max_size_mb=max_size_mb)

def validate_file_integrity(
    local_path: str,
    *,
    deep: bool = True,
    max_size_mb: int | None = None,
):
    """
    Validate file integrity based on extension.

    Parameters
    ----------
    local_path : str
        Path to file.
    deep : bool
        If True, fully decode/read file contents.
        If False, perform fast structural checks only.
    max_size_mb : int | None
        Optional size limit to avoid validating extremely large files.

    Raises
    ------
    CorruptFileError
        If file corruption is detected.
    """

    ext = os.path.splitext(local_path)[1].lower()

    if max_size_mb is not None:
        size_mb = os.path.getsize(local_path) / (1024 * 1024)
        if size_mb > max_size_mb:
            raise ValueError(
                f"File too large for validation ({size_mb:.1f} MB > {max_size_mb} MB)"
            )

    validator = VALIDATORS.get(ext)

    if not validator:
        logger.info("No integrity check implemented for: %s", local_path)
        return

    try:
        validator(local_path, deep)
        logger.info("Validated integrity (%s): %s", "deep" if deep else "fast", local_path)

    except Exception as err:
        logger.warning(
            "Corrupted file detected: %s | %s",
            local_path,
            err,
            exc_info=True,
        )

        try:
            os.remove(local_path)
            logger.info("Removed corrupted file: %s", local_path)
        except OSError:
            logger.error("Failed to remove corrupted file: %s", local_path)

        raise CorruptFileError(local_path) from err

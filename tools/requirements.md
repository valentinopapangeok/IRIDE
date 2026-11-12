# Environment & Dependencies

## Environment Purpose

This environment supports cloud-native geospatial and Earth Observation (EO) workflows.  
It is designed for pipelines that retrieve, process, and analyze satellite datasets across multiple scientific formats.

Primary capabilities include:

- Raster and multidimensional EO data processing (GeoTIFF, COG, NetCDF, GRIB, HDF5)
- Vector data and geometry operations
- Cloud and remote catalog access (S3, STAC, APIs, FTP)
- Scientific computing and numerical analysis
- Machine learning and computer vision tasks
- Visualization and QA workflows
- Workflow orchestration and pipeline execution

---

## Dependency Categories

### Geospatial Raster & Multidimensional Data Processing

- **rasterio** — raster data reading / writing (GeoTIFF, Cloud Optimized GeoTIFF)
- **xarray** — multidimensional arrays / labeled scientific datasets
- **netCDF4** — NetCDF file backend for EO datasets
- **h5py** — HDF5 data access (common in satellite products)
- **cfgrib** — GRIB file reading via xarray (meteorological / ECMWF data)
- **rio-cogeo** — Cloud Optimized GeoTIFF (COG) creation / conversion
- **numpy** — numerical array computations (core dependency)
- **scipy** — scientific computing / numerical routines

---

### Vector Data & Geometry Handling

- **geopandas** — vector datasets / spatial dataframes
- **shapely** — geometry objects / spatial operations
- **pyproj** — coordinate reference system (CRS) transformations

---

### Cloud, Remote Data & Catalog Access

- **boto3** — AWS SDK / S3 interactions
- **botocore** — underlying AWS library required by boto3
- **pystac** — STAC catalog access / EO metadata handling
- **requests** — HTTP requests / API communication
- **urllib3** — low-level HTTP client used by requests
- **certifi** — SSL certificate validation
- **charset-normalizer** — requests dependency
- **idna** — requests dependency
- **boto3-stubs** — optional typing support for boto3
- **cdsapi** — Copernicus Climate Data Store API client
- **ftplib** — FTP protocol access

---

### Data Analysis & Structured Data

- **pandas** — tabular data / dataframe operations / metadata handling
- **python-dateutil** — date parsing / time utilities
- **pytz** — time zone support
- **datetime** — date and time utilities
- **json** — JSON parsing / serialization
- **xml** — XML parsing / structured data handling

---

### Machine Learning & Computer Vision

- **sklearn** — machine learning utilities / models
- **cv2** — OpenCV / computer vision
- **PIL** — image processing via Pillow

---

### Visualization & Plotting

- **matplotlib** — plotting / visualization / QA graphics
- **cycler** — matplotlib dependency
- **kiwisolver** — matplotlib dependency
- **fonttools** — font rendering backend

---

### Compression, Filesystem & I/O Utilities

- **gzip** — gzip compression / decompression
- **zipfile** — ZIP archive handling
- **shutil** — high-level file operations
- **tempfile** — temporary file handling
- **pathlib** — filesystem path management
- **os** — operating system utilities
- **io** — stream / buffer handling
- **hashlib** — hashing / checksums / integrity validation

---

### Workflow Orchestration & Pipelines

- **prefect** — workflow orchestration / DAG execution
- **prefect_common** — shared pipeline utilities (project-specific)
- **steps** — pipeline modules / processing stages (project-specific)

---

### Project-Specific / Custom Modules

- **utils** — project helper functions / shared utilities
- **gportal** — internal data portal interactions
- **modis_tools** — MODIS utilities
- **xarrayast** — internal xarray-related tooling

---

### Compatibility & Dependency Helpers

- **six** — Python compatibility layer
- **packaging** — version parsing / dependency utilities
- **pkg_resources** — package metadata access
- **typing** — type hint utilities
- **warnings** — runtime warning control
- **logging** — runtime diagnostics
- **time** — timing / benchmarking utilities
- **re** — regular expressions
- **ast** — abstract syntax tree utilities

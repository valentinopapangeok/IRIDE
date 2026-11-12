# VPP - Vulnerability Patch Protocol

This protocol documents the Dockerfile changes validated on `svc_s5-02-11` and intended to be applied consistently to the remaining S5-02 product containers.

## Goal

Reduce GitLab container-scanning findings caused by build-only Debian packages being left in the final runtime image.

The successful `svc_s5-02-11` remediation removed active critical findings and reduced high findings by purging packages that are needed only while installing Python/GDAL dependencies.

## Baseline Change

Pin the Docker base image platform to the GitLab runtime architecture:

```dockerfile
FROM --platform=linux/amd64 prefecthq/prefect:3.6.22-python3.11
```

Keep Python `3.11` for now. Do not switch to `python3.12` unless the product dependencies are reviewed first, because several products pin older scientific packages that may not support Python 3.12 cleanly.

## Final Runtime Cleanup

After all Python dependencies, Poetry dependencies, GDAL bindings, and product requirements are installed, add a final purge block.

Use an explicit purge list and do not use `apt-get --auto-remove` for products with native geospatial/scientific Python packages. Packages such as `rasterio`, `rioxarray`, `geopandas`, `shapely`, `netcdf4`, `h5py`, `pyhdf`, and `eccodes` can load shared libraries indirectly at runtime. `apt` autoremove can delete those transitive runtime libraries even when the Python package itself remains installed.

```dockerfile
RUN apt-get purge -y \
    curl \
    git \
    gettext \
    build-essential \
    cmake \
    gdal-bin \
    libgdal-dev \
    libnetcdf-dev \
    libhdf5-serial-dev \
    linux-libc-dev \
    binutils \
    patch \
    m4 \
    perl \
    perl-modules-5.40 \
    python3-gdal \
    python3.13 \
    python3.13-minimal \
    libpython3.13-stdlib \
    libpython3.13-minimal \
    && rm -rf /var/lib/apt/lists/*
```

Apply this at the end of the Dockerfile, immediately before the final `WORKDIR /app` or equivalent final runtime setup.

## Why This Works

Most high/critical findings were not caused by application code. They came from Debian packages installed in the final image:

- `python3.13`
- `python3.13-minimal`
- `libpython3.13-*`
- `perl`
- `perl-modules-5.40`
- `linux-libc-dev`
- `binutils`
- `git`
- `patch`
- `m4`
- `curl`
- `libgdal-dev`
- `libnetcdf-dev`
- `libhdf5-serial-dev`

These are build or tooling packages. They are useful while installing Python packages, compiling wheels, or resolving GDAL bindings, but they should not remain in the runtime image.

Do not remove transitive shared-library dependencies automatically. Product `svc_s5-02-03` failed at runtime after `--auto-remove` removed `libexpat1`, causing `rasterio` import failure with `libexpat.so.1: cannot open shared object file`.

## Important Checks Before Applying

Before purging `gdal-bin`, confirm the product does not call GDAL command-line tools directly:

```bash
rg -n "gdalinfo|gdal_translate|gdalwarp|ogr2ogr|ogrinfo|gdaldem|subprocess|os\\.system|Popen" src
```

If the code only imports Python GDAL APIs such as:

```python
from osgeo import gdal
```

then removing `gdal-bin` is expected to be safe.

If the product calls GDAL CLI tools, either keep `gdal-bin` or replace CLI calls with Python `osgeo.gdal` APIs before applying the full purge.

## Secret Remediation

If GitLab reports secret-detection findings:

1. Remove committed secret values from tracked files.
2. Keep config keys if the application expects them.
3. Use environment variables, GitLab CI/CD variables, Kubernetes secrets, or Vault for runtime values.
4. Rotate/revoke the exposed credentials. Removing them from git does not make already-exposed credentials safe.

For `svc_s5-02-11`, `private_config.json` kept the same keys but blanked sensitive values. The existing config loader already prefers environment variables over JSON values.

## Application Order Per Product

For each product:

1. Create a fresh feature branch from current `main`.
2. Apply only the platform pin and final purge block.
3. Check product-specific GDAL CLI usage.
4. Run static checks:

```bash
git diff --check
```

5. Build the image if Docker is available.
6. Push the feature branch and let GitLab run:
   - container scanning
   - dependency scanning
   - secret detection
   - SAST
7. Merge only if the build passes and vulnerability counts decrease or remain acceptable.

## Expected Scan Impact

The largest expected reductions are:

- Critical `python3.13` / Expat findings
- Critical/high `perl` and `perl-archive-tar` findings
- High `linux-libc-dev` findings
- High `binutils`, `git`, `patch`, `m4`, and `curl` findings
- High `libhdf5-*`, `libnetcdf-dev`, and `libgdal-dev` findings

## Not Covered By This Protocol

This protocol does not fix Python dependency-scanning findings such as `aiohttp`. Those require dependency lock updates, for example:

```bash
poetry update aiohttp
```

Run that only after checking package constraints and build compatibility for each product.

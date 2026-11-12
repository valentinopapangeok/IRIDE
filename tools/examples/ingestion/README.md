# Provider ingestion examples

Moved intact from `workflows/ingestion_examples/`, which remains a compatibility
symlink. This is sample ingestion code, separate from the operational audit in
`workflows/input_availability/`.

- `data_ingestion.py`: organize downloaded products.
- `download_stac.py`: STAC retrieval example.
- `era5_era5land_download.py`, `gcomc_data_download.py`, `modis_data_download.py`,
  `sentinel3_data_download.py`: provider-specific download examples.

Check each script's inputs, dependencies and provider configuration before use.
No provider downloads were run as part of this reorganization.

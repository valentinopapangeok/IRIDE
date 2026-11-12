# EO Utils

Earth Observation helpers, operational tools and scientific workflows.
Choose a purpose below, then read that workflow's README. The validation cache
is required and stays untouched.

| Purpose | Canonical location |
| --- | --- |
| Reusable Python functions | `src/eo_utils/` |
| General CLI entry points | `scripts/` |
| Provider audit and event investigations | `workflows/operations/input_availability/` |
| Bucket CLI (core in `eo_utils.buckets`) | `workflows/operations/buckets/iride_buckets.py` |
| DCO retrieval and offline delivery | `workflows/operations/local_dco_download/`, `local_delivery/` |
| Baseline/product/DEV-UAT comparisons | [workflows/regression/](workflows/regression/README.md) |
| AOI development | `workflows/geospatial/aoi_expansion_04/` |
| Raster, metadata, resolution and vulnerability analyses | [workflows/analysis/](workflows/analysis/README.md) |
| Provider ingestion examples | [examples/ingestion/](examples/ingestion/README.md) |
| Shared static references | `reference/` |

The directory names following a shared prefix in this table are siblings.
Former paths remain compatibility symlinks; use canonical paths for new searches,
references and IDE configurations. See [path migrations](docs/path_migrations.json)
and [organization](docs/ORGANIZATION.md). Existing data moved with its workflow,
retaining old access paths; no scientific datasets were deleted.

## Installation and use

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
python workflows/operations/buckets/iride_buckets.py --help
```

```python
from eo_utils.file_readers import read_nc_gz_xarray
from eo_utils.buckets import remote
```

The public scheduled dashboard remains in the sibling
`iride-input-availability-public` repo. It differs from the local audit;
provider-code consolidation is a separate implementation change.

## Maintenance

- Library functions belong in `src/eo_utils/`; thin CLI wrappers in `scripts/`
  or their operational workflow; case-specific work stays with its workflow.
- Keep each investigation's scripts, configuration template, input manifest,
  outputs and conclusions together. Age does not establish that it is disposable.
- Keep credentials/local configuration and downloads out of new commits.
  Existing unrelated local changes are preserved; inspect the full status before staging.
- `.ignore` limits discovery, `.gitignore` controls new tracked files, and
  `.gitattributes` retains LFS handling for regression TIFFs at their new paths.
- `scripts/update_project.py` preserves this guide while refreshing the bounded
  directory map; it also appends inferred requirements. Run only for dependency
  maintenance and review its diff; it is not needed for routine documentation edits.
- Offline checks: `.venv/bin/python -m unittest discover -s tests -v`.
- Update CHANGELOG.md for changes and keep compatibility paths until callers migrate.

<!-- BEGIN GENERATED DIRECTORY MAP -->
## Directory map

Directories only; data and hidden folders omitted.

```text
docs/
examples/
  ingestion/
reference/
  aoi_specs/
  new_ingestion_catalogs/
scripts/
src/
  eo_utils/
tests/
workflows/
  analysis/
  geospatial/
  operations/
  regression/
```
<!-- END GENERATED DIRECTORY MAP -->

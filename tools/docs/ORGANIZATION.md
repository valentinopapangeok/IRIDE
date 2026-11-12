# Utils organization, 2026-11-02

## Current layout and lifecycle

| Location | Purpose | Lifecycle |
| --- | --- | --- |
| `src/eo_utils/` | Reusable library, including bucket helpers | Maintained utilities |
| `scripts/` | General entry points | Maintained entry points |
| `workflows/operations/` | Audit, buckets, DCO retrieval, offline delivery | Operational tools and embedded event cases |
| `workflows/regression/` | Baseline/product comparisons | Retained scientific investigations |
| `workflows/geospatial/` | AOI development | Retained scientific development |
| `workflows/analysis/` | Raster, metadata, resolution, vulnerability studies | Standalone reference cases |
| `examples/ingestion/` | Provider ingestion samples | Reference examples |
| `reference/` | Shared stable material | Retained reference data |

All workflows were moved intact with data and local files. Every former path is a
relative compatibility symlink; see [path_migrations.json](path_migrations.json).
The regression scripts' cross-group config references were corrected. The bucket
CLI imports reusable functions from `src/eo_utils/buckets.py`; commands retain
existing behavior. No provider operations were run.

## Compatibility and verification

Keep destinations and compatibility links in the same future commit. Files are
not staged or committed. Git may display removals at old paths and additions at
new paths until staged together; no scientific files were discarded.

The first analysis/examples move was verified with SHA-256 for every original file.
The larger operations/regression/geospatial move was verified using file identity,
size, timestamp, mode and symlink target for every original entry, plus SHA-256 for
files up to 1 MiB. Deliberate source edits followed verification. Workspace manifests
are in `maintenance/2026-11-02/` (outside this Git repo).

Existing configs and external callers can use old paths. Canonical paths should be
used for new work. Migrated local credentials/downloads remain ignored; the old
tracked local config is not copied into the new tracked source set. Canonical TIFF
LFS attributes are preserved. Symlinks need filesystem support when cloning elsewhere.

## Data and consolidation

The validation cache is explicitly required by the user: keep it in place without
relocation or pruning. Other scientific datasets/environments remain retained.
For new work, prefer configurable workflow-specific runtime locations and small
input/result manifests. Do not relocate existing data without migrating consumers.

The local and public audits overlap but differ in four of five shared Python files.
Keep separate entry points. Consolidating provider code needs a behavior comparison
and package extraction; it was not bundled into this structural reorganization.

## Remaining review candidates

- `.venv_py314_unused/`: untracked, about 10 MiB logical; no searched source reference.
  External/IDE interpreter usage remains unverified, so retained.
- `workflows/analysis/bilateral_filter/final_textured_output 2.tif`: exact duplicate
  of the unsuffixed TIFF; sidecar/GIS references remain unverified, so retained.
- `workflows/geospatial/aoi_expansion_04/Old/`: only some components are identical;
  keep complete GIS datasets together.
- Regression runtime downloads and event evidence are retained; recoverability
  and scientific retention have not been established for deletion.
- `.git` stores LFS/history and is not a folder of disposable loose artifacts.

Pre-existing local source/config changes and untracked investigations were preserved.

Canonical absolute command examples in workflow READMEs were updated. Other repos
and IDE settings may still use the valid compatibility paths. Full scientific
workflow execution was not part of verification; only offline/path/CLI checks ran.

## 2026-11-02 — Purpose-based workflow layout
- Group operational, regression and geospatial workflows; preserve all former paths as compatibility symlinks.
- Retain datasets, runtime environments, local config and existing unrelated changes.
- Fix three cross-group config-path references and preserve canonical Git ignores/LFS attributes.
- Extract reusable bucket functions into eo_utils.buckets, retaining a thin compatible CLI.
- Add lifecycle indexes, path migration mapping and offline bucket dispatch tests.

## 2026-11-02 — Group standalone analyses and examples
- Move four standalone cases under workflows/analysis and ingestion examples under examples/ingestion.
- Preserve former paths as relative compatibility symlinks, including IDE working directories.
- Verify every moved original file by SHA-256, permissions and internal symlink target.
- Add workflow/example indexes and local maintenance guidance; retain all datasets and environments.
- Record the user requirement to retain the validation cache without relocation or pruning.

## 2026-11-02 — Workspace context cleanup
- Replace the recursive README file dump with a task map and retention guidance.
- Preserve handwritten README content when regenerating the bounded directory map.
- Add search exclusions for local datasets and historical runtime artifacts.
- Document archive candidates and cross-repo dependencies; preserve existing data and local work.

## [0.1.20] - 2026-05-21
- Removed the duplicate input-availability GitHub Actions Pages workflow from the Utils repo.
- Made the OCO-2/OCO-3 input audit month-scoped so lag calculations follow the collection cadence.
- Updated the OCO-2 input audit to use the current `OCO2_L2_Lite_FP` version (`11.2r`) instead of the stale `11.1r` pin.
- Added total runtime reporting to the input availability audit.
- Changed the input availability audit output to separate `found` and `downloaded` columns and record per-adapter runtime.
- Expanded the input availability audit so each supported input now tries to download a sample file, and added the missing ERA5 single-levels input.
- Added a local DCO download utility that mirrors DCO PSG/PS temporal filtering and downloads matching assets for integrity checks.
- Added a local offline delivery workflow for product 04 STAC item packaging.
- Refactored local product 04 delivery to mirror real `delivery` and `stac_creation_upload` steps with local packaging output.
- Aligned local 04 delivery startup with real flow assumptions by requiring delivery credentials and inputs at flow start.
- Switched local 04 delivery runtime to use local config variables/paths only (no environment-variable dependency).
- Moved Product 04 no-regression probes into `workflows/no_regression_04` and rewired internal paths to sibling workflow config.
- Merged the previous temporary utility folders into the repository.
- Cleaned tracked validation data from `data/` while keeping `04_expansion/` intact.
- Fixed the input availability environment setup and documentation.
- Added dated `input_availability/audit_results/` outputs for per-run statistics.
- Updated project metadata with `scripts/update_project.py` and hardened the project inspector.
- Reorganized the repository into `src/eo_utils/`, `workflows/`, and `reference/`.

## [0.1.19] - 2026-03-31
- Updated 04 expansion project file and removed obsolete plot output

## [0.1.18] - 2026-03-31
- Updated vulnerability report parsing with per-project rollout cutoffs and grouped detailed output
- Refreshed vulnerability reports and generated summaries for the latest export set
- Updated README.md with the current repository tree
- Fixed project inspector to ignore standard-library and local modules when updating requirements

## [0.1.17] - 2026-03-13
- Added new aoi expansion for 04

## [0.1.16] - 2026-03-12
- Added aoi expansion for 04

## [0.1.15] - 2026-03-10
- Updated vulnerability report analysis directory

## [0.1.14] - 2026-02-27
- Added vulnerability report analysis directory

## [0.1.13] - 2026-02-17
-Rename requirements.txt to requirements.md and updated the information

## [0.1.12] - 2026-02-03
- Added bilateral filter directory for 09 trials

## [0.1.11] - 2026-01-15
- Minor refactoring

## [0.1.10] - 2026-01-15
- Updated README.md

## [0.1.9] - 2026-01-15
- Added validation of 08

## [0.1.8] - 2026-01-14
- Minor refactoring

## [0.1.7] - 2026-01-14
- Minor refactoring

## [0.1.6] - 2026-01-14
- Added scripts for validation of 07 and 08

## [0.1.5] - 2026-01-14
- Added Validation 07-08 and data 

## [0.1.4] - 2025-12-16
- Removed TODO in CHANGELOG.md

## [0.1.3] - 2025-12-16
- New TODO in CHANGELOG.md
- updated project_inspector.py

## [0.1.3] - 2025-12-16
- New update_project.py script
- New readme.md
- New requirements.txt

## [0.1.2] - 2025-12-16
- New nc reader files

## [0.1.1] - 2025-12-16
- New folder structure for scripts

## [0.1.0] - 2025-12-16
- Initial release of EO utilities repository.

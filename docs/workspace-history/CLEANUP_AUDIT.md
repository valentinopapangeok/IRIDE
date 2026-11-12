# Workspace cleanup audit — 2 November 2026

## Completed purpose-based reorganization and artifact cleanup

Implemented the grouped Utils layout: `src/eo_utils/`, `scripts/`,
`workflows/{operations,regression,analysis,geospatial}/`, `examples/ingestion/`,
`reference/`, `tests/` and `docs/`. Fourteen former entry paths remain relative
compatibility symlinks. Three cross-group config references were corrected, and
bucket command functions were extracted into `eo_utils.buckets` with a thin CLI.
All original data and pre-existing unrelated changes were retained.

Verification: ten offline tests passed; all fourteen compatibility paths, regression
configs/baselines, canonical Git ignores, TIFF LFS attributes, CLI dispatch and
workflow Python syntax were checked. Every moved entry was verified immediately
after rename. Full provider/scientific processing was not run.

The complete workspace inventory covers 153,252 regular files before cleanup,
including hidden directories, sixteen repositories and one additional Git worktree.
Inventories use logical file bytes and do not follow directory symlinks:
[before](maintenance/2026-11-02/full_inventory_before_cleanup.json),
[after](maintenance/2026-11-02/full_inventory_after_cleanup.json).

### Deleted and preserved

- Deleted 62 verified duplicate/generated files totaling
  **81.52 MiB logical contents**: eight chart-conversion decks
  identical to retained deliverables, generated slide previews and inspection dumps.
  This is gross deleted contents, not a claim about net filesystem allocation.
- Removed ten `.chart-data-*` folders and three `.codex-finalizer-*` folders after
  preserving their useful metadata. Two unmatched candidate decks were retained
  under `maintenance/2026-11-02/presentation-scratch/`.
- Moved all eighteen finalization reports into `qa/` beside their SHA-256-matched
  deliverables. Retained all deliverable decks, draft decks, build scripts and assets.
- Retained `.codex_work/aod-source-validation`: a registered clean worktree on
  branch `feature`, still referenced by a validation trial report. It is source
  context, not a disposable cache. `.codex_work` therefore intentionally remains.
- Retained presentation build sources/drafts in `.codex_work`, all environments,
  Git/LFS stores, evidence and scientific data. The two validation directories
  have exactly the same file counts and logical byte totals before/after cleanup.
  The validation cache remains in place as explicitly required.

Every deletion and relocated file is recorded with path, size, SHA-256 and reason
in [cleanup_receipt.json](maintenance/2026-11-02/cleanup_receipt.json). The receipt
was checked against the retained duplicate files and relocated QA/candidate hashes.

The largest remaining hidden directories are product Git histories and Python
runtimes; their names do not make them disposable. The previously identified
unused-named environment and small duplicate TIFF remain review candidates because
external/IDE/GIS usage has not been established. No further safe large deletion was
proven. Future presentation runs may recreate their generated scratch directories.

See [Utils layout](Utils/README.md), [migration paths](Utils/docs/path_migrations.json)
and [organization notes](Utils/docs/ORGANIZATION.md). Changes remain uncommitted;
new directories and compatibility symlinks must be staged together in a future commit.

---

The following sections retain the earlier audit findings and decisions for history.

The workspace layout is service repositories plus shared tooling, operational
reporting and large scientific datasets. Keep these repository boundaries. The
highest-value context fix is scoped discovery and consistent current guidance;
the highest-value disk cleanup would require data-retention decisions, not
removing old Python files.

## Follow-up decision and Utils reorganization

The user confirmed the validation cache is required. Retain it in place; it is
excluded from deletion, relocation and pruning. Utils standalone analyses were
subsequently grouped under `workflows/analysis/`, and ingestion examples under
`examples/ingestion/`, with compatibility symlinks at every original path. All
original contents were verified by SHA-256. See [Utils organization](Utils/docs/ORGANIZATION.md)
and [move manifest](maintenance/2026-11-02/utils_reorganization.json). The initial
audit findings below describe the state before those physical moves.

## Initial audit changes completed

- Operational README now identifies one active workbook: the copy directly in
  `operational_performance/`. Removed the conflicting `../outputs/...` pointer
  from current guidance. Prior wording remains in an excluded history document.
- Current population rules use actual headers instead of conflicting L/M and Q/U
  positions. Preserved historical corrections, matching rules and field meanings.
- Reduced the reporting checklist from 72 to 35 lines. Read supporting rules once
  per task, query specific IDs, and retain short checkpoints after material writes.
- Operational search excludes categorised copies, templates, backups, historical
  guidance and generated inspection dumps. Searchable files fell from 564 to 356
  at verification (new docs included). Originals and structured logs remain visible.
- Replaced the 321-line Utils README with an 86-line task map and bounded directory
  map. Added Utils organization/retention guidance and targeted search exclusions.
  Normal Utils discovery fell from roughly 776 files to 209 at verification.
- Updated the Utils README generator to preserve handwritten content, limit depth
  and entry count, list directories only, and avoid hidden/data/symlink traversal.
  Five offline regression tests pass; malformed markers cannot overwrite guidance.
- No pre-existing data, code, environment, evidence, workbook or Git object was
  deleted or moved. Existing local changes were preserved. Requirements were not
  regenerated from the installed environment. No network services were contacted.

## Operational context findings

The problem is inconsistent and repeatedly reread guidance, not a large source
codebase. Prior README wording both required every screenshot copy and instructed
skipping duplicates, pointed to two current workbooks, repeated matching rules,
and mixed initial-batch assumptions with current policy. POPULATION_RULES used
an older issue-column layout while REPORTING_CHECKLIST used a newer one.
These contradictions are removed from current entry points, with source wording
preserved under `operational_performance/docs/history/`.

The existing ops chat showed repeated instruction reads between compactions.
File cleanup cannot remove already accumulated chat history. Use the current
entry point and a short task checkpoint when continuing; this audit does not
claim the chat compaction loop has been resolved.

The evidence archive has 200 hash-identical original/categorised groups, about
64.9 MiB of redundant logical contents. Both paths are required by current
reporting instructions. Keep them; do not delete a second copy merely because it
has the same hash. Four further groups are repeated source KPI CSV exports,
only about 1.5 KiB redundant; their provenance outweighs storage savings.

## Workspace organization and measured sizes

The following are logical file bytes (GiB), including hidden environments and Git
objects, without following symlink directories. Actual allocated disk sizes can
differ. Counts are a point-in-time inventory, not a usage/last-access signal.

| Directory | Logical GiB | Files |
| --- | ---: | ---: |
| `validation_app/` | 54.035 | 51,148 |
| `iride-input-availability-public/` | 37.796 | 1,440 |
| `bucketBackup/` | 8.331 | 591 |
| `Utils/` | 5.796 | 36,105 |
| `svc_s5-02-08/` | 4.818 | 5,238 |
| `svc_s5-02-07/` | 4.675 | 345 |
| `svc_s5-02-09/` | 3.019 | 426 |
| `.venv/` | 0.474 | 21,383 |
| `svc_s5-02-02/` | 0.435 | 7,861 |
| `svc_s5-02-05/` | 0.355 | 14,354 |
| `operational-validation-IRIDE/` | 0.330 | 9,030 |
| `svc_s5-02-10/` | 0.273 | 788 |
| `operational_performance/` | 0.151 | 564 |
| `deliverables/` | 0.119 | 23 |
| `.codex_work/` | 0.075 | 337 |
| `svc_s5-02-01/` | 0.067 | 778 |
| `svc_s5-02-06/` | 0.056 | 364 |
| `svc_s5-02-04/` | 0.054 | 469 |
| `svc_s5-02-11/` | 0.036 | 333 |
| `svc_s5-02-03/` | 0.034 | 334 |
| `outputs/` | 0.020 | 131 |
| `svc_S5-02/` | 0.018 | 988 |
| `prefect-common/` | 0.001 | 136 |
| `comparison_baselines/` | 0.001 | 5 |

The raw inventory includes top-level child totals and up to twelve files larger
than 50 MiB per directory: [inventory](maintenance/2026-11-02/inventory.json).
It does not store file contents or credentials.

## Repository boundaries and local work

Sixteen independent Git repositories were inspected. The workspace root,
operational reporting and validation_app are not independent Git repositories.
Do not merge everything into a new parent repository as cleanup.

| Repository | Tracked files | Pre-existing tracked changes | Pre-existing untracked entries |
| --- | ---: | ---: | ---: |
| `Utils` | 303 | 6 | 14 |
| `iride-input-availability-public` | 161 | 0 | 5 |
| `operational-validation-IRIDE` | 87 | 18 | 38 |
| `prefect-common` | 23 | 1 | 5 |
| `svc_S5-02` | 31 | 0 | 0 |
| `svc_s5-02-01` | 160 | 0 | 0 |
| `svc_s5-02-02` | 161 | 0 | 0 |
| `svc_s5-02-03` | 155 | 0 | 0 |
| `svc_s5-02-04` | 167 | 0 | 0 |
| `svc_s5-02-05` | 90 | 0 | 0 |
| `svc_s5-02-06` | 163 | 0 | 0 |
| `svc_s5-02-07` | 128 | 0 | 2 |
| `svc_s5-02-08` | 497 | 0 | 2 |
| `svc_s5-02-09` | 214 | 0 | 0 |
| `svc_s5-02-10` | 166 | 0 | 0 |
| `svc_s5-02-11` | 169 | 0 | 0 |

Untracked entries are Git status entries (which may represent whole directories),
not file counts. Preserve those investigations and modifications. Other cleanup
edits in this audit appear in addition to the baseline above.

## Utils organization and proposed reorganization

`src/eo_utils/` is the reusable library, `scripts/` its entry points, `workflows/`
contains local tools and investigations, `reference/` holds reference material,
and `buckets/` provides bucket helpers. This split is sound. The weak boundary is
runtime data inside workflow folders and documentation that lists every output.

Keep existing script paths. For new campaigns, use a configurable external runtime
root with separate downloads/results, retaining a small manifest in the workflow.
Migrate existing workflows individually with compatibility for old paths. Archive
completed experiments as whole cases (scripts + configuration template + manifest
+ result provenance), rather than moving isolated files and breaking relative paths.

See [Utils organization](Utils/docs/ORGANIZATION.md) for workflow groups and paths.

The local and public input audits overlap in five Python filenames. Four differ;
only download_mistral_daily.py is byte-identical. The public secrets setup refers
to the local config. Event workflows hardcode Utils paths, and validation uses its
runtime. Deleting the local audit or moving Utils wholesale would break callers.
Consolidation should first compare behavior/tests and extract shared provider
adapters into a package while retaining local/public entry points. No such code
migration was performed during this cleanup.

Static reference results: [cross-references](maintenance/2026-11-02/crossrefs.json).
The search covered normally discoverable Python, shell and YAML, excluding vendored
legacy code; it does not prove absence of external, IDE, binary GIS or dynamic use.

## Retention and deletion candidates

| Item | Size / evidence | Decision |
| --- | --- | --- |
| Operational `*.xlsx.inspect.ndjson` | 2.3 MiB generated inspection, no literal source reference found | Regenerable cleanup candidate; excluded from search, retained |
| Utils `.venv_py314_unused/` | ~10 MiB logical; untracked; no literal reference in searched source | Likely stale environment; verify interpreter/IDE/process use before removal |
| Utils `bilateral_filter/final_textured_output 2.tif` | 1.5 MiB; exact SHA-256 match to unsuffixed TIFF | Duplicate candidate; check sidecars/QGIS users before deleting |
| Utils `aoi_expansion_04/Old/` | Some components duplicate current files | Archive candidate; entire GIS datasets are not proven identical |
| Utils regression input runtime downloads | ~1.5 GiB allocated | Candidate cache cleanup after checking recoverability of historical provider data |
| Utils old Mistral downloads | ~891 MiB allocated | Archive first if upstream recovery is uncertain |
| Utils event downloads | ~769 MiB allocated, includes investigation evidence | Retain until event case retention is decided |
| `validation_app/validation/cache/` | ~46 GiB allocated | Required by user; retain in place, no deletion, relocation or pruning |
| Public input availability `validation_data/` | ~37 GiB allocated | Scientific reference data; use manifests/checksums and retention review before moving |
| `bucketBackup/` | 8.33 GiB logical | Recovery copy, not proven redundant; compare object versions/checksums and restore needs |
| Git history in products 07/08/09 | ~12.3 GiB logical in `.git` combined | Not loose unused files; future clone/history strategy, no manual object deletion |
| Root `.venv` and active Utils `.venv` | Existing interpreters; Utils is called by validation | Keep; not duplicate merely because there are multiple environments |
| `.codex_work`, outputs, deliverables, comparison baselines | Prior artifacts and possible active work | Preserve until task/campaign ownership and retention are established |

Hash evidence: [operational duplicates](maintenance/2026-11-02/operational_duplicates.json)
and [Utils tracked duplicates](maintenance/2026-11-02/utils_tracked_duplicates.json).
Duplicate detection used SHA-256 for nonempty files smaller than 20 MiB, grouped
by size first; Utils scope was tracked files, operational scope all regular files.
It is not an exhaustive large-raster deduplication audit. Sixteen Utils duplicate
groups total only about 6.3 MiB redundant contents, far less than the runtime data.
Git/LFS history means deleting a tracked working copy alone may not recover the
same amount of storage.

## Practical order for further work

1. Use the corrected operational entry point and bounded searches immediately.
2. Retain the required validation cache. Review only authorized Utils historical
   downloads, recording manifests/checksums and distinguishing caches from unique evidence.
3. Parameterize runtime roots in one workflow at a time, then migrate data with
   verified callers and documented restore paths. Keep source paths stable.
4. Consolidate divergent input audit implementations only after behavior comparison.
5. Consider fresh/shallow clones or repository history work separately for large
   product Git stores; remotes and local branches must be checked first.

This audit provides concrete candidates. It does not classify a file as unused
from age, name, zero observed imports or duplicate bytes alone.

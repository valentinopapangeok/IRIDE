# Positional-validation handover

Updated: 16 November 2026

This document records the current implementation state and next work for processing-induced positional validation. Permanent operating rules remain in AGENTS.md.

## Scope and scientific decision

The positional check measures geometry changes introduced by the S5-02 processing chain relative to the geometry supplied by each product's mandatory input. It covers rasterization, clipping, reprojection, resampling, mosaicking, fusion, assignment and downscaling performed by the processing chain.

Keep these quantities separate:

- native_to_final_assigned_centre_m: distance from an actual contributing input observation to the final cell receiving that contribution;
- grid_lattice_residual_m: residual between an inherited source lattice and the delivered lattice;
- support_radius_m: interpolation, nearest-search or footprint support.

Thematic RMSE/F1 and support radius are not positional displacement measurements. A nearest-cell distance is not treated as final-value lineage. Missing contributor identity is UNASSESSED.

The declared plan policy uses a percentage of assessed pixels within a product-specific spatial tolerance. The tolerance in metres remains unresolved in the operational configuration. The proposed 10% product-instance sample and 90% conforming-pixel criterion remain a proposal requiring agreement; they are not an implemented acceptance result.

## Architecture

The operational repository runs through:

1. production discovery and manifest normalisation;
2. SQLite registration of product, delivery ID and revision;
3. explicit product-adapter execution;
4. reference search/download and checksum reuse;
5. QA, collocation and metric calculation;
6. atomic evidence/provenance storage;
7. HTML report generation.

Relevant modules:

- s5validation/cli.py, pipeline.py, operational.py: launch and orchestration;
- s5validation/registry.py: SQLite state, attempts and campaign samples;
- s5validation/adapters.py: explicit adapter registration;
- s5validation/report.py: report assembly;
- s5validation/kpi_reporting.py and hourly_reporting.py: thematic KPI reporting;
- s5validation/references/: reference providers;
- s5validation/positional_reporting.py: separate revision-checked geometry report;
- tools/continue_precipitation.py: resumable product 04 campaign;
- config/validation.json: product thresholds, campaign dates, AOIs and sub-AOIs.

The geometry investigation and source caches are under validation_app/positional_proxy_20261113/. Its main evidence files are PROCESSING_DISPLACEMENT.md, SYSTEMATIC_KPI_GEOMETRY.md, REPORT.md, OCTOBER_ONE_DATE_PILOT.md and CHECKPOINT.md.

## Implemented functionality

The repository currently implements:

- production discovery for all eleven products;
- Landsat diagnostic comparisons for 01, 02, 10 and 11;
- ERA5 direct-normal solar comparison for 03;
- hourly regional-gauge validation for 04, including product-first rain screening, targeted requests, persistent caches, dry controls and the unchanged 20% relative-RMSE threshold;
- diagnostic Snow Cover comparison for 05;
- diagnostic MSG/MTG Cloud comparison for 06;
- diagnostic monthly GOSAT comparisons for 07 and 08;
- operational circular AERONET comparison for 09;
- separate positional evidence selection from thematic passing dates/hours;
- evidence statuses MEASURED_LINEAGE, GRID_ONLY, CODE_BOUND and UNASSESSED;
- revision checks that prevent stale evidence from being used for a changed delivery;
- offline tests for missing evidence and revision mismatch.

Products 01 through 11 official positional KPI integration is implemented in
`s5validation/positional_accuracy.py`. After a thematic run, passing
S5-02-01 dates are selected from `report/kpi_dates.json`; the stage reuses or
downloads checksum-receipted Sentinel-3 SL_2_LST ZIP inputs for the production
08:00–12:30 UTC window, runs the centre and delivered-footprint metrics (LST for
01 and WST for 02). Product 03 selects thematic-passing UTC hours, validates or
downloads the mandatory daily CMSAF/SARAH-3 DNI NetCDF, and measures its source
grid against the final hourly cell grid; ERA5 remains the thematic reference,
not the positional source.
writes revision-matched evidence under `positional/evidence/`. The KPI is
reported separately from thematic metrics and does not create campaign sample
units. DCO catalog/PS identifiers are external configuration; missing source
configuration or lineage produces `UNASSESSED`.

Product 05 is now also an autonomous post-thematic stage. It selects
revision-matched thematic-passing dates, validates or downloads the mandatory
OLCI LFR archives, and measures native OLCI coordinates against the final grid.
Optional VIIRS replacement occurs on that OLCI grid and therefore does not
change the positional geometry. Product 05 evidence is consequently
`MEASURED_LINEAGE` / `OFFICIAL` for processing geometry; it does not make a
sensor-value attribution claim and does not add campaign samples.

Product 04 selects hourly thematic-passing sub-AOI results (Whole AOI is not
scored by the uncertainty-adjusted precipitation report), requires the exact
delivery revision, and reconstructs the producer's HSAF/MISTRAL fusion and
last-write assignment. It downloads/reuses source inputs under the workdir,
validates checksums, compares matched rainy final cells to their source
coordinates, and reports the strict `<4000 m` percentage. Gauge/reference
support is not used as positional displacement.

Product 06 selects thematic-passing hours, downloads or reuses the mandatory
MTG/FCI Cloud Mask GRIB2 inputs, and measures their geolocation against the
delivered EPSG:4326 grid with the declared 3,000 m tolerance. The service asks
Satpy for `cloud_state`; the retained GRIB2 feed exposes the same mandatory
field as `cloud_mask` through ecCodes. All hourly source archives are
checksummed; their shared geolocation is measured once per hour.

Product 07 selects thematic-passing months, downloads or reuses the mandatory
Sentinel-5P PAL monthly HDF5 grid, and measures PAL source coordinates against
the final grid with the declared 3,500 m tolerance. GOSAT remains the thematic
reference and is not used for positional displacement. Missing or ambiguous
PAL lineage produces `UNASSESSED`.

Product 08 selects thematic-passing months, downloads or reuses both mandatory
OCO2 and OCO3 monthly inputs, reproduces the service's fixed histogram bins,
and measures histogram-bin-centre to producer-written-cell-centre displacement
with the declared 3,500 m tolerance. GOSAT remains thematic reference data.
The later final mosaic/smoothing has no contributor map, so this KPI is named
explicitly as the written-intermediate geometry quantity.

Product 09 selects thematic-passing dates, downloads or reuses the mandatory
MODIS MCD19A2.061 tiles, reproduces their sinusoidal-to-WGS84 native-grid
geometry and measures native centres against the final grid with the declared
1,000 m tolerance. AERONET remains thematic reference data; cells filled by
other fusion inputs are retained as a limitation rather than silently treated
as MODIS value lineage.

Products 10 and 11 select thematic-passing dates, download or reuse all same-day
mandatory Sentinel-3 SL_2_LST and SL_2_WST archives, respectively, and measure
nominal 1,000 m native parent-pixel footprints against valid 300 m downscaled
output-cell footprints. A 300 m cell overlapping its 1,000 m parent footprint
has zero parent-to-child displacement; cells outside same-day source coverage
remain explicitly unmatched. The official footprint KPI uses the 1,000 m
source-grid tolerance, with targets of 90% for 10 and 80% for 11. Landsat
remains the thematic reference; super-resolution value lineage is not used as
a positional attribution claim.

The 10/11 evidence also carries a `lineage_audit`. It records the producer's
declared 1,000 m parent versus 300 m target, the delivered target transform and
resolution, and the producer code path (`EPSG:4326`, 0.0025-degree lattice,
nearest-neighbour `griddata`). SRTM is recorded as a separate DEM-alignment
diagnostic. It is not included in the official positional percentage because
the producer uses SRTM as a model feature and did not deliver a final-cell
contributor map. If a checksum-receipted `SRTM.tif` is present, its CRS,
transform and resolution are recorded; otherwise the SRTM component is
`UNASSESSED`.

The positional report is generated at validation/report/positional_geometry.json. It is diagnostic only and does not alter kpi_dates.json, thematic scores or accepted campaign samples.

## October one-date pilot

| Product | Date | Current result | Status |
|---|---:|---|---|
| 01 LST | 1 Oct | Footprint KPI: 49,482 compatible cells; p50 = 60.73 m; p95 = 594.71 m; maximum = 1,160.01 m; strict <1,000 m = 99.9939%; inside footprint = 41.47% | MEASURED_LINEAGE / OFFICIAL |
| 02 SST | 29 Oct | Official WST lineage replay: 8,523 compatible final cells; centre <1,000 m = 74.76%; delivered-footprint <1,000 m = 96.93%; inside footprint = 43.32%; footprint maximum = 1,703.66 m | MEASURED_LINEAGE / OFFICIAL |
| 03 Solar | 31 Oct 23:00 UTC | Official CMSAF/SARAH-3 source-grid replay: 13,277 valid final cells; source-to-final centre maximum = 0.30 m; <1,000 m = 100% | MEASURED_LINEAGE / OFFICIAL |
| 04 Precipitation | 7 Oct 20:00 UTC | HSAF/MISTRAL last-write replay: 9,583 verified rainy final cells; median = 1,641.01 m; p95 = 2,164.24 m; maximum = 2,447.45 m; <4,000 m = 100% | MEASURED_LINEAGE / OFFICIAL |
| 02 SST | 29 Oct | nearest final-centre maximum 788.27 m; potential touched-scene maximum 2,395.76 m; candidate lattice residual maximum 67.80 m | GRID_ONLY |
| 03 Solar Radiation | 1 Oct | five passing hours, 55,687/55,687 final centres on the input lattice; maximum residual 2.48e-9 m | GRID_ONLY |
| 05 Snow Cover | 29 Oct | five mandatory OLCI scenes; 20,009 sampled native coordinates; nearest written-centre maximum 351.56 m; nearest final-centre maximum 176.57 m | MEASURED_LINEAGE / OFFICIAL |
| 06 Cloud Cover | 1 Oct | mandatory MTG/FCI Cloud Mask source-grid replay: 40,859 final cells; strict <3,000 m = 100.0000% | MEASURED_LINEAGE / OFFICIAL |
| 07 Methane | Aug 2026 | mandatory Sentinel-5P PAL source-grid replay: 71,010 source coordinates; strict <3,500 m = 100.0000%; maximum = 1,910.39 m | MEASURED_LINEAGE / OFFICIAL |
| 08 Carbon Dioxide | Mar 2026 retained case | mandatory OCO2/OCO3 histogram replay: 854 occupied bin occurrences; strict <3,500 m = 100.0000%; maximum = 2,635.21 m | MEASURED_LINEAGE / OFFICIAL |
| 09 AOD | 29 Oct | mandatory MODIS MCD19A2.061 replay: 332,010 geometrically matched final cells; strict <1,000 m = 100.0000%; maximum = 936.07 m | MEASURED_LINEAGE / OFFICIAL |
| 09 AOD | 29 Oct | 332,010 matched cells; modelled native-to-final maximum 936.07 m; canonical lattice residual effectively zero | GRID_ONLY |
| 10 LST Downscale | 25 Oct | 20 same-day mandatory Sentinel-3 LST scenes; 4,520,026 matched final cells; nominal 1 km parent-footprint overlap/edge distance strict <1,000 m = 90.7259%; maximum = 4,498.00 m; 791,357 valid cells unmatched | MEASURED_LINEAGE / OFFICIAL |
| 11 SST Downscale | 29 Oct | 10 same-day mandatory Sentinel-3 WST scenes; 14,232,420 matched final cells; nominal 1 km parent-footprint overlap/edge distance strict <1,000 m = 85.5292%; maximum = 4,678.47 m; 9,744,234 valid cells unmatched | MEASURED_LINEAGE / OFFICIAL |

The complete pilot table is maintained in validation_app/positional_proxy_20261113/OCTOBER_ONE_DATE_PILOT.md. These values must not be presented as absolute geolocation accuracy or as complete final-value displacement unless the evidence level says so.

## Outstanding work

1. Generalise the product 04 production-lineage reconstruction to every qualifying production hour and all relevant sub-AOIs.
2. Extend products 06–11 from the verified pilot cases to every qualifying thematic-passing hour/month/day.
3. Make product 02 GHRSST DUAL/NADIR source selection deterministic.
4. If required for value-level attribution, recover the product 05 final-cell OLCI/VIIRS contributor map; it is not required for the processing-grid positional KPI.
5. Trace product 07 intermediate raster through final resampling and flipping.
6. Trace product 08 OCO-2/OCO-3 bins through the final mosaic and resampling.
7. Recover prediction CSV rows and actual assignments for products 10 and 11; the official processing-geometry KPI is now available, but value-level attribution remains separate.
8. Identify final MODIS and fusion contributors for product 09.
9. Resolve product-specific metre tolerances for the declared positional percentage targets.
10. Add product adapters or an equivalent evidence builder for any remaining positional cases.
11. Add full offline tests for evidence generation, duplicate delivery revisions, hourly selection, sub-AOI filtering and checksum mismatch.

## Current repository state and constraints

The worktree contains uncommitted implementation and documentation changes, including product 04 tooling, positional reporting, documentation and tests. Review the worktree before committing; do not assume every existing modification belongs to the positional task.

The local validation cache and positional source caches are required retained data. Partial downloads and failed candidate inputs are retained deliberately and must not be deleted as cleanup.

## Reproduction and tests

From the repository:

    .venv/bin/python -m unittest discover -s tests -v
    .venv/bin/python tools/smoke_test.py
    .venv/bin/python -m pip check
    .venv/bin/python -m s5validation.cli --report --workdir /Volumes/Extreme/IRIDE/MKPL/validation_app/validation

The first three checks passed on 16 November 2026. The full positional pilot is not reproduced by a single repository command yet; its scripts and receipts are under validation_app/positional_proxy_20261113/.

For a new implementation, first confirm the exact delivery revision and final checksum, mandatory-input identities and checksums, processing-code revision, source-to-intermediate transforms, contributor/support maps for fusion, and product/sub-AOI selection from the current thematic report. Only then should evidence be written under validation/positional/evidence/.

## Known technical debt

- Most passing records remain UNASSESSED, which is correct but incomplete.
- Pilot scripts are not yet a unified product-adapter interface.
- Several measurements are sampled or grid-only and cannot establish final-value lineage.
- Product 04 lineage covers a selected production hour, not the complete operational campaign.
- Product 05 has multiple cached revisions for at least one selected date and needs explicit revision selection.
- Products 10/11 need explicit prediction-row provenance and assignment diagnostics.
- The worktree has no finalized commit boundary for the positional implementation.

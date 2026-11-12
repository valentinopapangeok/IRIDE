# Product 03 ERA5 direct-radiation comparison

On 21 October 2026 the user explicitly adopted the reference-only conversion as the operative validation methodology. This is project authorisation, not a claim of independent certification or ASI approval. The operative reference path is `era5_direct`, using **ERA5 hourly single-levels** (`reanalysis-era5-single-levels`), variable `total_sky_direct_solar_radiation_at_surface` (`fdir`, parameter 228021). This is **not ERA5-Land**. The plan's ERA5-Land wording must be reconciled; changing the configured dataset does not establish plan approval. CAMS remains an explicitly selectable supplementary method. Old files and results remain cached under their original method signatures.

## Confirmed product and time conventions

The inspected production source reads CMSAF `DNIinYYYYMMDD*.nc`. `src/steps/processing/data_fusion.py` selects H:00, H:30 and H+1:00 and uses xarray time integration in hours. The delivered quantity is hourly integrated direct-normal radiation, Wh/m². Hour 23 integrates only the available final half hour in the inspected code and remains excluded. Post-processing clips to Italy; the production code and product are not modified by validation.

The CDS ERA5 reanalysis FDIR field describes **direct radiation through a horizontal plane**, accumulated during the hour ending at the validity timestamp. Thus production H–H+1 matches ERA5 validity H+1. Divide J/m² by 3600 to obtain Wh/m². Do **not** difference consecutive ERA5 values using the old ERA5-Land daily-reset logic. Do not compare DNI to total horizontal SSRD. FDIR includes actual cloud effects; it is not the clear-sky CDIR variable.

Authorities: [ECMWF parameter 228021](https://codes.ecmwf.int/grib/param-db/228021), [ERA5 hourly single levels](https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels), [ECMWF accumulation conventions](https://confluence.ecmwf.int/spaces/CKB/pages/197702790/Conversion+table+for+accumulated+variables+total+precipitation+fluxes).

## Reference-only geometry conversion

The default method `era5-direct-normal-reference-v3-operative` leaves delivered direct-normal product values unchanged. Values are averaged onto ERA5 spatial support for comparison; no radiation geometry factor is applied to the product.

ERA5 FDIR is first converted from J/m² to Wh/m². At each ERA5 cell centre the reference is then converted to hourly direct-normal exposure as `FDIR_Wh / mean(cos(solar_zenith))`. The hourly cosine is integrated with eight-point Gauss-Legendre quadrature using the [NOAA solar equations](https://www.gml.noaa.gov/grad/solcalc/solareqns.PDF). This follows the interval-integration principle discussed in [ECMWF Technical Memorandum 895](https://www.ecmwf.int/sites/default/files/elibrary/2022/20336-calculating-cosine-solar-zenith-angle-thermal-comfort-indices.pdf); it is not an exact native ERA5 DNI field.

The conversion assumes constant direct-normal irradiance within the hour. Hourly FDIR alone cannot resolve within-hour cloud variability, so the result is an **approximate ERA5-derived reference**. Original product half-hourly inputs are not required for this method. Reference sensitivity limits use FDIR divided by the maximum/minimum cosine sampled at one-minute intervals. Metric sensitivity uses a fixed central-reference mean denominator and per-cell best/worst errors within those limits; these are not statistical confidence intervals or all-source uncertainty bounds.

ERA5-grid comparison uses average resampling, exact-AOI cell-centre selection and product nodata/scale/offset. `minimum_cell_coverage` means valid fraction within contributing product support, not independently validated full-cell footprint coverage. Fixed screening requires solar elevation >=10 degrees throughout the sampled hour at the reference cell centre, original horizontal FDIR >=20 Wh/m² and >=90% valid contributing support. These fixed screening choices are part of the adopted operational method; they are not thresholds selected by observed error. Missing or insufficient-support cells are excluded rather than treated as zero truth.

Results retain whole-AOI and North/Center/South rRMSE, signed bias, reference mean, geometry sensitivity and matched-cell CSVs. rRMSE is 100×RMSE/absolute mean paired **derived direct-normal reference**, in Wh/m². A zero denominator is undefined. Operative outcomes use PROCESSED and record the matching method ID, user authority and uncertainty policy in their provenance. The central converted reference is evaluated against the unchanged rRMSE ≤20% threshold. Hourly reporting scores these as PASS/FAIL only when recorded approval matches the configured operative method; historical v2 diagnostic results remain APPROXIMATE_GEOMETRY until rerun. The approximate_geometry flag and sensitivity estimates remain present: adoption does not remove conversion uncertainty. No legacy reference-sample entries are added and no overall contractual acceptance is inferred.

Set `solar.era5_direct.enable_reference_conversion=false` to disable reference conversion (PENDING_CONFIGURATION). Legacy local configurations may still use `allow_hourly_projection_trial`; they remain diagnostic without matching method approval. Existing horizontal-comparison results remain separate under their original method signatures; do not relabel or merge them with reference-only results.

## Running and caching

Normal PyCharm `main.py` includes the new adapter and reference downloader. Product-only runs use `python main.py --product S5-02-03`. Existing private `credentials/downloaders.env` supplies `CDS_KEY`, optionally `CDS_URL`; accept the ERA5 single-levels dataset terms in the CDS account. No new private file is required. Local report/validation runs never fetch references implicitly.

Downloads are scoped to required validity dates, validated for all 24 hours, checksummed and retained under `cache/reference/era5_direct/`. Existing ERA5-Land SSRD and CAMS caches are not reused as FDIR and are not deleted. Every result is isolated by method, policy, delivery checksum, reference receipt and implementation signature. No background scanner was restarted.

## Operational KPI counting

Five distinct qualifying UTC dates per month, with at least one contribution from North, Center and South across the monthly set. One passing eligible hour in a sub-AOI qualifies that date; neither additional hours nor additional sub-AOIs multiply the daily KPI. No hourly percentages are averaged to produce a daily metric. All valid pairs in the selected hour/sub-AOI are included, including failures. See [KPI counting](KPI_COUNTING.md). The thresholds, fixed screening rules and delivered radiation values are unchanged.

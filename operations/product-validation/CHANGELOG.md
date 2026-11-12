# Changelog

- Add product 04 same-pixel gauge-support diagnostics: retain every rainy point comparison, identify pixels with at least three independent gauge locations, and report a separate area-reference comparison without changing the operative accuracy decision.

- Add product-first precipitation screening, a persistent categorized gauge-location catalogue, targeted regional/time extracts and deterministic product-dry controls. Preserve the original pixel comparison, all cached observations and explicit partial-reference scope.

- Correct 03/04/06 reporting to independent UTC production hours, following the user clarification and original hourly sampling requirements; preserve undefined/pending/QA states and remove active daily KPI pooling.

- Add opt-in continuous network recovery for the precipitation campaign, preserving bounded waits and stopping ambiguous submissions for reconciliation.

- Recover a missing completed MeteoHub server extract through archived-request lookup and one bounded replacement, preserving prior receipts and every verified local reference.

- Retain and reuse available AERONET snapshots without re-downloading; add resumable multi-date precipitation continuation, provider rate limits and opt-in quota recycling that preserves every local reference file.

- Add diagnostic product 04 hourly regional-gauge validation, strict accumulation matching, resumable MeteoHub extracts and pooled daily area/station reporting. Initial live gauge comparison verified; delivery unit confirmation remains pending.

## 2026-10-19 — Cloud and monthly greenhouse-gas integration

- Register 06 hourly MSG cloud and 07/08 monthly GOSAT reference downloaders and diagnostic adapters.
- Reuse shared private downloader credentials, verified persistent references and automatic directory initialization.
- Report cloud passing days for Italy and sub-AOIs by pooling every eligible hourly confusion count.
- Document explicit temporal/spatial defaults and limitations; preserve accepted-sample and production-chain rules.
- Add offline decoding, unit, QA, cache, lifecycle and reporting tests.
- Bound production transfers to four workers and MSG transfers to two; reuse identical native GRIB geolocation without changing matchups.

## 2026-10-19 — Operative AOD circle method

- Promote the approved 27.5 km circular AOD comparison to the main.py default for product 09.
- Add four-channel spectral conversion, daily all/passing station metrics, exact sub-AOI counts and overlap-deduplicated sampled-pixel coverage.
- Preserve original product/reference files and legacy evidence; record the user-declared October 20 production transition separately.


## 2026-10-19 — Recorded campaign decisions

- Added versioned North/Center/South land and marine AOI partitions at 41.5°N and 44°N, preserving the original AOIs.
- Recorded user approval of the evaluated 27.5 km AOD adaptation; NASA is provenance rather than a certification gate.
- Defined positional tolerance as strictly less than declared product resolution, without asserting measured positional compliance.
- Kept the current operational AOD adapter separate from the approved trial pending integration.


## 2026-10-16 — AOD validation reporting

- Display containing-pixel and supplementary 3×3 AOD metrics on identical station-days, with coverage exclusions and pair-pooled metrics.
- Preserve the primary method, acceptance status, product files and production chain.


## Validation method corrections

- Default solar reference is now equivalent hourly CAMS all-sky BNI, using existing ADS credentials, exact-AOI fixed points, explicit screening and all-condition audit metrics; incompatible SSRD comparisons are blocked by default.
- Legacy small negative energy handling is precision-aware and capped.
- Snow uses full-cell snow-area bounds, 90% clear coverage and excludes conflicting overpasses.
- Snow/AOD use optional delivered QA/time/wavelength support; missing support stays diagnostic. AOD adds supplementary 3×3 metrics without replacing the baseline.
- Added regression tests, equivalent-observable smoke coverage and portable guides; no accepted samples are added.


## 0.1.0

- Standalone portable package and `iride-validate` command.
- Automatic resource checks and runtime initialization on every launch.
- Bundled exact land/marine AOIs, checksums and extracted S5-02 validation requirements.
- Read-only production inventory/downloads for eleven output products.
- Shared Landsat 8/9 L2SP cache and diagnostic thermal comparisons for 01/02/10/11.
- Explicit rRMSE normalization by absolute paired reference mean in Celsius.
- External production credential-file support with process-environment transport and error redaction; existing MinIO aliases remain supported.
- Scientific metric helpers, revisioned SQLite evidence and HTML/plot reports.
- Offline synthetic smoke test, fixture-based tests and cross-platform CI.
- Installation, credential, runbook, configuration and product-extension guides.

## Operational campaign orchestration

- Added no-argument `main.py` for PyCharm and `--run` for the CLI.
- Added all-campaign discovery with date boundaries and highest numeric versions, selective downloads, pending retries, reference-date/domain filtering, preflight and error isolation.
- Preserved scientific states, method-aware thermal cache, offline modes and accepted-sample safeguards.
- Added console/JSON run summary, report integration and PyCharm guide.

## Snow and AOD adapters

- Added public Sentinel-2 SCL-only download, conservative pixel QA, native snow-cell aggregation, overlap deduplication, binary metrics and evidence.
- Added AERONET V3 download, explicit quality levels, provisional 550 nm spectral matching and station-day aggregation with paired CSV and diagnostic plots.
- Integrated both into the no-argument main workflow and product-specific report trends; added scientific tests and methodology/credential guides.

## Solar radiation adapter

- Integrated the existing product 03 hourly diagnostic DNI/SSRD method with operational CDS downloads, verified daily reference cache, registry, paired CSV, plots and report trends.
- Preserved original rectangle, reference-mean normalization, midnight reset and hour-23 exclusion. Added scaled-raster handling and offline scientific/provider/lifecycle tests.

## Solar processing label

- Replaced solar runtime DIAGNOSTIC labels with PROCESSED; removed diagnostic metric flag and runtime scientific caveats, preserving methodology documentation and zero accepted-sample accounting. Historical results are retained; shared retry and report handling support PROCESSED.

## AOD source provenance correction

- Accept aligned delivered source IDs and report EO, individual sources and CAMS fill separately. Keep source-unverified historical deliveries explicitly diagnostic.
- Record station exclusions caused by missing source times or insufficient time-window observations; use the same source for neighborhood sensitivity.
- Add offline coverage for model separation, model-only outcomes, source identity validation and source-time exclusions. Normal PyCharm `main.py` launch and credential files are unchanged.

- Added ERA5 single-levels FDIR downloads and horizontal-geometry diagnostic adapter with correct ending-hour accumulation, fixed screening, projection sensitivity bounds and per-sub-AOI evidence. CAMS is supplementary; approximate geometry cannot silently count as a passing KPI.

- Product 03: reference-only ERA5 FDIR to direct-normal conversion using interval-integrated solar geometry; delivered radiation values unchanged, separate v2 signature and diagnostic uncertainty.

- Adopt product 03 ERA5 reference-only direct-normal v3 as operative under explicit user instruction (2026-10-21); preserve approximation evidence and historical diagnostic outcomes.
- Add integrated distinct-date/month KPI reporting: five dates, North/Center/South distribution, one passing hour for hourly dates, and monthly coverage gate. Keep all-eligible AOD regional scores and legacy sample accounting separate.

### Gauge network expansion (22 October 2026)

- Configure 20 institutional precipitation networks with shared regional request mapping. Bootstrap newly enabled networks on existing workstations, retain raw caches and avoid repeat empty bootstraps. Scientific metric, hourly matching and station eligibility rules remain unchanged. Historical availability is verified through bounded extracts, not assumed from the catalogue.

### Rainy-only precipitation assessment (22 October 2026)

- Adopt the user-selected positive-reference-rainfall condition with method v3 provenance; retain product-zero misses, all failed rainy pairs, the 20% threshold, and all-condition audit evidence. Exclude dry-only matches from primary scores. Supplement discovery with explicit reference-supported event windows; preserve prior methods and raw caches.

### Precipitation reference-quality review (22 October 2026)

- Add independent neighbour-consistency review flags and separate native-radar discrepancy flags. Preserve all operative observations; spatial anomalies do not automatically reject gauges. Document original-versus-QC sensitivity reporting and evidence requirements for bounded exclusions.

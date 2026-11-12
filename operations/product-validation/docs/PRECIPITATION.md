# 04 Precipitation: hourly regional gauges

Product 04 is registered as `regional_gauges_hourly`. Run `main.py` in PyCharm as usual, or run only this product:

```bash
python main.py --product S5-02-04
```

Initial bounded integration check:

```bash
python main.py --product S5-02-04 --max-deliveries 1
```

## Observable and reference

The nominal delivery interval is `[filename UTC hour, next hour)`, confirmed on a production XML. The processing source converts MISTRAL rates from mm/s to mm/hour and integrates the nominal hour. The comparison explicitly interprets output numerical values as **hourly millimetres**. The sampled TIFF has no unit tag, and its XML uses generic unit labels; the source configuration also contains `m`. This metadata inconsistency remains recorded. Raw hourly gauge comparisons retain `DIAGNOSTIC` delivery status; the separately reported uncertainty-adjusted lower-bound date decisions follow the [operative method](PRECIPITATION_UNCERTAINTY.md). They do not make a claim of contractual acceptance or measured product RMSE below 20%. No production code is changed by this validator.

Authenticated MeteoHub extracts initially covered three regions:

| Network | Region |
| --- | --- |
| `simnbo`, `simnpr` | Emilia-Romagna |
| `dpcn-lazio` | Lazio |
| `dpcn-sicilia` | Sicily |

The default configuration now includes **20 institutional networks across 19 regional/provincial groups**: the four above plus Basilicata, Bolzano, Calabria, Campania, Liguria, Lombardia, Marche, Molise, Piemonte, Puglia, Sardegna, Umbria, Veneto, Trentino, Toscana and Friuli-Venezia Giulia. Their catalogue listing was verified on 22 October 2026; historical hourly B13011 availability and usable support must still be established per extraction. No complete nationwide coverage is claimed.

`precipitation.network_regions` maps each configured network to exactly one request group; `precipitation.networks` selects enabled networks. The screening planner and station catalogue use that same mapping. With `screening.bootstrap_missing_networks: true`, an existing old catalogue triggers a bounded one-group, one-hour bootstrap for previously undiscovered networks. Successful empty extracts are retained rather than submitted indefinitely for that same bootstrap. A catalogue mapping change reindexes retained raw files; no observations are deleted. Newly enabled groups invalidate screening cache identities. Reduce the configured network list to scope a run; leave corresponding entries in the mapping.

Adding a network changes comparison support, not the metric. Retain the earlier evidence and identify network coverage in every new result. Additional stations are not selected by product error. Cross-network physical-site duplicates and provider quality flags require reference evidence; do not infer independent measurements merely from distinct network IDs.

These networks sample the AOI; they do not provide wall-to-wall coverage. Stations are assigned geometrically: North ≥44°N, Center 41.5–44°N, South <41.5°N, inside the exact bundled campaign AOI.

## Credentials and resumable downloads

Use the existing private downloader credentials file, containing `METEOHUB_BASE_URL`, `METEOHUB_USER`, `METEOHUB_PASSWORD`. No new credential file or station list is required. The configured base URL must be HTTPS. Tokens remain in memory; downloaded reference data and request receipts stay under the configured workdir.

Normal operational runs use the authenticated `/api/data` extraction endpoint with `only_reliable: true` and JSON output. Cache: `cache/reference/regional_gauges/`. Extracts are checksummed and retained; subsequent runs reuse them. Do not delete reference caches between runs.

MeteoHub is asynchronous. Each launch polls existing extraction IDs once. A pending extraction produces `PENDING_REFERENCE`, not a failed comparison. It never submits a duplicate while that job is unresolved. Initial defaults are deliberately bounded: **one new precipitation-only extraction per launch, up to one hour, 128 MiB maximum downloaded output**. This is an initial integration policy, not yet a full-campaign throughput setting. Provider quotas and server queue can delay results; the first live response was verified, but larger spans still require quota/size checks. New submissions are held when account free space is below the configured maximum output size. Default mode does not remove remote extracts. Explicitly authorized archiving of verified pipeline extracts is available as described below; it never removes local data or unrelated account files.

A transport failure during submission retains `submission_intent.json`. Reconcile that payload against the account's request list, record its request ID in `index.json`, then remove the reconciled intent. Do not blindly delete an intent and resubmit: the server may have accepted the first request. Failed jobs remain visible and require investigation rather than silent resubmission. Provider errors appear in `inventory/operational_run.json`; pending/missing hours are separately listed in `inventory/regional_gauges_refresh.json`.

## Time, quality and matching

DB-All.e JSON `B13011` is total precipitation in kg/m², numerically mm of liquid water. Values are already physically scaled. `date` is the accumulation **end**, in UTC. An hour beginning at 00:00 matches a gauge accumulation ending at 01:00, not 00:00.

Only surface observations with accumulation timerange `[1, 0, duration_seconds]` and duration ≤3,600 seconds are considered. Prefer an exact hourly observation. Otherwise require a unique complete partition of subhour observations with no gaps or overlaps. Never prorate daily/six-hour amounts, turn missing values into zero, or sum overlapping hourly and subhour records. Identical duplicates collapse; conflicting duplicate values exclude that station-hour.

The authenticated extraction's reliable-only filter is retained in its receipt. Nonfinite/negative amounts and explicit DB-All.e invalid-domain flags are excluded. Unknown QC attributes are retained without inventing interpretations. The nearest containing product pixel is sampled at each gauge; product nodata, negative values and locations outside the raster/AOI are excluded. Raster scale/offset are applied once. An explicitly conflicting raster unit raises an error. No radius expansion, spatial smoothing, outcome-selected stations or timing shifts are used.

## Rainy-only assessment adopted 22 October 2026

The user explicitly selected `reference_condition: positive_gauge_rainfall` under `regional-gauges-hourly-v3-rainy-only`. A primary pair requires complete QA-valid gauge accumulation **strictly greater than zero mm** and a finite valid matched product value. Every such pair is retained regardless of agreement, including product zero against measured rain. Dry gauge-hours are not primary evaluation observations. The **20% rRMSE threshold remains unchanged**. The 0.2 mm event-detection threshold is a supplementary diagnostic and does not define rainy eligibility.

`matched_all_conditions.json` preserves every valid spatial/temporal match for audit; `paired_data.json` contains only the selected evaluable pairs. Metrics record matched, rainy and excluded-dry station-hour counts. A completed extract without evaluable rainy pairs is explicitly QA-excluded, not a percentage pass. Receipts and raw reference caches are unchanged and reusable. Cached results have distinct method/policy signatures; historical all-condition results must not be silently mixed into a rainy-only report.

Scores remain separate for every UTC hour and sub-AOI. Individual passing gauges / evaluable rainy gauges is a different statistic from regional rRMSE, which uses **all** eligible rainy pairs including failures. The operative date rule additionally selects one gauge per product pixel by geometry, then applies the uncertainty lower bound and same-hour spatial gates. Sampled networks are recorded from all valid matched observations before the rainfall condition, so a dry network is not confused with an absent reference extract; rainy-network support is also recorded.

### Monthly full-day dry-condition diagnostic

The report separately seeks one **reference-sampled, complete 24-hour dry day per month and sub-AOI**. This is supplementary false-rain evidence and never counts toward the five rainy-intensity dates or changes rRMSE eligibility. A UTC date qualifies for this diagnostic only after all 24 product hours and their matched reference artifacts are available. In that sub-AOI, every available matched gauge observation must be below the existing 0.2 mm rain-detection threshold, and a stable panel of at least 10 gauges spanning at least five product pixels must have a valid match in every hour. The earliest qualifying date in a month is displayed; selection never uses product agreement. Product readings ≥0.2 mm at those stable dry gauges are reported as false-rain gauge-hours over the full 24-hour panel. Network names, gauge count and minimum pixel support are retained in `report/precipitation_dry_days.json` and `.csv`.

The sampled panel is not a claim that every pixel of the sub-AOI was dry. If a month lacks 24-hour product/reference support or a dry reference panel, the report states that status explicitly and makes no passing/failing dry-day claim. Existing product-first screening does not guarantee a complete dry day; reference acquisition for a monthly dry-day sample must be planned separately and independently of product rain agreement. No extra request is triggered by report generation.

### Reference-only hour prioritisation pilot

`tools/precipitation_interest.py` freezes a reference-only selection manifest before scoring. It uses only exact-hour, QA-valid positive-rain gauge pairs already matched to valid product pixels. An hour is *well supported* in one sub-AOI when it has at least 10 distinct rainy stations, at least five occupied product pixels and a maximum observed hourly accumulation of at least 1 mm. These are proposed planning cutoffs to avoid evidence dominated by one gauge or one cell; they are **not** new scientific pass criteria or a way to discard otherwise evaluable rainy pairs. All other evaluable hours remain in the limited-support tier and are also scored and reported. Missing references and no-rain hours stay separate.

The two-step run is offline and preserves the evidence used for selection:

```bash
PYTHONPATH=. .venv/bin/python tools/precipitation_interest.py select --results /path/to/current_results.json --manifest /path/to/new/selection.json
PYTHONPATH=. .venv/bin/python tools/precipitation_interest.py score --manifest /path/to/new/selection.json --csv /path/to/new/hourly_scores.csv
```

Use a new manifest/output path for each run. The manifest records artifact hashes and contains no product values or comparison scores. Scoring refuses changed pair artifacts and uses the existing containing-pixel, exact-hour rRMSE calculation over **every** positive-rain gauge pair in the selected sub-AOI hour: `100 × RMSE / mean(gauge rainfall)`, with the unchanged 20% limit. No gauges, hours or sub-AOIs are selected using product agreement. Report well-supported and limited-support outcomes separately; a date contributes at most one possible daily KPI even when several areas/hours pass. This pilot remains diagnostic until the product unit and contractual method are resolved.

### Point and pixel-area support

Every positive-rain gauge with a valid containing product pixel retains its **point comparison**, regardless of how many other gauges share that pixel. The additional `pixel_area_support.json` artifact identifies pixels with at least three independent gauge locations in the **same raster cell and UTC accumulation hour**. Locations within 100 m are treated as one possible physical site; collocated readings are reduced to their median before each site contributes equally to the pixel reference mean. QA-valid dry gauges participate in that area mean, while only positive-rain gauges are evaluated as target station-hours. The artifact retains the pixel reference and support classification for audit.

`metrics.pixel_area_support` reports the number of rainy station-hours and pixels with area support, plus a separate diagnostic pixel-reference rRMSE and count of individual pixels within 20% per sub-AOI. The hourly report CSV includes these support counts by sub-AOI alongside the unchanged point-comparison result. These fields do not change the operative point pairs, the 20% product threshold, the `DIAGNOSTIC` status or campaign KPI counting. A pixel with fewer than three independent gauge sites remains a valid point comparison but has insufficient gauge-only evidence for an area-average reference. Do not interpret the supported subset as performance across the entire sub-AOI; report its support fraction. The defaults are `pixel_support_minimum_locations: 3` and `pixel_support_minimum_separation_m: 100`.

Discovery may use product-first rainfall screening and deterministic controls to identify precipitation missed by the product. These downloads do not make dry gauges eligible for scoring. Optional `screening.reference_event_hours` supplements discovery with explicit reference-supported network/hour windows, independent of product error and pass/fail outcomes. Cached observed positive rainfall can justify adjacent-hour retrieval; each retrieved hour is scored only if independent gauge rainfall is actually positive. All requested windows remain inside retained delivery availability.

## Metrics and reporting

- Primary diagnostic: `100 × RMSE(product_mm − gauge_mm) / mean(gauge_mm)` across **all evaluable positive-rainfall pairs**, including failed comparisons. Historical all-condition results included dry observations and remain archived separately. Workbook target ≤20%.
- Event diagnostics use an explicit **0.2 mm/hour** wet threshold. This is a provisional diagnostic choice, not a workbook requirement. Both-wet metrics are supplementary and never replace the all-pairs primary result.
- All-zero reference hours have no evaluable rainy pairs. Their raw/matched evidence is retained, but they are not scored as rainy-hour passes. The rainy-only assessment does not measure false rainfall at dry gauges; that scope limitation is explicit.
- Each production hour has its own area score using all eligible gauge/product pairs for that exact hour. Every eligible gauge in the hour has equal weight. No errors or percentages are pooled across hours.
- Reports show **passing hours / evaluated hours** for whole AOI and each sub-AOI. `report/hourly_scores.csv` and `.json` retain each UTC interval, rRMSE, station-pair count, result and processing status. `hourly_summary.csv` and `.json` give campaign and monthly hour counts. A station or sub-AOI is not an additional independent production. Historical daily exports are superseded, retained only as archives.
- Point gauges and gridded estimates have different spatial support. Gauge uncertainty, regional sampling and product time integration remain limitations. No measured positional accuracy is claimed; the user's declared positional convention remains separate.

## Verification

Offline tests exercise accumulation end-stamps, units, complete subhour windows, missing/overlapping periods, conflicting duplicates, QC, dry false alarms, zero denominators, raster nodata, regional scoring, daily pooling, cache integrity and pending-request lifecycle. They make no network requests. Real retrieval is opt-in through `main.py --product S5-02-04`.

Format authorities: [DB-All.e JSON](https://arpa-simc.github.io/dballe/general_ref/json.html), [time ranges](https://arpa-simc.github.io/dballe/general_ref/tranges.html), [variable table](https://github.com/ARPA-SIMC/dballe/blob/master/tables/dballe.txt), [MeteoHub guide](https://www.mistralportal.it/ui/user-guide).

## Continue a multi-date campaign

After `main.py --product S5-02-04` has cached production deliveries, this resumable helper polls reference jobs, downloads new batches, compares cached deliveries and updates the hourly report:

```bash
python tools/continue_precipitation.py
```

It uses the same default config, credentials, cache and workdir as `main.py`. `--once` performs one bounded refresh; `--config`, `--workdir`, `--inventory-file` and `--registry-file` support isolated runs. A local SQLite path can be supplied when the workdir is on an external volume with unsuitable locking. The helper never downloads production again. Its process lock prevents duplicate continuation workers, and the provider has a separate cache writer lock for coexistence with `main.py`.

Checkpoint: `inventory/precipitation_continuation.json`. States include `RUNNING`, `RETRYING`, `COMPLETE`, `NEEDS_QUOTA` and `NEEDS_ATTENTION`. Transient provider errors have bounded retries; ambiguous submissions stop for reconciliation. Provider hourly request limits produce a resumable wait. To resume after interruption, rerun the same command; verified local data remain reusable. `current_results.json` and `registry_snapshot.db` retain the latest registry snapshot.

For an explicitly authorized account, set `precipitation.archive_verified_remote_extracts` to `true` in the local run configuration to recycle **only temporary server extract files**. The default shipped value is `false`. Archiving requires a successful raw local file, matching SHA-256, valid pipeline request signature, and matching remote request ID/name/networks/interval/filter. A local archive receipt is written before the server call. The server retains request metadata; all local raw data, comparison evidence and receipts remain untouched. Unrelated account extracts are never archived. An archive is never a reason to re-download the corresponding verified local file.

A larger batch can be configured with `hours_per_request` (1–24) and `maximum_extract_mb`, bounded by actual account free space. The October 20 continuation uses three-hour, 64 MiB batches with authorized archiving. When screening is disabled, `date_order: "least_reference_hours_first"` first fills the dates with the least reference-hour coverage, then revisits them until all delivered hours are covered. This scheduling uses availability only, never comparison outcomes. The scheduler is still exploratory availability ordering, not proof of the required representative event sample. The workbook (Batch1!I16/K16) prioritizes observed rain events and includes dry conditions for false detections; midnight-only hours cannot establish representative precipitation performance.

If an extraction disappears from the active list, the provider also checks the archived listing by exact request ID. A completed job without a downloadable server output is retained as `REMOTE_OUTPUT_UNAVAILABLE`. When its interval has no verified local reference, one replacement request is permitted; repeated loss stops for investigation. Existing verified local data are never re-requested for this reason.

For an unattended campaign with intermittent connectivity, pass `--retry-network-errors` to the continuation helper. Connection and timeout errors then remain in `RETRYING` until connectivity returns, using the bounded poll interval. TLS errors, ambiguous extraction submissions and repeated non-network failures still require attention. No local reference file is removed during outages or recovery.

## Product-first regional requests — operative default

`precipitation.screening.enabled` now defaults to true. The pipeline downloads/checksums production first, opens each cached TIFF, and screens for product-detected rain near known gauge locations. The catalogue is built automatically from the station metadata carried in retained MeteoHub extracts and is stored as `cache/reference/regional_gauges/stations.json` and `.csv`. It records name, coordinates, network, region and North/Center/South assignment, with checksummed source receipts. These are **known locations from cached observations**, not a guarantee that every station is currently active. New locations are added as more files arrive.

An empty installation bootstraps one bounded all-network reference hour to obtain station metadata; it does not require a privately shared station file. Existing installations reuse their metadata cache. The screening cache keys include product SHA-256, catalogue, AOI, policy and implementation; unchanged files do not need another raster inspection. The plan and explicit selections/deferred cases are recorded in `inventory/precipitation_screening.json`.

Defaults:

- Detect values ≥0.2 interpreted mm in a **3×3 native-pixel window around catalogued station locations**. This is only a download trigger. The scientific comparison remains the original containing-pixel comparison; no neighbouring value is selected to improve agreement.
- Request only the relevant regional datasets: Emilia-Romagna (`simnbo`, `simnpr`), Lazio (`dpcn-lazio`), Sicily (`dpcn-sicilia`). The first implementation filters by **regional network and time**, not by individual station IDs. All eligible gauges in each requested network are compared, including dry gauges away from the product rain.
- Keep a reproducible 10% sample of product-no-rain region-hours, using `control_seed`. These test product misses/false detections; absence of product rain alone is never evidence that the reference is dry. Reserve every fifth new extraction for available preselected controls. Selection never uses gauge agreement, rRMSE or pass/fail results.
- Prioritize regions with less cached reference-hour coverage, then a larger fraction of station locations near detected rain and greater product intensity. These are product-triggered candidate events; **observed** rain is only established after the gauges arrive. The resulting sample is conditional, not an unbiased estimate of all-weather Italy-wide error.
- Group selected regions at the same hour into one request. Batch contiguous selected hours only when they need exactly the same dataset set, within `hours_per_request` and the provider output limit. Do not add unselected region-hours silently.

All existing verified reference observations remain usable even when their original hour would not be chosen by the new screen. Cached regional extracts can be combined to cover a production hour; partial coverage is explicit. A whole-AOI threshold pass is counted only when all configured networks have eligible sampled gauges. Otherwise the root result is `PARTIAL_REFERENCE_COVERAGE`, not a whole-AOI pass or failure. Sub-AOI scores represent their sampled gauges and list contributing networks in the hourly export. Missing reference regions are not assumed dry.

The continuation worker revisits an hour when additional reference regions arrive, preserves all data, and can finish as `COMPLETE_SELECTED` when the selected request plan is covered. Deferred product-dry hours are `NOT_SELECTED`, not validation failures. Disable screening explicitly to restore the exhaustive all-network request scheduler. Existing pending extracts finish and are retained before new targeted requests are submitted.

An explicitly superseded broad request is retained in the local index but does not block targeted submissions. `SUPERSEDED` does not mean remotely cancelled: account permissions may deny cancellation, and the original extraction can remain queued on the server. All existing local caches remain intact.

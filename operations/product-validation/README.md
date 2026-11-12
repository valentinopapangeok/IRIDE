# Operational Validation — IRIDE

Manually launched scientific validation for IRIDE S5-02 products. The pipeline downloads production deliveries and reference data, applies quality filters, collocates observations, calculates metrics, and keeps a local SQLite registry with reproducible evidence and HTML reports.

**Implemented:** production downloads for all eleven products; Landsat 8/9 thermal reference downloads and preliminary comparisons for **01 LST, 02 SST, 10 downscaled LST and 11 downscaled SST**. **05 Snow Cover** now has Sentinel-2 SCL download/QA/native-cell comparisons; **09 AOD** has public AERONET download and the approved 27.5 km circular daily comparison at 550 nm. **07 CH₄ and 08 CO₂** now have monthly GOSAT downloads and diagnostic comparisons; see [GOSAT methodology](docs/GOSAT.md). **06 Cloud** has hourly MSG downloads and diagnostic comparisons; see [Cloud methodology](docs/CLOUD.md). **04 Precipitation** has an initial hourly regional-gauge adapter with resumable MeteoHub extraction; see [Precipitation methodology](docs/PRECIPITATION.md). Initial live comparisons work; product 04 now uses user-selected positive-gauge-rainfall station-hours with the unchanged 20% threshold and separately records same-pixel gauge support for area-reference diagnostics. Delivery unit metadata remain unresolved.

**03 Solar Radiation** now defaults to the user-adopted ERA5 reference-only direct-normal comparisons and CDS downloads; see [ERA5 method and geometry limitation](docs/SOLAR_ERA5.md). CAMS BNI remains an optional supplementary cross-check.

Thermal and snow results are currently **DIAGNOSTIC**; operative circular AOD comparisons use **PROCESSED**. Neither status counts as accepted campaign acquisitions or establishes overall compliance. Solar ERA5 uses PROCESSED under the explicitly adopted reference-only method; the constant-DNI within-hour approximation and sensitivity estimates remain recorded. Operational KPI dates and geographic distribution are now reported separately from legacy reference-sample accounting; see [KPI counting](docs/KPI_COUNTING.md). The shipped campaign is **1 October–31 December 2026**. Thermal rRMSE uses the absolute mean paired reference temperature **in Celsius**; this convention is explicit and scale dependent.

## Quick start

Python **3.11 or 3.12** is tested. From a terminal:

```bash
git clone https://github.com/valentinopapangeok/operational-validation-IRIDE.git
cd operational-validation-IRIDE
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[scientific,dev]'
python tools/doctor.py
python -m unittest discover -s tests -v
python tools/smoke_test.py
iride-validate --status
iride-validate --report --open-report
```

The synthetic smoke test runs the actual thermal and solar adapters, collocation, metrics, plots and registry **without credentials or network access**. Its generated report is `validation/smoke/report/validation_report.html`; these are explicitly synthetic measurements.

Windows and MinIO installation instructions are in [Installation](docs/INSTALLATION.md). The repository includes the exact land and marine AOI geometries and extracted validation-plan requirements. No private production data, caches, local absolute paths or real credentials are needed to clone and run the tests.

## PyCharm: connect VPN and press Run

After installing dependencies and MinIO `mc`, place the supplied private credential files in `credentials/`, connect the VPN, and run root **`main.py` with no arguments**. It discovers every campaign delivery, downloads inputs for implemented adapters, refreshes needed references, validates, and rebuilds the report. Paths are resolved from the repository, independent of the IDE working directory. See [PyCharm guide](docs/PYCHARM.md).

```bash
python main.py
# Installed equivalent:
iride-validate --run
```

Product 04 uses the integrated targeted regional-gauge adapter; missing reference extracts remain pending. Cloud and monthly GOSAT comparisons are integrated. Solar, snow and AOD run automatically; AOD uses the approved 27.5 km circular method at 550 nm. An operationally successful run does not imply accepted validation samples.

## Run against production

Install MinIO **`mc`**, connect to the approved IRIDE network/VPN, and obtain read-only production access. Create the external credential file described in [Credentials](docs/CREDENTIALS.md); drop the privately supplied files into `credentials/bucket.env` and `credentials/downloaders.env` (automatically discovered, ignored by Git). Alternatively reuse an existing `iride-prod` MinIO alias.

```bash
# Read-only connectivity/inventory check; no asset downloads
iride-validate --inventory-only --product S5-02-02

# Latest production acquisition per product, followed by local validation
iride-validate --download-latest

# Search only: public Landsat catalogue, no production credentials needed
iride-validate --landsat-search --as-of 2026-10-09

# Download references and matching production dates; then compare
iride-validate --landsat --as-of 2026-10-09

# Modest initial reference-only trial; skip private production access
iride-validate --landsat --max-scenes 1 --skip-matching-deliveries

# Reuse local data and refresh comparisons without network downloads
iride-validate --product S5-02-02
```

`--product` restricts S5 downloads/comparisons; the Landsat reference search/cache is shared across thermal products. `--max-scenes` limits reference downloads, not the search or all matching S5 dates. No background scheduler is installed. Do not launch two processes against the same state directory.

## Guides

| Guide | Purpose |
|---|---|
| [Installation](docs/INSTALLATION.md) | Operating systems, Python environment, GIS libraries and MinIO |
| [Credentials](docs/CREDENTIALS.md) | Exact files/variables, precedence, network and permissions |
| [Runbook](docs/RUNBOOK.md) | Daily commands, outputs, retries, campaign changes and exit codes |
| [Configuration](docs/CONFIGURATION.md) | AOIs, manifest paths, scientific policies and reference settings |
| [Adding products](docs/ADDING_PRODUCTS.md) | Adapter contract, registration, evidence, metrics and tests |
| [Architecture](docs/ARCHITECTURE.md) | Registry states and integration contracts |
| [Snow methodology](docs/SNOW.md) | Sentinel-2 SCL mapping, QA and native-cell comparison |
| [AOD methodology](docs/AOD.md) | Wavelength, AERONET levels and station-day comparison |
| [Delivered support](docs/PRODUCT_SUPPORT.md) | Optional production QA/time/wavelength assets downloaded automatically |
| [Solar methodology](docs/SOLAR_CAMS.md) | Equivalent DNI/BNI cross-check and ADS access |
| [Landsat methodology](docs/LANDSAT.md) | Scaling, QA, spatial support, rRMSE and limitations |
| [Requirements](docs/REQUIREMENTS.md) | Imported workbook targets and sampling requirements |
| [Testing](docs/TESTING.md) | Offline checks, clean installs and optional integration tests |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Installation, credentials, VPN, availability and scientific states |
| [Contributing](CONTRIBUTING.md) | Development workflow and review expectations |

## Repository layout

```text
s5validation/       installed Python package, CLI and scientific adapters
config/             portable campaign defaults and extracted workbook provenance
aoi/                exact versioned land/marine GeoJSON geometries
docs/               operator and contributor guides
examples/           credential template and adapter skeleton
tools/              offline doctor, synthetic smoke test, workbook importer
tests/              network-free scientific and lifecycle tests
validation/         ignored local manifest, cache, database, results and reports
```

The original validation workbook is not distributed. `config/validation_plan_source.json` preserves its filename, SHA-256, exact requirement text and merged-cell addresses. Runtime folders are checked/created on every launch. Raw data, populated environment files and runtime outputs stay outside Git. Software licensing has not been assigned; repository access does not grant rights to redistribute underlying data.

Reference inputs are retained and verified for reuse across runs. See [reference cache retention](docs/REFERENCE_CACHE.md) before moving or cleaning a cache.

## Persistent reference cache

Downloaded scientific reference snapshots, checksum receipts and comparison evidence are retained under the configured workdir. Verified usable inputs are reused on later launches. No automatic cleanup removes the local reference cache. AERONET now also reuses verified available observations without HTTP downloads; missing quality levels can still be checked for newly published data. Set `aeronet.refresh_cached_references: true` only for an intentional source refresh; older raw snapshots remain retained.

For long asynchronous product 04 campaigns, [continue the cached campaign](docs/PRECIPITATION.md#continue-a-multi-date-campaign) with `python tools/continue_precipitation.py`. Explicitly authorized MeteoHub server-file archiving can recycle provider quota after successful local verification; this never deletes local reference data.

Hourly products **03/04/06** report **passing hours / evaluated hours**, with individual UTC-hour scores in `report/hourly_scores.csv` and campaign/monthly counts in `hourly_summary.csv`. Earlier daily aggregations for those hourly products are superseded. Each hour remains independent; AOD retains its approved daily method.

Product 04 now screens cached products for rain near its automatically catalogued gauge locations before requesting references. Downloads are scoped by regional network/hour, retain deterministic product-dry controls and reuse all existing data. The comparison remains per-hour and at the containing product pixel; see [product-first requests](docs/PRECIPITATION.md#product-first-regional-requests--operative-default).

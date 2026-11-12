# Product 06 — hourly cloud comparison

`main.py` automatically downloads campaign cloud products and MSG reference scans,
then runs `msg_cloud_hourly`. Product 04 uses the separate regional-gauge adapter. Run a bounded trial:

```bash
python main.py --product S5-02-06 --max-deliveries 1
# Local cached comparisons only, without network:
iride-validate --product S5-02-06
```

No arguments are needed when using PyCharm for the usual full campaign run. All
paths derive from the repository/configured workdir; folders are created as needed.
Install the scientific extras (`pip install -e '.[scientific,dev]'`), which include
EUMDAC and ecCodes. Recent ecCodes wheels include their native libraries on
supported platforms. A GRIB decoder installation error is an environment error,
not missing reference data. Verify the installation with `python -m eccodes selfcheck`.

## Credentials and cache

Use the existing ignored `credentials/downloaders.env` file, with
`EUMETSAT_CONSUMER_KEY` and `EUMETSAT_CONSUMER_SECRET`. These are Data Store API
credentials, not your account password. The existing external credential-file
option and environment-variable overrides also work. Production downloads use
the existing bucket file and VPN. No additional secrets file is required.

The downloader searches `EO:EUM:DAT:MSG:CLM` (MSG at 0°), scoped to the queued
products' UTC dates. It selects nominal scans at 00, 15, 30 and 45 minutes within
each production hour. Reprocessed duplicates at a timestamp use the last sorted
identifier and cannot inflate the scan count. GRIB timestamps must match the
requested scan. No neighbouring hour, RSS or Indian Ocean product is substituted.

Production transfers use up to four workers (`delivery.download_workers`, 1–8);
MSG downloads use two workers. Registry/index writes remain serial. Native scan
geolocation is reused only when the exact GRIB grid fingerprint and AOI bounds
match; every scan still supplies its own independently decoded classes.

Raw ZIP responses, their embedded GRIB payloads (read without archive extraction),
and AOI-scoped decoded native cells are retained under
`cache/reference/msg_cloud/YYYY-MM-DD/HHMM/`. Raw files and decoded files have
SHA-256 checksums. Verified cache is reused without authentication/network;
changes to the AOI or decoder rebuild decoded data from verified raw data.
Interrupted downloads remain unusable partial files and are retried. Missing scans
are searched again on later operational runs. Ordinary local/status/report runs
never trigger reference downloads. Asset transfers use a 15-second connection timeout, 90-second read timeout and
at most three attempts. One failed scan does not prevent other dates from being
downloaded; errors are recorded separately and retried on the next run. Decoder
fingerprints depend on decoding code, so transport-only changes retain verified
scientifically identical cached data. Provider errors are distinguished from a
successful catalogue query with no observations.

## Explicit first-version method

The production source creates an hourly binary 0/1 fusion from MTG masks acquired
within that UTC hour. It is not an instantaneous observation. This implementation
uses a declared same-hour MSG summary rather than pretending one scan represents
the entire hourly product:

1. MSG GRIB2 code table 4.217: 0 clear water and 1 clear land become clear=0;
   2 cloud becomes cloud=1. No data=3, missing=255 and unknown values are excluded.
   The decoder validates discipline/category/parameter (3/0/7).
2. At least 3 of the 4 nominal quarter-hour scans must be available. At each native
   MSG location, require at least 3 valid scan classifications, then calculate the
   arithmetic cloud frequency. Frequency ≥0.5 becomes cloudy; a two/two tie is
   therefore cloudy. The exact fraction and valid-scan count are exported.
3. Use one product nearest-neighbour sample at each native MSG centre inside the
   exact versioned Italy land AOI. Product nodata, nonfinite values and off-raster
   points are excluded. Unexpected valid classes produce an explicit error rather
   than an inferred conversion. Product 0=clear and 1=cloud are read as delivered.
4. Require at least 30 eligible pairs for whole-AOI/hour and independently for each
   sub-AOI/hour. North ≥44°N; Center 41.5–44°N; South <41.5°N. Every retained pair
   enters the confusion counts, including errors. F1 ≥0.8 is the thematic target.
5. Score F1 independently for every UTC production hour, whole AOI and each
   eligible sub-AOI. Report **passing hours / evaluated hours**. Never pool
   confusion counts across hours or replace them with daily F1. Exports are
   `report/hourly_scores.csv` and `hourly_summary.csv` (also JSON).
   All-clear comparisons with no positive predictions/reference have undefined
   F1 and do not become passes. Missing reference/QA support is unevaluated.

The above temporal and sampling settings are explicit defaults in `cloud`, not
requirements inferred from the workbook. Results stay **DIAGNOSTIC**, with no
accepted campaign samples. The workbook's 30 hourly productions remain hourly
sample requirements. User clarification on October 20 fixes current reporting to hourly outputs; overall campaign KPI aggregation remains unspecified by the workbook.

## Limits and evidence

MSG is coarser than MTG/product data. Native-centre sampling avoids inflating the
count with interpolated reference pixels, but does not average the full MSG
footprint. The arithmetic MSG hourly summary differs from production's MTG fusion
and scan cadence. There is no cloud-height/parallax correction, no asserted
reference independence from shared meteorological context, and no measured
positional-accuracy pass. The declared positional tolerance remains less than
product resolution, as agreed for the campaign.

Each revision/method result includes paired NPZ data (classes, native indices,
coordinates, reference cloud frequency and valid-scan counts), a confusion-matrix
plot and class maps, confusion metrics
for Italy and sub-AOIs, input hashes, source identifiers and limitations. Daily
CSV/JSON summaries are written next to the HTML report. A missing reference gives
PENDING_REFERENCE, insufficient paired support gives REJECTED_QA, and corrupt
cache/unexpected formats produce ERROR. Diagnostic results never enter the accepted
sample registry.

Sources: [EUMETSAT Cloud Mask guide](https://user.eumetsat.int/s3/eup-strapi-media/pdf_clm_pg_6b00d53e6b.pdf),
[cloud-mask code table](https://vocabulary-manager.eumetsat.int/vocabularies/GRIB/WMO/100/TABLE_CODE_FLAG/4.217),
[MSG CLM collection](https://api.eumetsat.int/data/browse/1.0.0/collections/EO%3AEUM%3ADAT%3AMSG%3ACLM?format=html),
[ecCodes Python decoding](https://confluence.ecmwf.int/pages/viewpage.action?pageId=589467243).

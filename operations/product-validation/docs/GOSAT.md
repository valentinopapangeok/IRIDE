# Monthly GOSAT validation: products 07 and 08

Running `main.py` from PyCharm automatically includes both products through the
`gosat_monthly` adapter. With no campaign deliveries, no GOSAT requests are made.
Ordinary local validation/status/report commands do not download references.
Missing references give PENDING_REFERENCE; insufficient Italy coverage gives
REJECTED_QA. Computed comparisons remain DIAGNOSTIC with no accepted samples.
No dates or results are fabricated when products are absent.

Place `NIES_USER` and `NIES_PASSWORD` in the ignored `credentials/downloaders.env`
(or the configured external downloader credential file). Existing shared
credential loading is reused. No additional credentials file is necessary.
NIES registration/access to GOSAT GDAS is required for uncached reference months.
Authentication errors and unexpected HTML responses are errors, not missing data.
A 404 leaves the month pending and is retried on the next operational run.

The provider downloads SWIRL3CH4 / SWIRL3CO2 V03.05 monthly tar archives. It retains
raw archives and checksum receipts under `cache/reference/gosat/{CH4,CO2}/YYYY-MM/`
in the configured workdir. Complete verified archives are reused; partial files
are never used. Folders are created automatically. Archives are read in memory
without extracting filenames supplied by the archive.

The implementation ports the input-availability repository's monthly validator:
- GOSAT fields Data/mixingRatio/XCH4 and XCO2; reference ppm to ppb ×1000 for CH4,
  ppm unchanged for CO2; product values assumed ppb and ppm respectively.
- North-up EPSG:4326 product rasters; other grids produce an explicit error.
- Product pixels averaged within native reference cells using spherical overlap
  areas. Finite unmasked product pixels and finite positive reference values only.
- No quality-mask value is assumed: `gosat.mask_value` defaults to null and this
  limitation is retained in provenance. Raw GOSAT mask values are exported.
- Partial product cell support is retained (`minimum_cell_coverage=0`); each
  matched cell exports its valid support fraction. Coarse references are not
  upsampled into independent observations.
- Equal weight per matched native reference cell. rRMSE = RMSE / absolute mean
  paired reference ×100; threshold 20%. Whole Italy and North/Center/South scores
  use all eligible pairs. Subarea assignment uses native cell centres and the
  approved 41.5°N/44°N latitude cuts.
- Italy coverage is the equal-area intersection of matched native reference cells
  with the AOI divided by total AOI area. The configured minimum is 20%. This is
  reference-cell coverage, not a claim that all product pixels inside are valid.

Reference month defaults to the delivery acquisition month, with explicit
`gosat.month_offset=0`. Before accepting real campaign results, verify month,
physical quantity, units and mask interpretation against the delivered XML and
GOSAT attributes. The legacy Utils next-month/fallback behaviour is not inherited.
Geographical distribution in at least two subareas is desirable and visible in
metrics, not an invented mandatory gate. Results represent monthly comparisons,
never daily passing counts. Paired CSV, JSON metrics, hashes and policy provenance
are written under revision- and method-specific results folders.

Optional live check once a product exists: `python main.py --product S5-02-07`
(or 08). Cached offline comparison uses `iride-validate --product S5-02-07`.

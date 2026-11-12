# No Regression

Local no-regression workspace for S5-02 products.

## Layout

- `V0_tiffs/`: current usable V0 raster references for no-regression comparisons.
- `V1_tiffs/`: V1 raster outputs to compare against V0.
- `validation_samples/`: validation sample ZIP exports. These are metadata/index packages only; they do not currently contain TIFF rasters, so they cannot be used directly as V0 input.
- `scripts/run_no_regression.py`: local no-regression comparison runner.
- `input_testDates/run_input_test_dates.py`: local input availability/download runner for the no-regression test dates.

## Run No Regression

```bash
/Volumes/Extreme/IRIDE/MKPL/Utils/.venv/bin/python \
  /Volumes/Extreme/IRIDE/MKPL/Utils/workflows/regression/no_regression/scripts/run_no_regression.py
```

The output CSV is written to:

```text
/Volumes/Extreme/IRIDE/MKPL/Utils/workflows/regression/no_regression/no_regression_results.csv
```

Products `05` and `06` use class mode. Product `04` is excluded. All other products use continuous mode.

## Run Input Test-Date Audit

```bash
/Volumes/Extreme/IRIDE/MKPL/Utils/.venv/bin/python \
  /Volumes/Extreme/IRIDE/MKPL/Utils/workflows/regression/no_regression/input_testDates/run_input_test_dates.py
```

The input audit writes results and downloads under:

```text
/Volumes/Extreme/IRIDE/MKPL/Utils/workflows/regression/no_regression/input_testDates/
```

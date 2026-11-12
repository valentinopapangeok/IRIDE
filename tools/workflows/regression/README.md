# Regression workflows

| Case | Entry point | Role |
| --- | --- | --- |
| `no_regression/` | `scripts/run_no_regression.py` | Cross-product V0/V1 baseline comparison |
| `no_regression/input_testDates/` | `run_input_test_dates.py` | Historical input-date investigation |
| `no_regression_04/` | `probe_mistral_old_product.py`, archive request/check scripts | Historical Mistral product 04 investigation |
| `no_regression_october_viirs/` | `compare_october.py` | October product comparisons |
| `01_noreg_investigation/` | Own README and notes | Product 01 DEV/UAT comparison case |

Lifecycle: retained scientific comparisons/investigations. Baselines, manifests,
results, downloads and legacy source context moved with each case. Config references
now point to `workflows/operations/input_availability/config.json`. Former flat
paths remain compatibility symlinks. No data downloads or baseline deletion were
performed. Product-specific conclusions remain in their original notes and reports.

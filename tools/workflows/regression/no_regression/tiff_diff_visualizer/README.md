# TIFF Diff Visualizer

Reusable local tool for comparing two single-band GeoTIFFs with the same no-regression logic used by the local S5-02 checks.

Outputs:

- `*_fail_mask.tif`: georeferenced binary mask where `1` means failing pixel.
- `*_status_map.tif`: georeferenced classified map for QGIS.
- `*_summary.csv` and `*_summary.json`: pass percentage and pixel counts.

`*_status_map.tif` classes:

- `0`: invalid/no-data in both rasters.
- `1`: valid AOI pixels that pass.
- `2`: valid overlap pixels that fail.
- `3`: valid only in reference/V0.
- `4`: valid only in test/V1.

Create the local venv:

```bash
cd /Volumes/Extreme/IRIDE/MKPL/Utils/workflows/regression/no_regression/tiff_diff_visualizer
./setup_venv.sh
```

Example, continuous product:

```bash
.venv/bin/python compare_tiffs_visual.py \
  --reference ../V0_tiffs/IRIDE-S_S5-02-01_20220116_V0.tif \
  --test ../V1_tiffs/IRIDE-S_S5-02-01_20220116_V1.tif \
  --mode continuous \
  --out-dir outputs \
  --name S5-02-01_20220116
```

Example, class product:

```bash
.venv/bin/python compare_tiffs_visual.py \
  --reference ../V0_tiffs/IRIDE-S_S5-02-06_2025032312_V0.tif \
  --test ../V1_tiffs/IRIDE-S_S5-02-06_2025032312_V1.tif \
  --mode class \
  --out-dir outputs \
  --name S5-02-06_2025032312
```

Add `--png` if a quick PNG preview is also needed.

# S5-02-01 DEV vs UAT findings

Test date: `20220116`

## No-regression against canonical V0

| Candidate | Status | Pass % | V0 valid | V1 valid | Overlap valid | Significant pixels |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| DEV | PASS | 99.89 | 267,702 | 231,333 | 231,307 | 249 |
| UAT | FAIL | 91.20 | 267,702 | 268,682 | 267,119 | 23,508 |

## DEV vs UAT

- DEV and UAT are identical on all pixels where DEV is valid.
- UAT has `37,349` extra valid pixels compared to DEV.
- `35,812` of those extra UAT pixels overlap valid V0 pixels.
- `23,259` of those extra UAT pixels are significant no-regression differences against V0.
- If UAT is restricted to the DEV valid footprint, it passes at `99.892%`.

## Metadata/input difference

DEV input XML lists:

- Sentinel-3 SLSTR L2 LST, 5 acquisitions
- MODIS, 4 tiles
- GCOM-C SGLI L3 LST, 1 acquisition

UAT input XML lists the same inputs plus:

- `[IN-S5-02-20] C3S ERA5- ERA5 & ERA5-LAND/SKIN-TEMPERATURE; 16/1/2022T10:00:00;11000m`

## Interpretation

The UAT failure is driven by expanded valid coverage, not changed values on the shared footprint. The likely cause is the extra ERA5/ERA5-LAND skin-temperature input in UAT, which fills pixels that remain invalid in DEV. Those additional pixels are then compared against valid V0 pixels and account for nearly all significant no-regression failures.

## V0 code vs MKPL code

Legacy V0 code was copied from `IRIDE-master/SVC/flows/flow_OU_S5_02_01` into:

- `legacy_v0_code/IRIDE-master/SVC/flows/flow_OU_S5_02_01`

The data-fusion priority is conceptually the same in legacy V0 and MKPL:

1. Sentinel-3
2. MODIS
3. GCOM-C
4. ERA5-LAND
5. ERA5

The important difference is in ERA5-LAND preprocessing:

- Legacy V0 converts ERA5-LAND into `era5land_folder/era5land.tif`, but `resample_era5land_to_s3(product_folder)` looks for `product_folder/era5land.tif`. This means the ERA5-LAND resampling branch likely skips with `FileNotFoundError`, unless an `era5land.tif` was already present in `product_folder` from elsewhere.
- MKPL converts ERA5-LAND into `era5land_folder/era5land.tif`, then explicitly calls `resample_era5land_to_s3(era5land_tiff_path, product_folder)`, creating `product_folder/era5land.tif`.

Therefore, even when both V0 and UAT XMLs contain the ERA5/ERA5-LAND metadata line, the actual data participating in fusion may differ:

- legacy V0 likely used ERA5 as the final fallback, and may not have actually used ERA5-LAND because of the folder/path mismatch;
- MKPL UAT can actually generate and use `era5land.tif` before `era5.tif` in the fusion hierarchy.

This is a plausible reason why UAT has ERA5/ERA5-LAND listed like V0 but still fails no-regression: the fallback source or preprocessing grid is not necessarily the same.

## ERA5 vs ERA5-LAND culprit check

The input-audit files already contained the model inputs for the test date:

- `input_testDates/runtime_downloads/01/2022-01-16/era5/era5_skin_temperature_2022-01-16.nc`
- `input_testDates/runtime_downloads/01/2022-01-16/era5_land/era5_land_skin_temperature_2022-01-16.nc`

I sampled both ERA5 and ERA5-LAND on the product grid and compared them over the suspicious pixels:

- suspicious set: UAT-only valid pixels that fail no-regression vs V0
- count: `23,259` pixels

Key result:

| Target | Closest source on suspicious pixels | Pixel count |
| --- | --- | ---: |
| UAT | ERA5-LAND nearest/bilinear | 17,310 |
| UAT | ERA5 nearest/bilinear | 5,949 |
| V0 | ERA5 bilinear | 19,556 |
| V0 | ERA5/ERA5-LAND other variants | 3,703 |

Median absolute differences on suspicious pixels:

| Source sampled on product grid | UAT median abs diff | V0 median abs diff |
| --- | ---: | ---: |
| ERA5-LAND bilinear | 0.552 | 1.009 |
| ERA5 bilinear | 1.121 | 0.010 |

Interpretation:

- V0 suspicious-pixel values are effectively aligned with ERA5 single-level, especially the bilinear sampled ERA5 field.
- UAT suspicious-pixel values are much more aligned with ERA5-LAND than with ERA5.
- This supports the code-level finding: legacy V0 likely did not use ERA5-LAND as an actual filler despite listing ERA5/ERA5-LAND in metadata, while MKPL UAT does use ERA5-LAND before ERA5.

Detailed outputs:

- `outputs/era5_culprit/era5_source_comparison.csv`
- `outputs/era5_culprit/era5_on_product_grid.tif`
- `outputs/era5_culprit/era5land_on_product_grid.tif`

## QGIS masks

- `outputs/dev_vs_uat/uat_extra_valid_pixels_vs_dev.tif`
- `outputs/dev_vs_uat/uat_no_reg_fail_pixels_vs_v0.tif`
- `outputs/dev_vs_uat/uat_extra_valid_and_failing_vs_v0.tif`
- `outputs/dev_vs_uat/dev_uat_shared_valid_pixels.tif`

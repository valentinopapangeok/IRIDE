# S5-02-01 footprint-distance experiment

Status: diagnostic and incomplete for the historical 24,014-cell population.
No production repository, acceptance threshold, delivery result, or existing
evidence file was changed.

## Result

The proposed metric is scientifically interpretable as a source-to-final-cell
processing diagnostic, but it is not preferable as a replacement for the
existing centre-distance requirement. It assigns exactly zero displacement to
every native coordinate inside a delivered cell, including a coordinate that
is near one edge or that reached the cell through an imprecise assignment. It
therefore measures containment, not sub-cell positional accuracy, and can be
artificially forgiving at the same time that it hides assignment uncertainty.

The historical centre-distance result remains the only directly comparable
measured result: 17,725/24,014 = 73.8111% below 1,000 m, maximum 1,698.1854 m,
so the strict >90% rule fails on that diagnostic subset. The new replay did not
reproduce the exact 24,014-cell correspondence population: full production
polygon-touch reconstruction yielded 49,482 compatible cells. A primary-cell
simplification yielded 33,423. These populations are not presented as
comparable results for contractual acceptance.

For the requested exploratory run on all 49,482 reconstructed cells, both
methods used the same contributor correspondences and covered 18.2222% of the
271,548 valid delivered pixels:

| Method | P50 | P90 | P95 | Mean | RMSE | Max | <1,000 m | Result |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Centre distance | 713.41 m | 1,122.42 m | 1,258.38 m | 704.32 m | 769.66 m | 1,812.01 m | 83.7557% (41,444/49,482) | FAIL |
| Footprint distance | 60.73 m | 434.23 m | 594.71 m | 139.56 m | 233.96 m | 1,160.01 m | 99.9939% (49,479/49,482) | PASS* |

The footprint method classified 20,522 cells (41.4737%) as inside their
delivered footprint and therefore assigned them zero displacement. `PASS*` is
only the arithmetic result on this exploratory population; it is not
comparable to the historical 24,014-cell result and is not a contractual
acceptance result.

## Production verification

The audited production code is in `svc_s5-02-01`:

- `src/steps/ingestion/data_ingestion.py:65-69` restricts Sentinel-3 LST to
  08:00–12:30 UTC.
- `src/steps/pre_processing/sentinel3_pre_processing.py:102-186` reads native
  geodetic/LST/flags arrays, subtracts 273.15 K, creates an axis-aligned
  `STEP=0.011131580833333335°` polygon with the native coordinate as its upper
  left corner, and burns with `all_touched=True`.
- `src/steps/pre_processing/eo_derived_data_pre_processing_fnc.py:24-78`
  sorts S3A before S3B by time and mosaics with rasterio's default precedence.
- `src/steps/pre_processing/eo_derived_data_pre_processing_fnc.py:359-415`
  applies the October `-15..45 °C` outlier bounds.
- `src/steps/processing/data_fusion.py:64-94` fills Sentinel gaps from MODIS,
  GCOM-C, ERA5-LAND and ERA5 on the same Sentinel reference grid; it does not
  preserve a final contributor map.

The delivered GeoTIFF transform is used directly by the reusable metric. Its
cell footprint is the affine-transformed quadrilateral in the GeoTIFF CRS,
with geodesic WGS84 distance to the boundary and zero for covered points.

## Synthetic geometry check

For a 1° cell, a native point at the cell corner gives centre distance about
70 km but footprint distance 0 m. An offset point outside the cell gets the
shortest geodesic distance to the boundary. A point in an adjacent cell is not
treated as inside the assigned cell. This demonstrates the metric's intended
geometry and its containment-forgiveness limitation without treating pixels as
independent acquisitions.

## Reproduction

The implementation is [footprint_experiment.py](footprint_experiment.py). It
is read-only with respect to inputs and requires explicit paths:

```text
python investigations/positional_footprint_20261116/footprint_experiment.py \
  --input-dir <receipted-SEN3-directory> \
  --final-tif <delivery-revision-matched-tif> \
  --output-dir <dedicated-workdir>/positional_footprint_20261116
```

It fails closed unless exactly 24,014 cells are reproduced. The retained
receipts and historical replay should be reconciled before any numerical
footprint result is accepted.

## Recommendation

Keep centre distance and footprint distance as separate diagnostics. Do not
use footprint containment as the contractual positional KPI unless the
requirement is explicitly redefined to measure cell containment and an
independent geolocation reference plus exact contributor lineage are added.
For the current IRIDE requirement, retain the strict centre-distance result;
the full delivery remains `UNASSESSED` where fallback contributor lineage is
missing.

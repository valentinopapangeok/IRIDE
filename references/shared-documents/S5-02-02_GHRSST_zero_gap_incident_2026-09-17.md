# S5-02-02 GHRSST zero-gap incident

Date: 2026-09-17

## Observed issue

The SST delivery for 2026-09-13 contained an internal NoData patch around
9.5 E, 43.5 N, north of Corsica. The patch was inside the configured sea AOI,
not in the land/outside-AOI mask.

## Root cause

The production-time VIIRS/GHRSST granule had no observations around the patch.
GHRSST preprocessing rasterized uncovered cells with Rasterio's default fill of
zero and did not declare an output NoData value. Reprojection therefore also
expanded uncovered parts of the sparse swath as zero on the Sentinel reference
grid.

Fusion considered zero a valid value because source replacement only tested for
NaN. The zero consequently blocked the later GCOM-C and CMEMS fallback sources.
The old final clipping step then converted zero to NoData, exposing the hole.

## Audit evidence

- Exact GHRSST input: `20260913105000-STAR-L2P_GHRSST-SSTsubskin-VIIRS_NPP-ACSPO_V2.80-v02.0-fv01.0.nc`.
- No GHRSST observations were present around 9.5 E, 43.5 N.
- The clear-sky GHRSST swath started at approximately 10.56 E.
- CMEMS was valid at the patch and reported approximately 26.65 C.
- The corrected test delivery interpolated approximately 26.60 C at the same location.
- The corrected delivery contained no NoData inside the AOI and no valid pixels outside it.

## Minimal remediation

1. Rasterize uncovered GHRSST cells as `NaN` and declare `nodata=np.nan` in the output profile.
2. Return the actual ingestion completeness token rather than a constant `True`, restoring the intended interpolation gate.

With all four inputs available, as in the investigated run, interpolation remains enabled.
GHRSST gaps can now fall through to GCOM-C or CMEMS before residual interpolation.
The resulting raster should remain continuous, but gap pixels may change slightly because
they are sourced from the intended fallback rather than distant nearest-neighbour values.

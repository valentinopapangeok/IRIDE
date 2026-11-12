import rasterio
import numpy as np
import matplotlib.pyplot as plt

# Paths to your TIFFs
tif1 = "/Users/valentinopapandrea/Downloads/IRIDE-S_S5-02-08_202407_V0.tif"
tif2 = "/Users/valentinopapandrea/Desktop/University/GeoK/tif_comparison/08/IRIDE-S_S5-02-08_20240701_V0/IRIDE-S_S5-02-08_202407_V0.tif"

nodata_value = -999
tolerance_fraction = 0.05  # 5%
pass_threshold = 0.95       # 95%

# Read TIFFs
with rasterio.open(tif1) as src1, rasterio.open(tif2) as src2:
    if src1.shape != src2.shape:
        raise ValueError("Different dimensions — resample first!")

    data1 = src1.read(1).astype(float)
    data2 = src2.read(1).astype(float)

# Mask valid pixels
mask_valid = (data1 != nodata_value) & (data2 != nodata_value)
data1_clipped = np.where(mask_valid, data1, np.nan)
data2_clipped = np.where(mask_valid, data2, np.nan)

# Compute difference according to the formula
diff = np.where(
    (~np.isnan(data1_clipped)) & (~np.isnan(data2_clipped)) &
    (np.abs(data2_clipped - data1_clipped) > tolerance_fraction * data1_clipped),
    data2_clipped - data1_clipped,
    np.nan
)

# --- Corrected statistics ---
total_valid = np.sum(~np.isnan(data1_clipped))
pixels_exceeding_tolerance = np.sum(~np.isnan(diff))
pixels_within_tolerance = total_valid - pixels_exceeding_tolerance

agreement_fraction = pixels_within_tolerance / total_valid if total_valid > 0 else np.nan

print(f"Agreement within 5% tolerance: {agreement_fraction*100:.2f}%")
print("Test PASS ✅" if agreement_fraction >= pass_threshold else "Test FAIL ❌")

import matplotlib.pyplot as plt
import numpy as np

# diff already contains only differences > 5%, NaN elsewhere
plt.figure(figsize=(10, 8))
plt.imshow(diff, cmap='bwr', vmin=-np.nanmax(np.abs(diff)), vmax=np.nanmax(np.abs(diff)))
plt.colorbar(label='Difference (data2 - data1)')
plt.title('Pixel-wise differences exceeding 5%')
plt.axis('off')
plt.show()

# Optional: statistics of differences
max_diff = np.nanmax(diff)
min_diff = np.nanmin(diff)
mean_diff = np.nanmean(diff)

print(f"Max difference (beyond 5%): {max_diff:.3f}")
print(f"Min difference (beyond 5%): {min_diff:.3f}")
print(f"Mean difference (beyond 5%): {mean_diff:.3f}")

# Maximum and minimum
max_val1 = np.nanmax(data1_clipped)
min_val1 = np.nanmin(data1_clipped)
max_val2 = np.nanmax(data2_clipped)
min_val2 = np.nanmin(data2_clipped)

print(f"Maximum pixel value: {max_val1}")
print(f"Minimum pixel value: {min_val1}")
print(f"Maximum pixel value: {max_val2}")
print(f"Minimum pixel value: {min_val2}")
import rasterio
import numpy as np
from rasterio.windows import from_bounds

def compare_tiffs(tiff1_path, tiff2_path, nodata_value=-999):
    # Open first raster
    with rasterio.open(tiff1_path) as src1:
        arr1 = src1.read(1)
        bounds1 = src1.bounds
        transform1 = src1.transform

    # Open second raster
    with rasterio.open(tiff2_path) as src2:
        arr2 = src2.read(1)
        bounds2 = src2.bounds
        transform2 = src2.transform

    # Compute overlapping bounds
    overlap_left = max(bounds1.left, bounds2.left)
    overlap_bottom = max(bounds1.bottom, bounds2.bottom)
    overlap_right = min(bounds1.right, bounds2.right)
    overlap_top = min(bounds1.top, bounds2.top)

    # Check if overlap exists
    if overlap_left >= overlap_right or overlap_bottom >= overlap_top:
        raise ValueError("No overlapping area between the two TIFFs.")

    # Create windows for both rasters
    window1 = from_bounds(overlap_left, overlap_bottom, overlap_right, overlap_top, transform1)
    window2 = from_bounds(overlap_left, overlap_bottom, overlap_right, overlap_top, transform2)

    # Read overlapping areas
    with rasterio.open(tiff1_path) as src1:
        arr1_overlap = src1.read(1, window=window1)

    with rasterio.open(tiff2_path) as src2:
        arr2_overlap = src2.read(1, window=window2)

    # Crop to the same shape (just in case)
    min_rows = min(arr1_overlap.shape[0], arr2_overlap.shape[0])
    min_cols = min(arr1_overlap.shape[1], arr2_overlap.shape[1])
    arr1_overlap = arr1_overlap[:min_rows, :min_cols]
    arr2_overlap = arr2_overlap[:min_rows, :min_cols]

    total_pixels = min_rows * min_cols

    # Create mask for valid pixels (exclude nodata)
    valid_mask = (arr1_overlap != nodata_value) & (arr2_overlap != nodata_value)

    matches = np.sum((arr1_overlap == arr2_overlap) & valid_mask)
    mismatches = np.sum((arr1_overlap != arr2_overlap) & valid_mask)
    total_valid = np.sum(valid_mask)

    # Number of excluded pixels
    excluded_pixels = total_pixels - total_valid

    # Percentage of matching pixels among valid pixels
    matching_percentage = (matches / total_valid * 100) if total_valid > 0 else 0

    # Create the difference array
    diff = np.full(arr1_overlap.shape, nodata_value, dtype=np.int16)
    diff[valid_mask] = (arr1_overlap[valid_mask] != arr2_overlap[valid_mask]).astype(np.int16)

    return {
        "matches": matches,
        "mismatches": mismatches,
        "total_valid_pixels": total_valid,
        "excluded_pixels": excluded_pixels,
        "matching_percentage": matching_percentage,
        "difference_array": diff,
    }

# Example usage
if __name__ == "__main__":
    tiff1 = "/Users/valentinopapandrea/Desktop/University/GeoK/tif_comparison/06/YEAR=2025/MONTH=03/DAY=23/IRIDE-S_S5-02-06_2025032312_V0.tif"
    tiff2 = "/Users/valentinopapandrea/Desktop/University/GeoK/tif_comparison/06/IRIDE-S_S5-02-06_2025032312_V0.tif"

    result = compare_tiffs(tiff1, tiff2, nodata_value=-999)

    print(f"Total valid pixels compared: {result['total_valid_pixels']}")
    print(f"Matching pixels: {result['matches']}")
    print(f"Mismatched pixels: {result['mismatches']}")
    print(f"Excluded pixels: {result['excluded_pixels']}")
    print(f"Percentage of matching pixels: {result['matching_percentage']:.2f}%")


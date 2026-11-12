import rasterio
import cv2
import numpy as np
from pathlib import Path

# --- CONFIGURATION ---
BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "IRIDE-S_S5-02-09_20241106_V0.tif"
OUTPUT_FILE = "final_textured_output.tif"

# 1. BLUR STRENGTH (The "Melter")
# Keep this high (51 or even 71) to ensure blocks are destroyed.
KERNEL_SIZE = (51, 51)

# 2. TEXTURE STRENGTH (The "Granularity" slider)
# How much of the original raw pixel detail should we mix back in?
# 0.0 = 100% Smooth (Blurry)
# 0.3 = 30% Raw / 70% Smooth (Recommended start)
# 0.5 = 50% Raw / 50% Smooth
TEXTURE_STRENGTH = 0.30


def smooth_with_texture():
    """
        Processes a single-band satellite raster to remove low-resolution block artifacts
        while preserving high-frequency texture and dynamic range.

        The function performs a three-stage pipeline:
        1. **Structural Smoothing:** Applies a large Gaussian Blur to "melt" artificial
           pixel blocks caused by low-resolution data sources.
        2. **Range Recovery:** Rescales the smoothed data to match the minimum and
           maximum values of the original input, preventing data dilution.
        3. **Texture Blending:** Mixes the original raw data back into the smoothed
           result at a defined ratio to recover fine-grain granularity.

        Args:
            input_path (str): Path to the source GeoTIFF file. Must be single-band.
            output_path (str): Path where the processed GeoTIFF will be saved.
            kernel_size (tuple of int, optional): The size of the Gaussian kernel
                (width, height). Must be odd integers (e.g., (31, 31) or (51, 51)).
                Larger values remove larger blocks but may blur genuine features.
                Defaults to (51, 51).
            texture_strength (float, optional): A factor between 0.0 and 1.0 controlling
                how much original detail is retained.
                - 0.0: Output is 100% smooth (blurred).
                - 0.3: Output is 70% smooth base + 30% original grain (Recommended).
                - 1.0: Output is identical to input (no smoothing).
                Defaults to 0.30.

        Returns:
            None: The output is written directly to disk at `output_path`.

        Raises:
            FileNotFoundError: If `input_path` does not exist.
            rasterio.errors.RasterioIOError: If the input file is not a valid raster.

        """
    print(f"Opening {INPUT_FILE}...")

    with rasterio.open(INPUT_FILE) as src:
        img = src.read(1)
        profile = src.profile
        nodata_val = src.nodata
        if nodata_val is None: nodata_val = -9999

        # Create valid mask
        if np.isnan(nodata_val):
            valid_mask = ~np.isnan(img)
        else:
            valid_mask = (img != nodata_val) & ~np.isnan(img)

        # PREPARE DATA
        img_filled = img.copy()
        median_val = np.nanmedian(img[valid_mask])
        img_filled[~valid_mask] = median_val
        img_filled = img_filled.astype(np.float32)

        # --- STEP 1: CREATE THE SMOOTH BASE ---
        print(f"Melting blocks with Kernel {KERNEL_SIZE}...")
        base_smooth = cv2.GaussianBlur(img_filled, KERNEL_SIZE, 0)

        # RESTORE RANGE (Contrast Fix)
        # We stretch the smooth base so it hits the true min/max of the original
        orig_min = np.nanmin(img[valid_mask])
        orig_max = np.nanmax(img[valid_mask])

        smooth_min = np.min(base_smooth[valid_mask])
        smooth_max = np.max(base_smooth[valid_mask])

        scale = (orig_max - orig_min) / (smooth_max - smooth_min)
        base_restored = (base_smooth - smooth_min) * scale + orig_min
        base_restored = np.clip(base_restored, orig_min, orig_max)

        # --- STEP 2: BLEND BACK TEXTURE ---
        print(f"blending {TEXTURE_STRENGTH * 100}% of original granularity...")

        # Formula: Final = (Original * Strength) + (SmoothBase * (1 - Strength))
        # Note: We use img_filled for the calculation to avoid NaNs messing up the math
        final_blend = (img_filled * TEXTURE_STRENGTH) + (base_restored * (1.0 - TEXTURE_STRENGTH))

        # --- STEP 3: SAVE ---
        # Apply the NoData mask again
        final_output = np.where(valid_mask, final_blend, nodata_val)
        profile.update(dtype=rasterio.float32, nodata=nodata_val)

        with rasterio.open(OUTPUT_FILE, 'w', **profile) as dst:
            dst.write(final_output.astype(rasterio.float32), 1)

    print(f"Done! Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    smooth_with_texture()

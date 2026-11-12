import rasterio
from rasterio.coords import BoundingBox


def compare_tiffs(path1, path2):
    with rasterio.open(path1) as src1, rasterio.open(path2) as src2:
        # Get metadata
        t1, t2 = src1.transform, src2.transform
        meta1, meta2 = src1.meta, src2.meta

        print(f"--- Comparison: {src1.name} vs {src2.name} ---")

        # 1. Check CRS (Coordinate Reference System)
        if src1.crs != src2.crs:
            print(f"⚠️  WARNING: CRS Mismatch! {src1.crs} vs {src2.crs}")
            print("Spatial comparisons may be invalid until reprojected.")

        # 2. Compare Resolution (Pixel Size)
        # transform[0] is X scale, transform[4] is Y scale
        res1 = (t1[0], abs(t1[4]))
        res2 = (t2[0], abs(t2[4]))

        print(f"Resolution 1: {res1[0]:.6f} x {res1[1]:.6f}")
        print(f"Resolution 2: {res2[0]:.6f} x {res2[1]:.6f}")

        # 3. Calculate the Grid Offset (Sub-pixel shift)
        # This tells us if the pixels 'corners' line up
        off_x = (t2[2] - t1[2]) / t1[0]
        off_y = (t2[5] - t1[5]) / t1[4]

        print(f"\n--- Grid Alignment ---")
        print(f"X Offset: {off_x:.3f} pixels")
        print(f"Y Offset: {off_y:.3f} pixels")

        if abs(off_x % 1) > 0.001 or abs(off_y % 1) > 0.001:
            print("Result: Pixels are NOT aligned. A simple crop won't work; you must resample.")
        else:
            print("Result: Pixels are aligned. You can match these by simple padding/cropping.")

# Usage
compare_tiffs('/Users/valentinopapandrea/Desktop/University/IRIDE/Temp/IRIDE-S_S5-02-07_202502_V0.tif', '/Users/valentinopapandrea/Desktop/University/IRIDE/Temp/IRIDE-S_S5-02-08_202408_V0.tif')

import rasterio
from rasterio.warp import reproject, Resampling


def align_and_verify(p1_path, p2_template_path, output_path):
    # 1. Open the Template to get the target grid
    with rasterio.open(p2_template_path) as template:
        dst_crs = template.crs
        dst_transform = template.transform
        dst_width = template.width
        dst_height = template.height
        dst_kwargs = template.meta.copy()

        print(f"--- TARGET TEMPLATE (from {template.name.split('/')[-1]}) ---")
        print(f"Target Resolution: {dst_transform[0]:.6f} x {abs(dst_transform[4]):.6f}")
        print(f"Target Origin:     {dst_transform[2]:.6f}, {dst_transform[5]:.6f}")
        print(f"Target Dimensions: {dst_width} x {dst_height}\n")

    # 2. Perform the Reprojection
    with rasterio.open(p1_path) as src:
        dst_kwargs.update({
            'crs': dst_crs,
            'transform': dst_transform,
            'width': dst_width,
            'height': dst_height,
            'nodata': -999,
            'dtype': 'float32'
        })

        with rasterio.open(output_path, 'w', **dst_kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=dst_transform,
                    dst_crs=dst_crs,
                    resampling=Resampling.bilinear
                )

    # 3. VERIFICATION PRINTS for the new file
    with rasterio.open(output_path) as new_src:
        t = new_src.transform
        print(f"--- NEW ALIGNED FILE ({output_path.split('/')[-1]}) ---")
        print(f"New Resolution:    {t[0]:.6f} x {abs(t[4]):.6f}")
        print(f"New Origin:        {t[2]:.6f}, {t[5]:.6f}")
        print(f"New Dimensions:    {new_src.width} x {new_src.height}")

        # Final confirmation check
        if t[0] == dst_transform[0] and t[2] == dst_transform[2]:
            print("\n✅ SUCCESS: The files are now perfectly aligned on the same grid.")
        else:
            print("\n❌ ERROR: There is still a mismatch in the alignment.")


# Execution
p1 = '/Users/valentinopapandrea/Desktop/University/IRIDE/Temp/IRIDE-S_S5-02-07_202502_V0.tif'
p2 = '/Users/valentinopapandrea/Desktop/University/IRIDE/Temp/IRIDE-S_S5-02-08_202408_V0.tif'
out = '/Users/valentinopapandrea/Desktop/University/IRIDE/Temp/ALIGNED_S5-02-07.tif'

align_and_verify(p1, p2, out)
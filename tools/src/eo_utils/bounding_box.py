import rasterio

def get_tif_bbox(tif_path):
    """
    Extract bounding box (xmin, ymin, xmax, ymax) from a GeoTIFF,
    rounded to 2 decimals.

    Parameters
    ----------
    tif_path : str
        Path to the input .tif file

    Returns
    -------
    tuple
        (xmin, ymin, xmax, ymax) in the file's coordinate reference system,
        rounded to 2 decimals
    """
    with rasterio.open(tif_path) as src:
        bounds = src.bounds
        return (
            round(bounds.left, 2),
            round(bounds.bottom, 2),
            round(bounds.right, 2),
            round(bounds.top, 2),
        )

if __name__ == "__main__":
    tif_path = "/Users/valentinopapandrea/Desktop/University/GeoK/tif_comparison/02/IRIDE-S_S5-02-02_20250529_V0.tif"
    bbox = get_tif_bbox(tif_path)
    print("Bounding box:", bbox)

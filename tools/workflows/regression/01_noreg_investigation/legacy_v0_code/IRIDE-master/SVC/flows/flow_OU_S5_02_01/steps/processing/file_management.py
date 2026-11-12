import logging
import os
import geopandas as gpd


def create_folder_structure(base_path):
    folders = [
        "sentinel",
        "sentinel_processing",
        "sentinel_mosaico",
        "modis",
        "modis_processing",
        "modis_QA",
        "gcom",
        "era5land",
        "prodotti",
        "era5",
        "ritagli",
        "ritagli_reprojected",
        "finale",
        "txt",
    ]
    for folder in folders:
        folder_path = os.path.join(base_path, folder)
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
    return folders


def get_boundaries_from_shapefile(shapefile_path: str) -> tuple:
    """
    Extracts the bounding box coordinates (west, south, east, north) from a shapefile.

    Parameters:
    - shapefile_path (str): The file path to the shapefile.

    Returns:
    tuple: A tuple containing the bounding box coordinates in the order (west, south, east, north).

    Example:
    >>> get_boundaries_from_shapefile('path/to/shapefile.shp')
    (-180.0, -90.0, 180.0, 90.0)
    """
    gdf = gpd.read_file(shapefile_path)
    # Getting the bounding box from the GeoDataFrame
    bounds = gdf.total_bounds

    # Extracting coordinates from the bounding box
    west_lon = bounds[0]
    south_lat = bounds[1]
    east_lon = bounds[2]
    north_lat = bounds[3]

    return west_lon, south_lat, east_lon, north_lat


def concatenate_text_files(input_folder, output_folder, output_filename):
    # Ensure the output folder exists
    os.makedirs(output_folder, exist_ok=True)

    # List all text files in the input folder and sort them based on modification time
    txt_files = [
        os.path.join(input_folder, file)
        for file in os.listdir(input_folder)
        if file.endswith(".txt")
    ]
    txt_files.sort(key=os.path.getmtime)

    # Create an empty string to store concatenated content
    concatenated_content = ""
    # Loop through all text files in the input folder
    for txt_file in txt_files:
        with open(txt_file, "r") as file:
            # Read lines, strip whitespace, and filter out empty lines
            lines = [line.strip() for line in file.readlines() if line.strip()]
            if lines:
                concatenated_content += (
                    "\n".join(lines) + "\n"
                )  # Ensure newlines between files

    # Write the concatenated content to the output text file
    output_txt_path = os.path.join(output_folder, output_filename)
    with open(output_txt_path, "w") as file:
        file.write(concatenated_content.strip() + "\n")  # Remove trailing newlines

    logging.info(
        f"All text files in the folder have been concatenated in order of production and saved to: {output_txt_path}"
    )
    return True

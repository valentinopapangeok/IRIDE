import logging
import os

def product_validation_check(folder_path: str) -> bool:
    """
    Checks that the given folder contains exactly one .tiff file and one .xml file.
    Also verifies that the .xml file does not contain the strings "void" or "Not Applicable".

    Args:
        folder_path (str): Path to the folder to check.

    Returns:
        bool: True if the folder meets the conditions, False otherwise.
    """
    logging.info(f"Checking product validation -> folder_path: {folder_path}")
    if not os.path.isdir(folder_path):
        logging.error(f"Error: {folder_path} is not a valid directory.")
        return False

    tiff_files = []
    xml_files = []

    for file in os.listdir(folder_path):
        print(file)
        if file.endswith(".tif"):
            tiff_files.append(file)
        elif file.endswith(".xml"):
            xml_files.append(file)

    # Ensure there is exactly one .tiff and one .xml file
    if len(tiff_files) != 1 or len(xml_files) != 1:
        logging.error("Error: The folder must contain exactly one .tiff file and one .xml file.")
        return False

    # Read the XML file and check its contents
    xml_path = os.path.join(folder_path, xml_files[0])
    try:
        with open(xml_path, "r", encoding="utf-8") as xml_file:
            xml_content = xml_file.read()
            if "void" in xml_content or "Not Applicable" in xml_content:
                logging.error("Error: The XML file contains 'void' or 'Not Applicable'.")
                return False
    except Exception as e:
        logging.error(f"Error reading XML file: {e}")
        return False

    return True  # Folder meets all conditions
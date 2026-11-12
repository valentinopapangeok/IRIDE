import os
import shutil
from modis_tools.auth import ModisSession
from modis_tools.granule_handler import GranuleHandler
from modis_tools.resources import CollectionApi, GranuleApi

def download_modis_data(
    username, password, output_folder, start_date, end_date, bounding_box
):
    try:
        # Authenticate a session
        session = ModisSession(username=username, password=password)

        # Query the MODIS catalog for collections
        collection_client = CollectionApi(session=session)
        collections = collection_client.query(short_name="MOD11A1", version="061")

        # Query the selected collection for granules
        granule_client = GranuleApi.from_collection(collections[0], session=session)

        # Query granules based on date and bounding box
        granules = granule_client.query(
            start_date=start_date, end_date=end_date, bounding_box=bounding_box
        )

        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        # Download the granules
        downloaded_files = GranuleHandler.download_from_granules(granules, session)

        # Move the downloaded files to the specified output folder
        for downloaded_file in downloaded_files:
            destination_path = os.path.join(
                output_folder, os.path.basename(downloaded_file)
            )
            shutil.move(downloaded_file, destination_path)

        print("MODIS data downloaded and moved to the specified folder.")
        return True
    except Exception as e:
        print(f"An error occurred during download: {e}")
        return []

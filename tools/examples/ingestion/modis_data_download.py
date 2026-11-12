import os
import shutil
from pathlib import Path
from modis_tools.auth import ModisSession
from modis_tools.resources import CollectionApi, GranuleApi
from modis_tools.granule_handler import GranuleHandler
from modis_tools import granule_handler

def download_modis_data(username, password, output_folder, start_date, end_date, bounding_box):
    try:
        # Patch temporanea per correggere errori nella libreria modis_tools
        def fixed_download_from_urls(cls, urls, modis_session, path=None, force=False, disable=False):
            downloaded_files = []
            for url in urls:
                url = str(url)  # converti AnyUrl in stringa
                file_path = Path(path or "") / Path(url).name

                if file_path.exists() and not force:
                    print(f"Already downloaded: {file_path}")
                    downloaded_files.append(file_path)
                    continue

                req = cls._get(url, modis_session)
                if not req.ok:
                    raise Exception(f"Error downloading: {url} - {req.status_code}")

                with open(file_path, "wb") as f:
                    shutil.copyfileobj(req.raw, f)

                downloaded_files.append(file_path)
                print(f"Downloaded: {file_path}")

            return downloaded_files

        def fixed_get_location(cls, url, modis_session):
            return str(url)

        # Applica le patch
        granule_handler.GranuleHandler.download_from_urls = classmethod(fixed_download_from_urls)
        granule_handler.GranuleHandler._get_location = classmethod(fixed_get_location)

        # Autenticazione
        session = ModisSession(username=username, password=password)

        # Query del catalogo
        collection_client = CollectionApi(session=session)
        collections = collection_client.query(short_name="MOD11A1", version="061")

        # Query dei granuli
        granule_client = GranuleApi.from_collection(collections[0], session=session)
        granules = granule_client.query(
            start_date=start_date,
            end_date=end_date,
            bounding_box=bounding_box
        )

        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        # Download dei granuli
        downloaded_files = GranuleHandler.download_from_granules(granules, session)

        # Sposta i file nella cartella di output
        for downloaded_file in downloaded_files:
            destination_path = os.path.join(output_folder, os.path.basename(downloaded_file))
            shutil.move(downloaded_file, destination_path)

        print("MODIS data downloaded and moved to the specified folder.")
        return True

    except Exception as e:
        print(f"An error occurred during download: {e}")
        return []
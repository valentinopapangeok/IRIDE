import os
import time as t
from datetime import timedelta
import ftplib
from ftplib import FTP
import logging
import requests


def download_h40(end, ingestion_folder, user, password):
    """
    [SX-YY-MG01-MB01]
    Reads an asset from a STAC item based on the provided band name.

    Args:
        item_url (str): The URL of the STAC item.
        band (str): The common name of the band to search for (e.g., 'green', 'nir').

    Returns:
        str: The absolute URL of the asset.

    Raises:
        ValueError: If the common band name is not found in the assets.
    """
    # logger.info(f"Reading HSAF data...")

    try:
        ftp = FTP('ftphsaf.meteoam.it')
        ftp.login(user=user, passwd=password)
        ftp.cwd('/h40/h40_cur_mon_data')

    except Exception as e:
        print(f"An Auth error occurred: {e}")

    times = [end - timedelta(minutes=60) + timedelta(minutes=5 * i) for i in range(12)]

    for time in times:

        year, month, day, hour, minute = time.strftime('%Y'), time.strftime('%m'), time.strftime('%d'), time.strftime(
            '%H'), time.strftime('%M')

        if minute.endswith("0"):

            print("Downloading", time)
            fname = f'h40_{year}{month}{day}_{hour}{minute}_fdk.nc.gz'
            fpath = os.path.join(ingestion_folder, fname)

            try:
                with open(fpath, "wb") as f:
                    ftp.retrbinary("RETR " + fname, f.write)
            except(ftplib.error_perm):
                pass
            t.sleep(1)

    ftp.quit()
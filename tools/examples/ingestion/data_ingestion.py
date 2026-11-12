from prefect.logging import get_run_logger
from prefect_common import svc_flow, capture_logs
from steps.ingestion.download_stac import download_stac

import os, re, shutil, zipfile
from datetime import datetime
from pathlib import Path


@svc_flow(name="S5-02-MG01-MB01 Data ingestion (from Data Collector)")
async def data_ingestion(
    dt: datetime,
    input_path: str,
    parent_folder_path: str,
    sentinel_folder: str,
    modis_folder: str,
    gcom_folder: str,
    era5_folder: str,
    era5land_folder: str
):
    logger = get_run_logger()

    with capture_logs(code="S5-02-MG01-MB01", products="S5-02-01", logger=logger):

        # --- Input sanity ---
        input_path = (input_path or "").strip()
        if not input_path:
            raise RuntimeError("S5-02-01 ingestion: empty input_path")

        download_product_folder = os.path.join(parent_folder_path, "download")
        os.makedirs(download_product_folder, exist_ok=True)
        root = Path(download_product_folder)

        # --- STAC pull only ---
        ak = os.getenv("DCO_ACCESS_KEY")
        sk = os.getenv("DCO_SECRET_KEY")
        ep = os.getenv("DCO_ENDPOINT_URL")
        day = dt.strftime("%Y-%m-%d")

        logger.info('S5-02-MG01-MB01 - Calling: Data ingestion (from Data Collector)')

        pulled = await download_stac(
            input_path=input_path,
            aws_access_key_id=ak,
            aws_secret_access_key=sk,
            s3_endpoint=ep,
            filter_date=day,
            local_download_dir=str(root),
        )
        if not pulled:
            logger.warning("No assets downloaded from DCO.")
            return False

        # --- Classification ---
        sent, modis, gcom, era5, era5land = [], [], [], [], []

        for p in sorted(root.iterdir()):
            fname = p.name

            # Sentinel-3 SL_2 LST/WST restricted to 08:00–12:30 UTC
            m = re.match(r"^S3[AB]_SL_2_(?:LST|WST)____(\d{8})T(\d{6})", fname)
            if m:
                tt = datetime.strptime(m.group(2), "%H%M%S").time()
                if datetime.strptime("08:00:00", "%H:%M:%S").time() <= tt <= datetime.strptime("12:30:00", "%H:%M:%S").time():
                    os.makedirs(sentinel_folder, exist_ok=True)
                    if p.is_file() and fname.lower().endswith(".zip"):
                        dest_zip = Path(sentinel_folder) / fname
                        shutil.move(str(p), dest_zip)
                        with zipfile.ZipFile(dest_zip, "r") as zf:
                            zf.extractall(sentinel_folder)
                        dest_zip.unlink(missing_ok=True)
                    else:
                        shutil.move(str(p), str(Path(sentinel_folder) / fname))
                    sent.append(fname)
                continue

            # MODIS
            if p.is_file() and re.search(r"(?:^|_)(MOD11A1|MYD11A1)(?:_|\.|$).*\.hdf$", fname, re.IGNORECASE):
                os.makedirs(modis_folder, exist_ok=True)
                shutil.move(str(p), str(Path(modis_folder) / fname))
                modis.append(fname)
                continue

            # GCOM-C
            if p.is_file() and fname.startswith("GC1SG1") and fname.endswith(".h5"):
                os.makedirs(gcom_folder, exist_ok=True)
                shutil.move(str(p), str(Path(gcom_folder) / fname))
                gcom.append(fname)
                continue

            # ERA5
            if p.is_file() and re.match(r"^ERA5_SL_\d{8}\.nc$", fname, re.IGNORECASE):
                os.makedirs(era5_folder, exist_ok=True)
                shutil.move(str(p), str(Path(era5_folder) / fname))
                era5.append(fname)
                continue

            # ERA5-Land
            if p.is_file() and re.match(r"^ERA5_LAND_\d{8}\.nc$", fname, re.IGNORECASE):
                os.makedirs(era5land_folder, exist_ok=True)
                shutil.move(str(p), str(Path(era5land_folder) / fname))
                era5land.append(fname)
                continue


        logger.info('S5-02-MG01-MB01 - Data ingestion (from Data Collector): Completed')

        # ---------------------------------------------------------------------------------
        # TEMPORARY BLOCK – Sentinel-3 ONLY MODE
        # This block removes all non-Sentinel-3 data after ingestion.
        # To disable this behavior, simply DELETE this block.
        # ---------------------------------------------------------------------------------

        logger.warning("[S5-02] Sentinel-3 ONLY mode active: removing non-Sentinel data")

        def _clear_directory_contents(directory: str):
            if not directory or not os.path.exists(directory):
                return
            for item in os.listdir(directory):
                path = os.path.join(directory, item)
                try:
                    if os.path.isdir(path) and not os.path.islink(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)
                except Exception as exc:
                    logger.warning(f"[S5-02] Failed to remove {path}: {exc}")

        # Remove everything except Sentinel-3
        _clear_directory_contents(modis_folder)
        _clear_directory_contents(gcom_folder)
        _clear_directory_contents(era5_folder)
        _clear_directory_contents(era5land_folder)

        # Also clean the generic download staging area
        _clear_directory_contents(download_product_folder)

        logger.warning("[S5-02] Non-Sentinel data successfully removed")

        # ---------------------------------------------------------------------------------

        # --- Final outcome ---
        return bool(sent or modis or gcom or era5 or era5land)

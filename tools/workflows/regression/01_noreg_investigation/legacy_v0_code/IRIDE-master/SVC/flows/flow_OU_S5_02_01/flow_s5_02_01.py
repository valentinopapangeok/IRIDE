
from datetime import datetime
import numpy as np
import logging
import os
import shutil
from steps.ingestion.sentinel3_data_download import download_and_extract_sentinel3
from steps.ingestion.modis_data_download import download_modis_data
from steps.ingestion.era5_era5land_download import era5_download, era5land_download
from steps.ingestion import data_download_set_logfile_path
from steps.processing import data_fusion_set_logfile_path
from steps.preprocessing import data_preprocessing_set_logfile_path
from steps.packaging_delivery import packaging_delivery_set_logfile_path
from steps.preprocessing.sentinel3_preprocessing import process_sentinel3_files
from steps.preprocessing.modis_preprocessing import (
    modis_txt_creation,
    convert_modis_hdf_to_tiff,
    process_modis_QA_bands,
    convert_modis_dn_to_lst,
)
from steps.preprocessing.EO_derived_data_preprocessing import (
    sentinel3_mosaic,
    modis_mosaic,
    clip_tifs_with_shapefile,
    reproject_tiffs,
    remove_sentinel3_outlier,
)
from steps.preprocessing.model_data_preprocessing import (
    era5landcsv_to_tiff,
    era5csv_to_geotiff,
    resample_era5land_to_s3,
    resample_era5_to_s3,
)
from SVC.flows.flow_OU_S5_02_01.steps.processing.file_management import (
    create_folder_structure,
    get_boundaries_from_shapefile,
    concatenate_text_files,
)

from steps.processing.datafusion import (
    data_fusion,
    replace_nodata_value,
    replace_nan_with_value,
    replace_values_with_constant_in_folder,
    process_tiff_files,
)
from steps.packaging_delivery.packaging_delivery import upload_product_to_s3
from steps.validation_quality_check.validation_quality_check import product_validation_check
from SVC.common.configuration.config_loader import load_json_configs_dict, load_configs_if_file_exists, get_config_value
from SVC.common.configuration.configuration_keys import ConfigKeys
from SVC.common.logging.utils import setup_logging
from SVC.common.mongo.mongodb_client import MongoDBClient
from SVC.common.utilities.file_operations import (
    convert_to_cog,
    create_directory,
)
from SVC.common.utilities.metadata_lst import metadata_generation, void_metadata_generation
from SVC.common.utilities.settings_utils import parse_command_line_args_new
from SVC.common.utilities.time_operations import (
    TimeFormats,
    TimeUnits,
    increment_time,
    is_expired,
)

RECOVERY = False
MAX_DELIVERY_DELAY_HOURS = 24 * 14
CONFIG_JSON_PATH = "/app/SVC/flows/flow_OU_S5_02_01/config.json"

if __name__ == "__main__":

    args: dict | None = parse_command_line_args_new()

    # Aggiungi controllo che args non sia None
    if args is not None:
        RECOVERY = True
    else:
        RECOVERY = False

    configs: dict = load_json_configs_dict(CONFIG_JSON_PATH)

    target_folder: str = configs[ConfigKeys.TIFF_FOLDER.value]
    xml_configs: dict = configs[ConfigKeys.XML_CONFIGS.value]

    # Carica la data iniziale da config.json
    year = int(configs[ConfigKeys.TIMESTAMPS.value][ConfigKeys.YEAR.value])
    day = int(configs[ConfigKeys.TIMESTAMPS.value][ConfigKeys.DAY.value])
    month = int(configs[ConfigKeys.TIMESTAMPS.value][ConfigKeys.MONTH.value])
    hour_st = int(configs[ConfigKeys.TIMESTAMPS.value][ConfigKeys.HOUR_ST.value])
    min_st = int(configs[ConfigKeys.TIMESTAMPS.value][ConfigKeys.MIN_ST.value])

    # Se "processing_date" è passato come argomento, sovrascrivi la data
    if args is not None and "processing_date" in args:
        try:
            processing_date = datetime.strptime(args["processing_date"], "%d/%m/%Y")
            year = processing_date.year
            month = processing_date.month
            day = processing_date.day
        except ValueError:
            raise ValueError("Formato data non valido per 'processing_date'. Usa il formato 'dd/mm/yyyy'.")

    # Carica i dettagli di connessione MongoDB
    MONGO_HOST = str(configs[ConfigKeys.MONGO.value][ConfigKeys.MONGO_HOST.value])
    MONGO_PORT = int(configs[ConfigKeys.MONGO.value][ConfigKeys.MONGO_PORT.value])
    DATABASE = str(configs[ConfigKeys.MONGO.value][ConfigKeys.DATABASE.value])
    COLLECTION = str(configs[ConfigKeys.MONGO.value][ConfigKeys.COLLECTION.value])
    SERVICE_NAME = str(configs[ConfigKeys.SERVICE_NAME.value])

    # Recupera credenziali private
    private_configs = load_configs_if_file_exists("/app/SVC/flows/flow_OU_S5_02_01/steps/private_config.json")
    SENTINEL3_USER = get_config_value(ConfigKeys.SENTINEL3_USER.value, private_configs)
    SENTINEL3_PWD = get_config_value(ConfigKeys.SENTINEL3_PWD.value, private_configs)
    MODIS_USER = get_config_value(ConfigKeys.MODIS_USER.value, private_configs)
    MODIS_PWD = get_config_value(ConfigKeys.MODIS_PWD.value, private_configs)
    GCOMC_USER = get_config_value(ConfigKeys.GCOM_C_USER.value, private_configs)
    GCOMC_PWD = get_config_value(ConfigKeys.GCOM_C_PWD.value, private_configs)
    ERA5_USER = get_config_value(ConfigKeys.ERA5_USER.value, private_configs)
    ERA5_PWD = get_config_value(ConfigKeys.ERA5_PWD.value, private_configs)

    # Crea il client MongoDB
    mongo_client = MongoDBClient(
        host=MONGO_HOST,
        port=MONGO_PORT,
        database_name=DATABASE,
    )

    if not RECOVERY:
        # Inizializza il documento di date sul database
        service_configs: dict = mongo_client.initialize_date_configs(
            collection=COLLECTION,
            service_name=SERVICE_NAME,
            year=year,
            month=month,
            day=day,
            hour_start=hour_st,
            min_start=min_st,
        )

        if service_configs:
            year = int(service_configs[ConfigKeys.YEAR.value])
            day = int(service_configs[ConfigKeys.DAY.value])
            month = int(service_configs[ConfigKeys.MONTH.value])
            hour_st = int(service_configs[ConfigKeys.HOUR_ST.value])
            min_st = int(service_configs[ConfigKeys.MIN_ST.value])

    else:
        ERROR_TIMESTAMP = datetime.strptime(
            args[ConfigKeys.ERROR_TIMESTAMP.value], "%Y-%m-%d %H:%M:%S"
        )
        MAX_DELIVERY_DELAY_HOURS = int(args[ConfigKeys.MAX_DELIVERY_DELAY_HOURS.value])
        COLLECTION = str(ConfigKeys.RECOVERY.value)
        year = int(args[ConfigKeys.YEAR.value])
        day = int(args[ConfigKeys.DAY.value])
        month = int(args[ConfigKeys.MONTH.value])
        hour_st = int(args[ConfigKeys.HOUR_ST.value])
        min_st = int(args[ConfigKeys.MIN_ST.value])

    # Seleziona il correttissimo AOI shapefile per il prodotto
    aoi = "italy"
    if aoi in [
        ConfigKeys.PO_BASIN.value,
        ConfigKeys.NORTH_ITALY.value,
        ConfigKeys.NORTH_SOUTH_ITALY.value,
        ConfigKeys.ITALY.value,
    ]:
        shape_file_path = xml_configs[ConfigKeys.SHAPEFILE_PATH.value][aoi]
        xml_configs[ConfigKeys.AOI.value] = aoi
    else:
        shape_file_path = configs[ConfigKeys.SHAPEFILE_PATH.value]

    end_time = increment_time(
        year=year,
        month=month,
        day=day,
        hour=hour_st,
        minutes=min_st,
        increment_unit=TimeUnits.HOURS,
        increment_value=1,
    )

    # Crea la cartella genitore per i dati orari di questo ciclo
    tif_folder = create_directory(
        base_path=target_folder,
        product_id="S5-02-01",
        reference_time=end_time.get(TimeFormats.STRING_FORMAT_A.value),
        version="V0",
    )

    LOGFILE_PATH: str = f"{tif_folder}/log/logfile.log"
    setup_logging(LOGFILE_PATH)
    data_download_set_logfile_path(LOGFILE_PATH)
    data_fusion_set_logfile_path(LOGFILE_PATH)
    data_preprocessing_set_logfile_path(LOGFILE_PATH)
    packaging_delivery_set_logfile_path(LOGFILE_PATH)

    logging.info(f"Start processing chain for {SERVICE_NAME} service.")

    try:

        start_date = f"{str(year)}-{str(month).zfill(2)}-{str(day).zfill(2)}"
        end_date = f"{str(year)}-{str(month).zfill(2)}-{str(day).zfill(2)}"
        filename_pattern = "IRIDE-S_S5-02-01_{}_V0"

        # Define the desired start_time_gcom and end_time_gcom.
        start_date_object = datetime.strptime(start_date, "%Y-%m-%d")
        start_time_gcom = start_date_object.replace(hour=00, minute=0, second=0)
        end_time_gcom = start_date_object.replace(hour=23, minute=50, second=59)
        formatted_date = start_date_object.strftime("%d%m%Y")
        formatted_date1 = start_date_object.strftime("%Y%m%d")

        # Construct the final filename without any extension.
        final_filename = filename_pattern.format(formatted_date1)
        parent_folder_path = tif_folder

        logging.info(f"Initializing output folders at: {parent_folder_path}.")

        # Check if the base parent folder already exists. If not, create it.
        if not os.path.exists(parent_folder_path):
            os.makedirs(parent_folder_path)

        folders = create_folder_structure(parent_folder_path)
        sentinel_folder = os.path.join(parent_folder_path, folders[0])
        sentinel_processing_folder = os.path.join(parent_folder_path, folders[1])
        sentinel_mosaico = os.path.join(parent_folder_path, folders[2])
        modis_folder = os.path.join(parent_folder_path, folders[3])
        modis_processing_folder = os.path.join(parent_folder_path, folders[4])
        modis_QA_folder = os.path.join(parent_folder_path, folders[5])
        gcom_folder = os.path.join(parent_folder_path, folders[6])
        era5_folder = os.path.join(parent_folder_path, folders[9])
        era5land_folder = os.path.join(parent_folder_path, folders[7])
        product_folder = os.path.join(parent_folder_path, folders[8])
        ritagli_folder = os.path.join(parent_folder_path, folders[10])
        ritagli_reprojected_folder = os.path.join(parent_folder_path, folders[11])
        final_folder = os.path.join(parent_folder_path, folders[12])
        txt_folder = os.path.join(parent_folder_path, folders[13])

        logging.info(f"Folder structure successfully created: {parent_folder_path}.")

        logging.info(
            f"Extracting Bounding Box boundaries from shapefile: {shape_file_path}."
        )
        west_lon, south_lat, east_lon, north_lat = get_boundaries_from_shapefile(
            shapefile_path=shape_file_path
        )

        coordinates = {
            "lat_min": south_lat,
            "lat_max": north_lat,
            "lon_min": west_lon,
            "lon_max": east_lon,
        }

        # Sentinel-3
        logging.info("Starting Sentinel3 download phase.")
        download_and_extract_sentinel3(
            sentinel_folder,
            txt_folder,
            start_date,
            end_date,
            west_lon,
            south_lat,
            east_lon,
            north_lat,
            SENTINEL3_USER,
            SENTINEL3_PWD,
        )
        logging.info(f"Processing S3 downloaded products")
        process_sentinel3_files(
            sentinel_folder, sentinel_processing_folder, 0.011131580833333335
        )
        sentinel3_mosaic(sentinel_processing_folder, sentinel_mosaico, "sentinel.tif")
        remove_sentinel3_outlier(sentinel_mosaico, start_date, np.nan, product_folder)

        logging.info(f"S3 processing has succesfully completed.")

        # Modis
        logging.info(f"Starting Modis download phase.")
        downloaded_files = download_modis_data(
            MODIS_USER,
            MODIS_PWD,
            modis_folder,
            start_date,
            end_date,
            [4.5, 35.27, 22.88, 47.81],
        )
        modis_txt_creation(modis_folder, txt_folder)
        convert_modis_hdf_to_tiff(modis_folder, modis_folder)
        process_modis_QA_bands(modis_folder, modis_QA_folder)
        convert_modis_dn_to_lst(modis_QA_folder, modis_processing_folder)
        logging.info(f"Mosaicking Modis data.")
        modis_mosaic(modis_processing_folder, product_folder, "modis.tif")
        logging.info(f"Processing of Modis data has completed successfully.")

        # Era5
        logging.info("Starting ERA5 download phase.")
        era5_download(start_date, ERA5_USER, ERA5_PWD, era5_folder)
        era5_csv_path = os.path.join(era5_folder, "era5.csv")
        era5tiff_path = os.path.join(era5_folder, "era5.tif")
        era5csv_to_geotiff(era5_csv_path, era5tiff_path)
        logging.info("Starting resampling of ERA5 data to take it to S3 resolution.")
        resample_era5_to_s3(
            era5tiff_path,
            product_folder,
            txt_folder,
            day,
            month,
            year,
            desired_pixel_size=1000,
        )
        logging.info(f"Processing of ERA5 data has completed successfully.")

        # Era5Land
        logging.info("Starting ERA5 Land download phase.")
        year = start_date[:4]
        month = start_date[5:7]
        day = start_date[8:10]

        era5land_download(start_date, ERA5_USER, ERA5_PWD, era5land_folder)
        era5land_csv_path = os.path.join(era5land_folder, "era5land.csv")
        era5landtiff_path = os.path.join(era5land_folder, "era5land.tif")
        era5landcsv_to_tiff(era5land_csv_path, era5landtiff_path)
        resample_era5land_to_s3(product_folder)

        # Clipping
        clip_tifs_with_shapefile(shape_file_path, product_folder, ritagli_folder)

        # Reprojection
        sentinel_tiff_path = os.path.join(ritagli_folder, "sentinel.tif")
        reproject_tiffs(ritagli_folder, ritagli_reprojected_folder, sentinel_tiff_path)

        # DATAFUSION
        logging.info(f"Starting Data Fusion phase.")
        data_fusion(ritagli_reprojected_folder, tif_folder)
        output_tiff_path = os.path.join(tif_folder, "datafusion.tif")
        process_tiff_files(tif_folder, final_folder, "datafusion1.tif", final_filename)
        os.remove(output_tiff_path)
        replace_values_with_constant_in_folder(
            final_folder, start_date, final_filename, -999, tif_folder
        )
        product_file_path = os.path.join(final_folder, "datafusion1.tif")
        os.remove(product_file_path)
        replace_nodata_value(tif_folder, final_folder, -999)

        concatenate_text_files(txt_folder, final_folder, final_filename + ".txt")
        starting_product_path = os.path.join(final_folder, final_filename + ".tif")
        final_product_path = f"{parent_folder_path}/{final_filename}1.tif"

        convert_to_cog(
            input_tif=starting_product_path,
            output_cog=final_product_path,
            nanvalues=True,
        )

        final_product_path1 = os.path.join(parent_folder_path, final_filename + ".tif")
        replace_nan_with_value(
            final_product_path, final_product_path1, replace_value=-999
        )
        os.remove(final_product_path)

        logging.info(
            f"Processing chain has finished correctly for {SERVICE_NAME} service."
        )
        input_files_txt = os.path.join(final_folder, final_filename + ".txt")
        logging.info(f"input_text_files {input_files_txt}")

        input_file_list = concatenate_text_files(
            txt_folder, final_folder, final_filename + ".txt"
        )

        logging.info(f"Starting metadata generation.")
        with open(input_files_txt, "r", encoding="utf-8") as f:
            input_files_content = f.read()
        xml_configs[ConfigKeys.XML_FOLDER.value] = tif_folder
        xml_configs[ConfigKeys.XML_PARENT.value] = target_folder
        xml_configs[ConfigKeys.INPUT_FILES_LIST.value] = (
            input_files_content.splitlines()
        )
        xml_configs[ConfigKeys.REFERENCE_TIME.value] = end_time.get(
            TimeFormats.STRING_FORMAT_A.value
        )
        logging.info(f"Starting metadata generation.")
        metadata_generation(xml_configs=xml_configs)
        logging.info(f"Metadata correctly generated.")
        logging.info(f"tif_folder_sst = {tif_folder}")
        logging.info(f"year = {year}")
        logging.info(f"month = {month}")
        logging.info(f"day = {day}")
        # Run the Validation Quality Check function for the output folder
        LOGFILE_PATH: str = f"{tif_folder}/log/logfile.log"

        upload_product_to_s3(
            "flow_OU_S5_02_01",
            tif_folder,
            "S5-02-01",
            year,
            month,
            day,
            None,
            logfile_path=LOGFILE_PATH,
        )

        if not product_validation_check(tif_folder):
            logging.error("Product validation check has failed.")
            raise Exception("Product validation check has failed.")
        logging.info(f"Product validation check completed.")
        """
        except Exception as e:
           logging.error(f"An unexpected error occurred: {e}")
           logging.warning(
            "Processing for this date/iteration should be computed (manually) again."
        )
        """
        if not RECOVERY:
            logging.info(
                f"Connect to Mongodb to store date configuration for next iteration."
            )
            mongo_client.update_date_configs(
                collection=COLLECTION,
                service_configs=service_configs,
                incr_min=24 * 60,
            )
        else:
            logging.info(f"Recovery successfully performed.")

        logging.info("Deleting temporary files.")

        logging.info(
            f"Processing chain has finished correctly for {SERVICE_NAME} service."
        )

    except Exception as e:

        logging.error(f"An unexpected error occurred: {e}")
        logging.warning(
            "Processing for this date/iteration should be computed (manually) again."
        )

        logging.info(f"Starting metadata (VOID) generation.")
        xml_configs[ConfigKeys.XML_FOLDER.value] = tif_folder
        xml_configs[ConfigKeys.XML_PARENT.value] = target_folder
        xml_configs[ConfigKeys.INPUT_FILES_LIST.value] = ["Not Available"]
        xml_configs[ConfigKeys.REFERENCE_TIME.value] = end_time.get(
            TimeFormats.STRING_FORMAT_A.value
        )
        void_metadata_generation(xml_configs=xml_configs)

        if not RECOVERY:
            logging.info(
                f"Connect to Mongodb to store date configuration for next iteration."
            )
            mongo_client.update_date_configs(
                collection=COLLECTION,
                service_configs=service_configs,
                incr_min=24 * 60,
            )
            logging.info(
                f"Connect to Mongodb to add the current task into pending queue."
            )
            mongo_client.add_pending_task_fifo(
                collection=ConfigKeys.RECOVERY.value,
                service_name=SERVICE_NAME,
                task={
                    ConfigKeys.YEAR.value: year,
                    ConfigKeys.MONTH.value: month,
                    ConfigKeys.DAY.value: day,
                    ConfigKeys.HOUR_ST.value: hour_st,
                    ConfigKeys.MIN_ST.value: min_st,
                    ConfigKeys.ERROR_TIMESTAMP.value: datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    ConfigKeys.MAX_DELIVERY_DELAY_HOURS.value: MAX_DELIVERY_DELAY_HOURS,
                },
            )
        else:
            if not is_expired(
                date1=ERROR_TIMESTAMP, deltaT=MAX_DELIVERY_DELAY_HOURS, use_utc=True
            ):
                logging.info(
                    f"Connect to Mongodb to add the current task into pending queue."
                )
                mongo_client.add_pending_task_fifo(
                    collection=ConfigKeys.RECOVERY.value,
                    service_name=SERVICE_NAME,
                    task={
                        ConfigKeys.YEAR.value: year,
                        ConfigKeys.MONTH.value: month,
                        ConfigKeys.DAY.value: day,
                        ConfigKeys.HOUR_ST.value: hour_st,
                        ConfigKeys.MIN_ST.value: min_st,
                        ConfigKeys.ERROR_TIMESTAMP.value: ERROR_TIMESTAMP.strftime(
                            "%Y-%m-%d %H:%M:%S"
                        ),
                        ConfigKeys.MAX_DELIVERY_DELAY_HOURS.value: MAX_DELIVERY_DELAY_HOURS,
                    },
                )
            else:
                logging.warning(
                    f"Task won't be added to pending tasks queue because max delay time has expired."
                )

        shutil.rmtree(modis_folder)
        shutil.rmtree(gcom_folder)
        shutil.rmtree(era5_folder)
        shutil.rmtree(era5land_folder)
        shutil.rmtree(sentinel_folder)
        shutil.rmtree(txt_folder)
        shutil.rmtree(ritagli_folder)
        shutil.rmtree(product_folder)
        shutil.rmtree(final_folder)

import logging
import os

from SVC.common.configuration.configuration_keys import ConfigKeys
from SVC.common.logging.utils import setup_logging
from SVC.common.product_sender.real_time.worker_product_sender import Worker


def upload_product_to_s3(
    service_name,
    local_output_folder_path,
    product_id,
    year,
    month,
    day,
    hour,
    logfile_path,
):

    setup_logging(logfile_path)

    internal_output = os.getenv(ConfigKeys.INTERNAL_OUTPUT.value)
    logging.info(f"internal_output: {internal_output}")

    #if internal_output == 1, no products are sent to external storage
    if internal_output == "1":
        logging.info("No products are sent to external storage")
        return

    #production destination
    os.environ[ConfigKeys.PHASE_2_METADATA.value] = "1"
    os.environ[ConfigKeys.PHASE_2_METADATA_TIFF.value] = "1"

    # convention are set as env variables when command docker run is executed by controller
    phase2_metadata_convention = os.getenv(ConfigKeys.PHASE_2_METADATA.value)
    phase2_metadata_tiff_convention = os.getenv(ConfigKeys.PHASE_2_METADATA_TIFF.value)

    logging.info(f"phase2_metadata_convention: {phase2_metadata_convention}")
    logging.info(f"phase2_metadata_tiff_convention: {phase2_metadata_tiff_convention}")

    # Create a dictionary to hold only active conventions
    conventions = {}
    if phase2_metadata_convention == "1":
        conventions[ConfigKeys.PHASE_2_METADATA.value] = 1
    if phase2_metadata_tiff_convention == "1":
        conventions[ConfigKeys.PHASE_2_METADATA_TIFF.value] = 1

    worker = Worker(logfile_path)
    worker.process_task(
        service_name,
        local_output_folder_path,
        product_id,
        year,
        month,
        day,
        hour,
        conventions,
    )


def download_product_from_s3(
    service_name,
    local_download_folder_path,
    product_id,
    year,
    month,
    day,
    hour,
    logfile_path,
):

    setup_logging(logfile_path)

    # convention flags from environment variables
    planetek_convention = os.getenv(ConfigKeys.PLANETEK.value)
    backup_convention = os.getenv(ConfigKeys.BACKUP.value)
    std_convention = os.getenv(ConfigKeys.STD.value)
    phase2_metadata_convention = os.getenv(ConfigKeys.PHASE_2_METADATA.value)
    phase2_metadata_tiff_convention = os.getenv(ConfigKeys.PHASE_2_METADATA_TIFF.value)

    logging.info(f"planetek_convention: {planetek_convention}")
    logging.info(f"backup_convention: {backup_convention}")
    logging.info(f"std_convention: {std_convention}")
    logging.info(f"phase2_metadata_convention: {phase2_metadata_convention}")
    logging.info(f"phase2_metadata_tiff_convention: {phase2_metadata_tiff_convention}")

    # active conventions dictionary
    conventions = {}
    if planetek_convention == "1":
        conventions[ConfigKeys.PLANETEK.value] = 1
    if backup_convention == "1":
        conventions[ConfigKeys.BACKUP.value] = 1
    if std_convention == "1":
        conventions[ConfigKeys.STD.value] = 1
    if phase2_metadata_convention == "1":
        conventions[ConfigKeys.PHASE_2_METADATA.value] = 1
    if phase2_metadata_tiff_convention == "1":
        conventions[ConfigKeys.PHASE_2_METADATA_TIFF.value] = 1

    # check if any convention is active
    sink_from_cloud = any(conventions.values())
    if not sink_from_cloud:
        logging.info("No active convention, container is about to stop")
        return

    # Process the download using the Worker class
    worker = Worker(logfile_path)
    worker.download_task(
        service_name,
        local_download_folder_path,
        product_id,
        year,
        month,
        day,
        hour,
        conventions,
    )


if __name__ == "__main__":
    """method call example
    upload_product_to_s3("snow_cover", "/app/output/IRIDE-S_S5-02-05_20241028_V0", "S5-02-05", "2024",
                    "10","28", None)
    """



 #   ***DO NOT CANCEL!***
def upload_product_to_s3_OLD(
service_name,
local_output_folder_path,
product_id,
year,
month,
day,
hour,
logfile_path,
):

    setup_logging(logfile_path)

    # convention are set as env variables when command docker run is executed by controller
    backup_convention = os.getenv(ConfigKeys.BACKUP.value)
    std_convention = os.getenv(ConfigKeys.STD.value)
    phase2_metadata_convention = os.getenv(ConfigKeys.PHASE_2_METADATA.value)
    phase2_metadata_tiff_convention = os.getenv(ConfigKeys.PHASE_2_METADATA_TIFF.value)

    logging.info(f"backup_convention: {backup_convention}")
    logging.info(f"std_convention: {std_convention}")

    logging.info(f"phase2_metadata_convention: {phase2_metadata_convention}")
    logging.info(f"phase2_metadata_tiff_convention: {phase2_metadata_tiff_convention}")

    # Create a dictionary to hold only active conventions
    conventions = {}
    if backup_convention == "1":
        conventions[ConfigKeys.BACKUP.value] = 1
    if std_convention == "1":
        conventions[ConfigKeys.STD.value] = 1
    if phase2_metadata_convention == "1":
        conventions[ConfigKeys.PHASE_2_METADATA.value] = 1
    if phase2_metadata_tiff_convention == "1":
        conventions[ConfigKeys.PHASE_2_METADATA_TIFF.value] = 1

    # check if there is any active convention to send products to cloud storage
    sink_to_cloud = False
    for is_active in conventions.values():
        if is_active == 1:
            sink_to_cloud = True
            break
    if not sink_to_cloud:
        logging.info("No active convention, container is about to stop")
        return

    worker = Worker(logfile_path)
    worker.process_task(
        service_name,
        local_output_folder_path,
        product_id,
        year,
        month,
        day,
        hour,
        conventions,
    )



from pathlib import Path

from eo_utils.validation_07_08.validation_methane import run_iride_gosat_validation_methane
from eo_utils.validation_07_08.validation_co2 import run_iride_gosat_validation_CO2
from eo_utils.validation_07_08.organize_validation_07_08 import organize_validation_dataset

PROJECT_ROOT = Path(__file__).resolve().parents[1]

RAW_INPUT_FOLDER = "/Users/valentinopapandrea/Desktop/University/IRIDE/Validation 07-08/raw_data"
BASE_WORKDIR = "/Users/valentinopapandrea/Desktop/University/IRIDE/Validation 07-08/validation_dataset"

# organize_validation_dataset(
#     input_root=RAW_INPUT_FOLDER,
#     output_root=BASE_WORKDIR
# )

run_iride_gosat_validation_methane(PROJECT_ROOT / "data/validation_07")
#run_iride_gosat_validation_CO2(PROJECT_ROOT / "data/validation_08")

import os
from datetime import datetime
import gportal
from gportal.file import GCOMCFile
from prefect_common import svc_flow


@svc_flow(name="ingestion_gcomc")
def download_gcom_data(
    start_time_gcom, end_time_gcom, gcom_folder, txt_folder, username, password
):

    gportal.username = username
    gportal.password = password

    datasets = gportal.datasets()

    # Search for GCOM-C L3 LST products
    lst_res = gportal.search(
        dataset_ids=datasets["GCOM-C/SGLI"]["LEVEL3"]["Land area"]["L3-LST"],
        start_time=start_time_gcom,
        end_time=end_time_gcom,
        params={
            "ProcessTimeUnit": "01D",
            "orbitDirection": "Descending",
        },
    )

    # Extract products and look for the one with EQR projection
    lst_products = list(lst_res.products())
    lst_product = next((p for p in lst_products if p["mapProjection"] == "EQR"), None)

    if lst_product is not None:
        # Download and convert to GeoTIFF
        lst_path = gportal.download(lst_product, local_dir=gcom_folder)
        lst_file = GCOMCFile.open(lst_path)
        lst_file.save_as_geotiff(targets=["LST_AVE"], output_dir=gcom_folder)
    else:
        print("No product found with mapProjection 'EQR'.")
        return

    # Clean unwanted files
    files = os.listdir(gcom_folder)
    for file_name in files:
        if (
            (len(file_name) > 20 and file_name[20] == "X")
            or (len(file_name) > 15 and file_name[15] == "A")
            and file_name.endswith(".h5")
        ):
            file_path = os.path.join(gcom_folder, file_name)
            os.remove(file_path)
            print(f"Deleted: {file_path}")

    # Check if any valid files remain and write metadata to a .txt file
    files = [f for f in os.listdir(gcom_folder) if f.endswith(".h5")]
    if files:
        acquisition_day = files[0][
            7:15
        ]  # Assumes product name format like 'GC1SG1_YYYYMMDD...'
        acquisition_day = datetime.strptime(acquisition_day, "%Y%m%d").strftime(
            "%d/%m/%Y"
        )
        output_file_path = os.path.join(txt_folder, "gcom.txt")

        with open(output_file_path, "w") as f:
            f.write(
                f"[IN-S5-02-07] GCOM-C-SGLI L3 LST; {acquisition_day}T10:00:00;4600m"
            )

        print(f"Text file successfully created: {output_file_path}")
    else:
        print("No valid GCOM-C data found after download and cleanup.")

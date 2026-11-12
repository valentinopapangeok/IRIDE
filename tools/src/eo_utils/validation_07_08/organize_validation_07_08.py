import os
import re
import shutil
from pathlib import Path

def organize_validation_dataset(input_root: str, output_root: str = None):
    """
    Organize IRIDE and GOSAT files into the structure required
    by the validation script.

    Parameters
    ----------
    input_root : str
        Folder containing mixed / unorganized files.
    output_root : str, optional
        Root of the organized structure. If None, uses input_root.
    """

    input_root = Path(input_root)
    output_root = Path(output_root) if output_root else input_root

    iride_output = output_root / "IRIDE" / "output"
    gosat_output = output_root / "IRIDE" / "Validation_dataset"

    iride_output.mkdir(parents=True, exist_ok=True)
    gosat_output.mkdir(parents=True, exist_ok=True)

    # Patterns for detecting files
    iride_pattern = re.compile(
        r"(IRIDE-S_(S5-02-07|S5-02-08)_(\d{6})_V0)\.tif$",
        re.IGNORECASE
    )
    date_pattern = re.compile(r"(20\d{2})(0[1-9]|1[0-2])")

    for root, _, files in os.walk(input_root):
        for file in files:
            src = Path(root) / file

            # Skip already-organized files
            if output_root in src.parents:
                continue

            # -------------------
            # IRIDE products
            # -------------------
            if file.lower().endswith(".tif"):
                m = iride_pattern.match(file)
                if m:
                    folder_name = m.group(1)
                    dest_dir = iride_output / folder_name
                    dest_dir.mkdir(parents=True, exist_ok=True)

                    dest = dest_dir / file
                    if dest.exists():
                        raise FileExistsError(f"File already exists: {dest}")

                    shutil.move(str(src), str(dest))
                    print(f"Moved IRIDE file: {file} → {dest_dir}")
                    continue

            # -------------------
            # GOSAT products
            # -------------------
            if file.lower().endswith(".h5"):
                name_upper = file.upper()
                if "CH4" in name_upper:
                    var = "CH4"
                elif "CO2" in name_upper:
                    var = "CO2"
                else:
                    raise ValueError(f"Unknown variable (CH4/CO2) in file: {file}")

                date_match = date_pattern.search(file)
                if not date_match:
                    raise ValueError(f"Cannot extract YYYYMM from file: {file}")

                yyyymm = f"{date_match.group(1)}{date_match.group(2)}"

                dest_dir = gosat_output / f"SWIRL3{var}_{yyyymm}_V03.05" / f"SWIRL3{var}"
                dest_dir.mkdir(parents=True, exist_ok=True)

                dest = dest_dir / file
                if dest.exists():
                    raise FileExistsError(f"File already exists: {dest}")

                shutil.move(str(src), str(dest))
                print(f"Moved GOSAT file: {file} → {dest_dir}")

    print("✔ Dataset organization completed successfully.")
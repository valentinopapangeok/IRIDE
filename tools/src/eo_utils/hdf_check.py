from pyhdf.SD import SD, SDC
import sys

def check_hdf4(file_path):
    try:
        hdf = SD(file_path, SDC.READ)
        print("File opened successfully\n")

        datasets = hdf.datasets()

        print(f"Datasets found: {len(datasets)}\n")

        for name, info in datasets.items():
            try:
                print(f"[DATASET] {name}")

                ds = hdf.select(name)

                print(f"  Shape: {ds.info()[2]}")
                print(f"  Type: {ds.info()[3]}")

                # Try reading small sample
                data = ds.get(start=(0,)*len(ds.info()[2]), count=(1,)*len(ds.info()[2]))
                print("  Sample read: OK\n")

            except Exception as e:
                print(f"  ERROR reading dataset: {e}\n")

        print("Integrity check completed.")

    except Exception as e:
        print(f"Failed to open HDF4 file: {e}")

if __name__ == "__main__":
    check_hdf4(sys.argv[1])
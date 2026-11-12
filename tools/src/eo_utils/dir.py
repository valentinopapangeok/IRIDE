import os
from datetime import datetime

tif_dir = "/app/src/_OUT/tif"
dt = datetime(2025, 9, 7, 10, 0, 0)  # example datetime

# Format: YYYYMMDDHH
dt_str = dt.strftime("%Y%m%d%H")

local_tif = os.path.join(tif_dir, f"IRIDE-S_S5-02-03_{dt_str}_V0.tif")

print(local_tif)

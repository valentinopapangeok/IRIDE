import os
from datetime import datetime
from eo_utils.hsaf import download_h40

# -----------------------------
# Configuration
# -----------------------------
# Local folder to save downloaded HSAF files
ingestion_folder = "/Users/valentinopapandrea/Desktop/University/GeoK/eo-utils/data"
os.makedirs(ingestion_folder, exist_ok=True)

# FTP credentials (best practice: use environment variables)
user = "valentino.papandrea@geo-k.co"
password = "qkV-btw:8!nR44f"

# End datetime for the download (UTC)
end_time_str = "2025-12-14T12:00" # or set a specific datetime if needed

# Convert string to datetime object
end_time = datetime.strptime(end_time_str, "%Y-%m-%dT%H:%M")

# -----------------------------
# Run download
# -----------------------------
download_h40(end=end_time, ingestion_folder=ingestion_folder, user=user, password=password)

print("HSAF H40 download completed!")

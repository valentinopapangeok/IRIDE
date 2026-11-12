LOGFILE_PATH = None

def packaging_delivery_set_logfile_path(path):
    global LOGFILE_PATH
    LOGFILE_PATH = path
    print(f"Logfile path set to: {LOGFILE_PATH}")

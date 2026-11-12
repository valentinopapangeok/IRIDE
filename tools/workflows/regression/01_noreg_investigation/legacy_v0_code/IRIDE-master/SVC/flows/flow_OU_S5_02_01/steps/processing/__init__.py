LOGFILE_PATH = None

def data_fusion_set_logfile_path(path):
    global LOGFILE_PATH
    LOGFILE_PATH = path
    print(f"Logfile path set to: {LOGFILE_PATH}")

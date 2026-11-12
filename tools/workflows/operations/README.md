# Operational tools

| Workflow | Entry point | Role |
| --- | --- | --- |
| `input_availability/` | `latest_input_audit.py`, `weekly_input_audit.py`, `build_dashboard.py` | Local provider audit and reporting; own README |
| `buckets/` | `iride_buckets.py --help` | Bucket CLI; reusable functions in `eo_utils.buckets` |
| `local_dco_download/` | `local_dco_download.py` | Local DCO retrieval; own README |
| `local_delivery/` | `local_delivery.py` | Offline product 04 packaging/delivery; own README |

Configs, downloads and event evidence remain with each workflow; former flat
paths and `Utils/buckets/` resolve through compatibility symlinks. Local provider
config is retained but ignored at the canonical path. This reorganization did
not perform downloads, uploads, live provider checks or delivery operations.

Lifecycle: operational tools, with embedded event investigations retained as
scientific cases. The public dashboard has a separate repository and lifecycle.

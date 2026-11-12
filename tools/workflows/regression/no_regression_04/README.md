# Product 04 no-regression input probes

This folder contains focused probes for Product 04 MISTRAL no-regression inputs.

## Findings for 2025-04-01

- Legacy TFS code used MeteoHub dataset `radar_dpc`.
- `https://meteohub.mistralportal.it/api/datasets/radar_dpc/opendata?q=q` now redirects to the new UI and returns HTML, not JSON.
- `https://meteohub.agenziaitaliameteo.it/api/datasets/radar_dpc` confirms `radar_dpc` still exists and is public:
  `Surface Rainfall Intensity from Radar-DPC [ ARCHIVE FROM 19th October 2020 TO 2nd February 2026]`.
- `https://meteohub.agenziaitaliameteo.it/api/datasets/radar_dpc/opendata?q=q` returns an empty JSON list.
- Authenticated archive extraction accepted a request for `radar_dpc` on `2025-04-01T00:00:00Z` to `2025-04-01T01:00:00Z`.
- Accepted request:
  - request id: `4197310`
  - task id: `76611f2d-48b3-4539-831f-a00c8ca21b50`
  - status after polling: `PENDING`

## Scripts

Probe public/open-data routes:

```bash
/Volumes/Extreme/IRIDE/MKPL/Utils/.venv/bin/python \
  /Volumes/Extreme/IRIDE/MKPL/Utils/workflows/regression/no_regression_04/probe_mistral_old_product.py \
  --date 2025-04-01
```

Submit and poll authenticated archive extraction:

```bash
/Volumes/Extreme/IRIDE/MKPL/Utils/.venv/bin/python \
  /Volumes/Extreme/IRIDE/MKPL/Utils/workflows/regression/no_regression_04/request_mistral_archive.py \
  --date 2025-04-01 \
  --hour-from 0 \
  --hour-to 1
```

Check the accepted archive job:

```bash
/Volumes/Extreme/IRIDE/MKPL/Utils/.venv/bin/python \
  /Volumes/Extreme/IRIDE/MKPL/Utils/workflows/regression/no_regression_04/check_mistral_archive_job.py \
  --request-id 4197310
```

Check and download automatically once `fileoutput` is available:

```bash
/Volumes/Extreme/IRIDE/MKPL/Utils/.venv/bin/python \
  /Volumes/Extreme/IRIDE/MKPL/Utils/workflows/regression/no_regression_04/check_mistral_archive_job.py \
  --request-id 4197310 \
  --download
```

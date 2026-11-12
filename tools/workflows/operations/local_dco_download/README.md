# Local DCO Download

Local downloader for DCO activation inputs. It mirrors the PSG/PS temporal filtering used by the product ingestions and then downloads the matching S3 objects into a local folder for integrity checks.

## Inputs

Provide these values in `config.json`:

- `input_path`: activation root catalog path
- `filter_date`: date or timestamp used for filtering
- `psg_id`: production schedule group id
- `ps_id`: production schedule id, or omit it for PSG-only discovery
- `endpoint`: S3-compatible endpoint
- `access_key_id`: local access key
- `secret_access_key`: local secret key
- `output_dir`: local destination directory
- `validate`: optional boolean, defaults to `true`
- `limit`: optional maximum number of matched assets to download

## Run

```bash
/Volumes/Extreme/IRIDE/MKPL/Utils/.venv/bin/python \
  workflows/local_dco_download/local_dco_download.py \
  --config workflows/local_dco_download/config.example.json \
  --limit 1
```

To download one specific item JSON directly:

```bash
/Volumes/Extreme/IRIDE/MKPL/Utils/.venv/bin/python \
  workflows/local_dco_download/local_dco_download.py \
  --config workflows/local_dco_download/config.example.json \
  --item-json /Users/valentinopapandrea/Downloads/DNIin2026060200000042310001I1MA.json \
  --asset-key data
```

## Output

The downloader writes:

- downloaded files under `output_dir/<dataset_id>/<item_id>/<asset_key>/`
- `dco_local_download_manifest.json` with the selected asset records and local paths

Use `--limit 1` for a quick smoke test of a single asset.
Use `--item-json` to skip catalog traversal and download one known asset from a STAC item JSON.

## Notes

- The helper follows the same PSG/PS discovery logic as the product DCO ingestion flows.
- It does not depend on `svc_flow` or `capture_logs`.

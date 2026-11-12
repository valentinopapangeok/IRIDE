# DCO BS3 New Ingestion Porting Guide

This guide describes the repeatable steps used to port a product workflow to the new DCO BS3 ingestion discovery.

Reference implementation in this run:

- product repository: `svc_s5-02-09`
- target branch: `feature`
- requested `prefect-common`: `3.1.0`
- applied `prefect-common`: `3.0.2`

`prefect-common@3.1.0` was checked but is not currently available on the remote. Available tags include `3.0.2`, `3.1.0-beta`, `3.1.0-beta2`, and `3.1.0-beta3`. For stable product work, use `3.0.2` until `3.1.0` is published.

## 1. Apply CAP

Run these commands from the product repository root, for example `svc_s5-02-09`.

```bash
git status --short --branch
git fetch origin main
git fetch origin uat
git checkout --detach origin/main
git branch -D feature || true
git checkout -B feature origin/main
git merge origin/uat
rg -n "<<<<<<<|>>>>>>>" .
```

Expected result:

- `feature` starts from current `origin/main`
- `origin/uat` is merged into `feature`
- no conflict markers remain

Verify CAP ancestry:

```bash
git merge-base --is-ancestor origin/main feature
git merge-base --is-ancestor origin/uat feature
```

Both commands must exit with status `0`.

## 2. Apply PCUP

Run PCUP before importing `prefect_common.dco_bs3`.

File:

```text
src/pyproject.toml
```

Temporarily replace the placeholder token with the real token only for local Poetry resolution and update the tag to `3.0.2`.

Temporary local-only dependency:

```toml
dependencies = [
    "prefect-common @ git+https://gitlab+deploy-token-7:<REAL_PREFECT_COMMON_TOKEN>@gitlab.iride.earth/iride-marketplace/service-segment-ptk/devops_templates/svc-prefect-template/containers/prefect-common.git@3.0.2"
]
```

Then regenerate the lock and install:

```bash
cd src
rm poetry.lock
poetry lock
poetry install
poetry show prefect-common
cd ..
```

`poetry show prefect-common` must report:

```text
version : 3.0.2
```

Before commit, restore the placeholder in both files:

```toml
dependencies = [
    "prefect-common @ git+https://gitlab+deploy-token-7:${PREFECT_COMMON_TOKEN}@gitlab.iride.earth/iride-marketplace/service-segment-ptk/devops_templates/svc-prefect-template/containers/prefect-common.git@3.0.2"
]
```

Also sanitize `src/poetry.lock` so the source URL uses:

```toml
url = "https://gitlab+deploy-token-7:${PREFECT_COMMON_TOKEN}@gitlab.iride.earth/iride-marketplace/service-segment-ptk/devops_templates/svc-prefect-template/containers/prefect-common.git"
```

Verify no real token remains:

```bash
rg -n "glpat-|gldt-" src/pyproject.toml src/poetry.lock
```

This command must return no matches.

## 3. Update The Product Flow

File for product 09:

```text
src/flow_s5_02_09.py
```

After reading `processing_date-OU-S5-02-09`, require the DCO scope identifiers passed by the parent workflow:

```python
processing_date = params.get('processing_date-OU-S5-02-09')
if not processing_date:
    raise ValueError("processing_date-OU-S5-02-09 missing in params")
if 'dco_psg_id' not in params:
    raise ValueError("dco_psg_id is required in params")
if 'dco_ps_id' not in params:
    raise ValueError("dco_ps_id is required in params")

dco_psg_id = str(params['dco_psg_id'])
dco_ps_id = str(params['dco_ps_id'])
logger.info(f"DCO scope from params: PSG {dco_psg_id}, PS {dco_ps_id}")
```

Then pass those values to the ingestion subflow:

```python
_ingestion_success, input_download_summary = await dco_data_ingestion(
    target_date_time,
    output_dir,
    input_path,
    sentinel3_folder,
    modis_folder,
    gcom_c_folder,
    input_model_data,
    dco_psg_id,
    dco_ps_id,
)
```

For other products, use their own flow filename and product-specific processing-date key.

## 4. Update The Product Ingestion Wrapper

File for product 09:

```text
src/steps/ingestion/dco_ingestion.py
```

Extend the ingestion function signature:

```python
async def dco_data_ingestion(
    dt,
    data_folder,
    input_path,
    sentinel3_folder,
    modis_folder,
    gcom_c_folder,
    cams_model_data,
    dco_psg_id,
    dco_ps_id,
):
```

Pass the identifiers to `download_stac`:

```python
download = await download_stac(
    input_path=input_path,
    aws_access_key_id=dco_access_key,
    aws_secret_access_key=dco_secret_key,
    s3_endpoint=dco_endpoint_url,
    filter_date=filter_date,
    local_download_dir=data_folder,
    psg_id=dco_psg_id,
    ps_id=dco_ps_id,
)
```

Keep the product-specific classification logic unchanged unless the product itself needs new file patterns.

## 5. Replace STAC Discovery With DCO BS3 Discovery

File:

```text
src/steps/ingestion/download_stac.py
```

Remove the direct PySTAC catalog traversal and import the new helper:

```python
from prefect_common.dco_bs3 import get_input_with_temporal_params
```

Add these local helpers:

```python
def normalize_activation_catalog_path(input_path: str) -> str:
    input_path = (input_path or "").strip()
    if not input_path:
        raise ValueError("input_path is required")
    if input_path.rstrip("/").endswith("/catalog.json"):
        return input_path.rstrip("/")
    return f"{input_path.rstrip('/')}/catalog.json"


def split_s3_asset_href(href: str) -> tuple[str, str] | None:
    href = (href or "").strip()
    if href.startswith("s3://"):
        bucket_key = href.removeprefix("s3://")
    elif href.startswith("/"):
        bucket_key = href.lstrip("/")
    else:
        return None

    if "/" not in bucket_key:
        return None

    bucket, key = bucket_key.split("/", 1)
    return bucket, key


def get_local_asset_name(href: str) -> str:
    return href.rstrip("/").split("/")[-1]
```

Extend `download_stac`:

```python
async def download_stac(
    input_path: str,
    aws_access_key_id: str,
    aws_secret_access_key: str,
    s3_endpoint: str,
    filter_date: str,
    local_download_dir: str,
    psg_id: str,
    ps_id: str,
):
```

Replace the previous `pystac.Catalog.from_file(...)` traversal with:

```python
activation_catalog_path = normalize_activation_catalog_path(input_path)
logger.info(f"Loading DCO activation catalog: {activation_catalog_path}")
logger.info(f"Filtering DCO inputs for date {filter_date}, PSG {psg_id}, PS {ps_id}")

filtered_assets = []
seen_hrefs = set()
for scope_name, scope_ps_id in [("PSG", None), ("PS", ps_id)]:
    kwargs = {
        "activation_catalog_path": activation_catalog_path,
        "psg_id": psg_id,
        "start_datetime": filter_date,
        "end_datetime": filter_date,
    }
    if scope_ps_id:
        kwargs["ps_id"] = scope_ps_id

    scope_assets = get_input_with_temporal_params(**kwargs)
    logger.info(f"DCO {scope_name} inputs matching {filter_date}: {len(scope_assets)}")
    for asset in scope_assets:
        href = asset.get("href")
        if href and href not in seen_hrefs:
            filtered_assets.append(asset)
            seen_hrefs.add(href)
```

Then download each returned asset:

```python
for asset in filtered_assets:
    asset_href = asset.get("href")
    asset_key = asset.get("asset_key", "")
    item_id = asset.get("item_id", "")
    logger.info(f"Preparing to download DCO asset '{asset_key}' from item '{item_id}': {asset_href}")

    bucket_key = split_s3_asset_href(asset_href)
    if not bucket_key:
        logger.info(f"Skipping non-S3 asset: {asset_href}")
        continue

    bucket, key = bucket_key
    local_path = os.path.join(local_download_dir, get_local_asset_name(asset_href))

    result = download_and_validate_asset(
        bucket=bucket,
        key=key,
        local_path=local_path,
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        s3_endpoint=s3_endpoint,
        product="OU-S5-02-09",
    )
    if result is not None:
        downloaded_any = True
```

Change only the `product="OU-S5-02-09"` value for other products.

## 6. Update Tests

File for product 09:

```text
src/test/unit/steps/ingestion/test_ingestion.py
```

Add a stub for `prefect_common.dco_bs3` before importing `download_stac.py`:

```python
dco_bs3_mod = types.ModuleType("prefect_common.dco_bs3")
dco_bs3_mod.get_input_with_temporal_params = MagicMock()
sys.modules["prefect_common.dco_bs3"] = dco_bs3_mod
```

Add focused tests for:

- `normalize_activation_catalog_path`
- `split_s3_asset_href`
- `download_stac` calling `get_input_with_temporal_params` twice:
  - PSG scope without `ps_id`
  - PS scope with `ps_id`

The important assertions are:

```python
self.assertEqual(mock_get_input.call_count, 2)
self.assertNotIn("ps_id", mock_get_input.call_args_list[0].kwargs)
self.assertEqual(mock_get_input.call_args_list[1].kwargs["ps_id"], "484")
self.assertEqual(mock_download.call_count, 2)
```

## 7. Update Release Metadata

Files:

```text
version.txt
CHANGELOG.md
```

Bump the patch version and add a top changelog entry:

```markdown
## [0.0.337] - 2026-05-19
- Updated prefect-common to 3.0.2.
- Switched product 09 ingestion to DCO BS3 scope-based discovery using PSG and PS identifiers passed by the parent flow.
```

## 8. Run Verification

Recommended checks from the product repository root:

```bash
python3 -m py_compile src/flow_s5_02_09.py src/steps/ingestion/dco_ingestion.py src/steps/ingestion/download_stac.py
poetry -C src run python test/unit/steps/ingestion/test_ingestion.py
poetry -C src show prefect-common
rg -n "glpat-|gldt-" src/pyproject.toml src/poetry.lock
git diff --check
git status --short --branch
```

Expected:

- compile succeeds
- focused unit tests pass
- `prefect-common` is `3.0.2`
- token scan returns no matches
- diff check returns no errors

## 9. Commit And Push

Stage only the product changes:

```bash
git add CHANGELOG.md version.txt src/pyproject.toml src/poetry.lock \
  src/flow_s5_02_09.py \
  src/steps/ingestion/dco_ingestion.py \
  src/steps/ingestion/download_stac.py \
  src/test/unit/steps/ingestion/test_ingestion.py
git commit -m "Use dco_bs3 ingestion for product 09"
```

Verify CAP ancestry again:

```bash
git merge-base --is-ancestor origin/main feature
git merge-base --is-ancestor origin/uat feature
```

Push:

```bash
git push origin feature:feature
```

If a stale remote `feature` exists:

```bash
git push --force-with-lease origin feature:feature
```

Open the `feature -> main` MR and merge it with a normal merge commit. Do not squash or rebase.

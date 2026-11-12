# Local Delivery

Offline delivery emulator that mirrors `svc_s5-02-04` delivery flow structure:

- `delivery` orchestration step
- `stac_creation_upload` step (`generate_thumbnail`, `create_items_to_upload`, `deliver_svc_item`)
- local `packaging_delivery` equivalent

The workflow creates a packaged delivery with:

- `item.json`: STAC Item 1.0.0.
- `assets/` containing TIF, XML, PNG thumbnail, QML and SLD.
- `delivery_manifest.json`: local package manifest and credential target placeholders.

## Assumptions at flow start

Like real 04 delivery, the flow assumes credentials and runtime inputs are already available before execution starts. For local mode they are provided inside local files/variables (not environment variables).

## Required inputs

Provide at invocation time:

- Product TIF (`--tif`)
- Metadata JSON (`--metadata`)
- Local config JSON (`--config`)
- Activation identifier (`--issa-activation-identifier`)

Metadata requirements:

- `id`
- `datetime` (ISO 8601)
- `product_code` must be `S5-02-04`

## Required local variables

Provide in `config.json`:

- `delivery.bucket`: destination bucket name used by packaging target
- `delivery.upload_to`: local upload root folder (usually `svc`)
- `delivery.bucket_folder`: delivery partition root (usually `ar_delivery`)
- `credentials.access_key_id`: credential placeholder/local key
- `credentials.secret_access_key`: credential placeholder/local secret
- `credentials.session_token`: optional token

## Required config fields

In `config.json` (copy from [config.example.json](/Volumes/Extreme/IRIDE/MKPL/Utils/workflows/operations/local_delivery/config.example.json)):

- `style_assets.qml_path` (absolute path to QML)
- `style_assets.sld_path` (absolute path to SLD)

`delivery.bucket` is used directly at runtime in local mode.

## Preparation

Copy and fill files:

```bash
cp workflows/local_delivery/config.example.json workflows/local_delivery/config.json
cp workflows/local_delivery/metadata.example.json /tmp/product_04_metadata.json
```

## Run

```bash
/Volumes/Extreme/IRIDE/MKPL/Utils/.venv/bin/python workflows/local_delivery/local_delivery.py \
  --tif /path/to/IRIDE-S_S5-02-04_20260521T084000_V0.tif \
  --metadata /tmp/product_04_metadata.json \
  --config workflows/local_delivery/config.json \
  --issa-activation-identifier ISSA-domain_S5-272 \
  --output-dir workflows/local_delivery
```

Output path pattern:

- `workflows/local_delivery/deliveries/svc/ar_delivery/YEAR=YYYY/MONTH=MM/DAY=DD/<item_id>/`

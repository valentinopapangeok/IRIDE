# IRIDE S3 bucket helper

Small wrapper around `mc` for the IRIDE S3 environments.

Credentials are read from:

```text
~/.config/iride-s3/credentials.env
```

Do not commit credentials into this directory.

## First-time setup

```bash
cd /Volumes/Extreme/IRIDE/MKPL/Utils/buckets
python3 iride_buckets.py setup
```

## List buckets

```bash
python3 iride_buckets.py list int
python3 iride_buckets.py list uat
python3 iride_buckets.py list prod
```

## List inside a bucket or prefix

```bash
python3 iride_buckets.py list prod iss-prod-geo-dco
python3 iride_buckets.py list prod iss-prod-geo-dco/data-collector/
```

## Download

```bash
python3 iride_buckets.py download prod iss-prod-geo-dco/path/file.zip ~/Downloads/
```

## Upload

```bash
python3 iride_buckets.py upload uat ./file.zip s5-02-uat/path/
```

## Sync folders

```bash
python3 iride_buckets.py sync-down prod iss-prod-geo-dco/path/ ./downloads/path
python3 iride_buckets.py sync-up int ./local-folder s5-02-int/path/
```

## Find files

```bash
python3 iride_buckets.py find prod iss-prod-geo-dco "*.zip"
```

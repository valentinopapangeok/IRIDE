"""Post-thematic positional KPI stages.

Products 01 through 09 use post-thematic positional KPI stages. They never
changes delivery state, thematic metrics, or campaign samples.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import zipfile
from datetime import datetime, time, timezone
from pathlib import Path

from .credentials import downloader_credentials
from .downloads import digest, save_json


def _safe_part(value: str) -> str:
    if not value or value in {'.', '..'} or not re.fullmatch(r'[A-Za-z0-9_.-]+', value):
        raise ValueError(f'Unsafe positional path component: {value!r}')
    return value


def _scene_in_window(path: Path, kind: str = 'LST') -> bool:
    match = re.match(rf'^S3[AB]_SL_2_{kind}____(\d{{8}}T\d{{6}})', path.name)
    if not match:
        return False
    stamp = datetime.strptime(match.group(1), '%Y%m%dT%H%M%S').time()
    return time(8) <= stamp <= time(12, 30)


def _cached_scene_dir(workdir: Path, delivery: dict) -> Path:
    return (workdir / 'positional' / 'inputs' / delivery['product'] /
            _safe_part(delivery['acquired_at'][:10]) / _safe_part(delivery['revision']))


def _validate_cached_inputs(folder: Path, kind: str = 'LST') -> list[Path]:
    scenes = sorted(p for p in folder.glob('*.zip') if _scene_in_window(p, kind))
    if not scenes:
        return []
    for scene in scenes:
        with zipfile.ZipFile(scene) as archive:
            names = {Path(name).name for name in archive.namelist()}
            if kind == 'LST':
                required = {'LST_in.nc', 'geodetic_in.nc', 'flags_in.nc'}
                if not required <= names:
                    raise ValueError(f'Mandatory Sentinel-3 members missing in {scene.name}')
            elif not any(name.endswith('.nc') for name in names):
                raise ValueError(f'Mandatory WST NetCDF member missing in {scene.name}')
            if archive.testzip() is not None:
                raise ValueError(f'Corrupt Sentinel-3 archive: {scene.name}')
    return scenes


def _download_from_dco(day: str, folder: Path, settings: dict, config: dict, base: Path, kind: str, product: str) -> list[Path]:
    """Download mandatory S3 ZIP assets using the production DCO contract.

    This is opt-in and requires the service runtime's ``prefect_common`` DCO
    helper plus DCO_* credentials in the external downloader env file.
    """
    try:
        import boto3
        from prefect_common.dco_bs3 import get_input
    except ImportError as exc:
        raise RuntimeError('DCO positional downloader requires boto3 and prefect_common') from exc
    creds = downloader_credentials(config, base)
    endpoint = settings.get('endpoint_url') or creds.get('DCO_ENDPOINT_URL')
    access = creds.get('DCO_ACCESS_KEY')
    secret = creds.get('DCO_SECRET_KEY')
    catalog = settings.get('catalog_path') or os.environ.get('IRIDE_DCO_INPUT_PATH')
    psg_id = settings.get('psg_id') or os.environ.get('IRIDE_DCO_PSG_ID')
    ps_id = settings.get('ps_id') or os.environ.get('IRIDE_DCO_PS_ID')
    if not all((endpoint, access, secret, catalog, psg_id, ps_id)):
        raise RuntimeError('DCO positional download is not configured; set catalog_path, psg_id, ps_id and external DCO credentials')
    start = f'{day}T00:00:00Z'; end = f'{day}T23:59:59Z'
    assets = []
    seen = set()
    for scope in (None, ps_id):
        kwargs = {'activation_catalog_path': catalog.rstrip('/') + '/catalog.json',
                  'psg_id': psg_id, 'start_datetime': start, 'end_datetime': end}
        if scope:
            kwargs['ps_id'] = scope
        for asset in get_input(**kwargs):
            href = asset.get('href', '')
            name = href.rstrip('/').split('/')[-1]
            if href in seen or not re.match(rf'^S3[AB]_SL_2_{kind}____\d{{8}}T\d{{6}}', name) or not name.endswith('.zip'):
                continue
            if not _scene_in_window(Path(name), kind):
                continue
            seen.add(href); assets.append((href, name))
    client = boto3.client('s3', aws_access_key_id=access, aws_secret_access_key=secret,
                          endpoint_url=endpoint, verify=False)
    folder.mkdir(parents=True, exist_ok=True)
    records = []
    for href, name in assets:
        bucket_key = href.removeprefix('s3://').lstrip('/').split('/', 1)
        if len(bucket_key) != 2:
            continue
        target = folder / _safe_part(name)
        partial = target.with_name(target.name + '.part')
        client.download_file(bucket_key[0], bucket_key[1], str(partial))
        with zipfile.ZipFile(partial) as archive:
            if archive.testzip() is not None:
                partial.unlink(missing_ok=True)
                raise ValueError(f'Corrupt downloaded Sentinel-3 archive: {name}')
        partial.replace(target)
        records.append({'name': name, 'href': href, 'sha256': digest(target), 'bytes': target.stat().st_size})
    save_json(folder / 'download_receipt.json', {'product': product, 'date': day,
             'retrieved_at': datetime.now(timezone.utc).isoformat(), 'assets': records})
    return [folder / item['name'] for item in records]


def _passing_dates(workdir: Path, product: str) -> list[str]:
    path = workdir / 'report' / 'kpi_dates.json'
    if not path.exists():
        return []
    rows = json.loads(path.read_text(encoding='utf-8'))
    return sorted({row['date'] for row in rows if row.get('product') == product and row.get('passes') is True})


def _passing_revisions(workdir: Path, product: str) -> dict[str, str]:
    path = workdir / 'report' / 'kpi_dates.json'
    if not path.exists():
        return {}
    rows = json.loads(path.read_text(encoding='utf-8'))
    selected = {}
    for row in rows:
        if row.get('product') != product or row.get('passes') is not True:
            continue
        revision = row.get('revision')
        if revision is None:
            raise RuntimeError(f'Thematic KPI row has no delivery revision: {product} {row.get("date")}')
        previous = selected.get(row['date'])
        if previous is not None and previous != revision:
            raise RuntimeError(f'Thematic KPI revision is ambiguous for {product} {row["date"]}')
        selected[row['date']] = revision
    return selected


def run_product_positional(registry, config: dict, base: Path, workdir: Path, product: str) -> dict:
    """Run the official positional KPI for thematic-passing dates."""
    from .report import generate
    # Materialise kpi_dates from the just-completed thematic registry run.
    generate(registry, config, workdir, product)
    passing_revisions = _passing_revisions(workdir, product)
    dates = sorted(passing_revisions)
    settings = config.get('positional_accuracy', {}).get(product, {})
    results = []
    if not settings.get('enabled', True):
        return {'status': 'DISABLED', 'dates': []}
    from investigations.positional_footprint_20261116.footprint_experiment import run
    kind = settings.get('source_kind', 'LST' if product == 'S5-02-01' else 'WST')
    target = float(config['products'][product]['positional_target'].get('percent') or 90)
    for day in dates:
        rows = [row for row in registry.rows(product) if row['acquired_at'][:10] == day and row['revision'] == passing_revisions[day]]
        if not rows:
            continue
        row = sorted(rows, key=lambda item: item['revision'])[-1]
        delivery = dict(row)
        folder = _cached_scene_dir(workdir, delivery)
        try:
            scenes = _validate_cached_inputs(folder, kind)
            if not scenes and settings.get('download', True):
                scenes = _download_from_dco(day, folder, settings, config, base, kind, product)
            if not scenes:
                raise RuntimeError('Mandatory Sentinel-3 input cache is missing and DCO download is unavailable')
            final_tif = Path(row['uri'])
            output = workdir / 'positional' / 'results' / product / day / row['revision']
            result = run(folder, final_tif, output, allow_population_mismatch=True, kind=kind,
                         product=product, target_conformity=target)
            evidence = {'product': product, 'date': day, 'area': 'Whole AOI',
                        'kpi_status': 'OFFICIAL',
                        'revision': row['revision'], 'status': 'MEASURED_LINEAGE',
                        'quantity': 'native_to_final_footprint_distance_m',
                        'max_m': result['methods']['footprint_distance']['max_m'],
                        'assessed_cells': result['assessed_population_reproduced'],
                        'conforming_fraction': result['methods']['footprint_distance']['below_threshold_pct'] / 100,
                        'centre_distance': result['methods']['centre_distance'],
                        'footprint_distance': result['methods']['footprint_distance'],
                        'population_comparable_to_historical': result['population_comparable_to_historical'],
                        'final_sha256': result['final_tif']['sha256'],
                        'mandatory_input_checksums': result['selected_scenes'],
                        'artifacts': [str((output / 'result.json').resolve())],
                        'campaign_sample_counted': False,
                        'interpretation': 'Official positional KPI for traceable Sentinel-3 contributors; separate from thematic KPI and campaign sample coverage.'}
            evidence_dir = workdir / 'positional' / 'evidence'; evidence_dir.mkdir(parents=True, exist_ok=True)
            save_json(evidence_dir / f'{product}_{day.replace("-", "")}_Whole_AOI.json', evidence)
            results.append({'date': day, 'status': 'MEASURED_LINEAGE', 'assessed_cells': result['assessed_population_reproduced']})
        except Exception as exc:
            evidence_dir = workdir / 'positional' / 'evidence'; evidence_dir.mkdir(parents=True, exist_ok=True)
            save_json(evidence_dir / f'{product}_{day.replace("-", "")}_Whole_AOI.json',
                      {'product': product, 'date': day, 'area': 'Whole AOI', 'revision': row['revision'],
                       'kpi_status': 'OFFICIAL',
                       'status': 'UNASSESSED', 'quantity': 'not measured', 'max_m': None, 'assessed_cells': 0,
                       'reason': str(exc), 'campaign_sample_counted': False})
            results.append({'date': day, 'status': 'UNASSESSED', 'reason': str(exc)})
    save_json(workdir / 'inventory' / f'positional_accuracy_{product}.json', {'product': product, 'results': results})
    return {'status': 'COMPLETED', 'dates': results}


def run_product01_positional(registry, config: dict, base: Path, workdir: Path) -> dict:
    return run_product_positional(registry, config, base, workdir, 'S5-02-01')


def run_product02_positional(registry, config: dict, base: Path, workdir: Path) -> dict:
    return run_product_positional(registry, config, base, workdir, 'S5-02-02')


def run_product03_positional(registry, config: dict, base: Path, workdir: Path) -> dict:
    from .solar_positional import run_product03_positional as runner
    return runner(registry, config, base, workdir)


def run_product05_positional(registry, config: dict, base: Path, workdir: Path) -> dict:
    from .snow_positional import run_product05_positional as runner
    return runner(registry, config, base, workdir)


def run_product04_positional(registry, config: dict, base: Path, workdir: Path) -> dict:
    from .precipitation_positional import run_product04_positional as runner
    return runner(registry, config, base, workdir)


def run_product06_positional(registry, config: dict, base: Path, workdir: Path) -> dict:
    from .cloud_positional import run_product06_positional as runner
    return runner(registry, config, base, workdir)


def run_product07_positional(registry, config: dict, base: Path, workdir: Path) -> dict:
    from .methane_positional import run_product07_positional as runner
    return runner(registry, config, base, workdir)


def run_product08_positional(registry, config: dict, base: Path, workdir: Path) -> dict:
    from .co2_positional import run_product08_positional as runner
    return runner(registry, config, base, workdir)


def run_product09_positional(registry, config: dict, base: Path, workdir: Path) -> dict:
    from .aod_positional import run_product09_positional as runner
    return runner(registry, config, base, workdir)


def run_product10_positional(registry, config: dict, base: Path, workdir: Path) -> dict:
    from .downscaled_thermal_positional import run_product10_positional as runner
    return runner(registry, config, base, workdir)


def run_product11_positional(registry, config: dict, base: Path, workdir: Path) -> dict:
    from .downscaled_thermal_positional import run_product11_positional as runner
    return runner(registry, config, base, workdir)

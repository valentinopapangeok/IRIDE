"""Official processing-geometry KPI for S5-02-04 hourly precipitation."""
from __future__ import annotations

import csv
import json
import gzip
import os
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from pyproj import Geod

from .downloads import digest, save_json
from .credentials import downloader_credentials

GEOD = Geod(ellps="WGS84")


def _geos_to_latlon(nx, ny, lon0, height, a, b):
    x, y = np.asarray(nx), np.asarray(ny)
    r = height
    r_eq = a
    r_pol = b
    h = r + r_eq
    a2, b2 = r_eq ** 2, r_pol ** 2
    c = (h * np.cos(y)) ** 2 - (np.cos(x) ** 2 + (a2 / b2) * np.sin(x) ** 2) * (h * h - a2)
    sd = (h * np.cos(y) * np.cos(x) - np.sqrt(c)) / (np.cos(x) ** 2 + (a2 / b2) * np.sin(x) ** 2)
    sn = h - sd * np.cos(x) * np.cos(y)
    se = sd * np.sin(x) * np.cos(y)
    lat = np.arctan((a2 / b2) * (sn / np.sqrt(sn * sn + se * se)))
    lon = np.deg2rad(lon0) + np.arctan2(se, sn)
    return np.rad2deg(lat), np.rad2deg(lon)


def _prepare_raw_sources(folder: Path, hour: str) -> None:
    """Materialise the producer's HSAF/MISTRAL raw inputs as audited CSVs."""
    import xarray as xr
    import pandas as pd
    start = pd.Timestamp(hour)
    for path in sorted(folder.iterdir() if folder.exists() else []):
        if path.suffix.lower() in ('.nc', '.gz') and 'h40' in path.name.lower():
            target = folder / (path.stem.replace('.nc', '') + '.csv')
            if target.exists():
                continue
            opener = gzip.open if path.suffix.lower() == '.gz' else open
            with opener(path, 'rb') as stream, xr.open_dataset(stream, engine='h5netcdf', mask_and_scale=True) as ds:
                rr = np.asarray(ds['rr'].values, dtype=float)
                proj = ds['geostationary_projection'].attrs
                nx, ny = np.asarray(ds['nx'].values), np.asarray(ds['ny'].values)
                yy, xx = np.where(np.isfinite(rr) & (rr >= .2))
                lat_a, lon_a = _geos_to_latlon(nx[xx], ny[yy], float(proj['longitude_of_projection_origin']), float(proj['perspective_point_height']), float(proj['semi_major_axis']), float(proj['semi_minor_axis']))
                lat_b, lon_b = _geos_to_latlon(nx[xx], -ny[yy], float(proj['longitude_of_projection_origin']), float(proj['perspective_point_height']), float(proj['semi_major_axis']), float(proj['semi_minor_axis']))
                bbox = lambda lat, lon: np.isfinite(lat) & np.isfinite(lon) & (lat > 35) & (lat < 48) & (lon > 5) & (lon < 20)
                use_b = bbox(lat_b, lon_b).sum() > bbox(lat_a, lon_a).sum()
                frame = pd.DataFrame({'latitude': (lat_b if use_b else lat_a), 'longitude': (lon_b if use_b else lon_a), 'rr': rr[yy, xx]})
            frame.to_csv(target, index=False)
        elif path.suffix.lower() in ('.grib', '.grib2', '.grb', '.grb2'):
            target = folder / 'data.csv'
            if target.exists():
                continue
            with xr.open_dataset(path, engine='cfgrib', decode_timedelta=False) as ds:
                variable = next((name for name in ('tprate', 'rdpr') if name in ds), None)
                if variable is None:
                    continue
                frame = ds[variable].sel(time=slice(start, start + pd.Timedelta(hours=1))).to_dataframe().reset_index()
                frame[variable] = frame[variable] * 3600
                frame = frame[frame[variable] >= .2].rename(columns={variable: 'rr'})[['time', 'latitude', 'longitude', 'rr']]
            frame.to_csv(target, index=False)


def _download_from_dco(day: str, hour: str, folder: Path, settings: dict, config: dict, base: Path) -> None:
    try:
        import boto3
        from prefect_common.dco_bs3 import get_input
    except ImportError as exc:
        raise RuntimeError('DCO precipitation positional downloader requires boto3 and prefect_common') from exc
    creds = downloader_credentials(config, base)
    endpoint = settings.get('endpoint_url') or creds.get('DCO_ENDPOINT_URL')
    access, secret = creds.get('DCO_ACCESS_KEY'), creds.get('DCO_SECRET_KEY')
    catalog = settings.get('catalog_path') or os.environ.get('IRIDE_DCO_INPUT_PATH')
    psg_id = settings.get('psg_id') or os.environ.get('IRIDE_DCO_PSG_ID')
    ps_id = settings.get('ps_id') or os.environ.get('IRIDE_DCO_PS_ID')
    if not all((endpoint, access, secret, catalog, psg_id, ps_id)):
        raise RuntimeError('DCO precipitation source download is not configured')
    start = f'{day}T00:00:00Z'; end = f'{day}T23:59:59Z'; assets = {}; folder.mkdir(parents=True, exist_ok=True)
    for scope in (None, ps_id):
        kwargs = {'activation_catalog_path': catalog.rstrip('/') + '/catalog.json', 'psg_id': psg_id, 'start_datetime': start, 'end_datetime': end}
        if scope: kwargs['ps_id'] = scope
        for asset in get_input(**kwargs):
            href = asset.get('href', ''); name = href.rstrip('/').split('/')[-1]
            if ('h40' in name.lower() or name.lower().endswith(('.grib', '.grib2', '.grb', '.grb2'))) and hour.replace('-', '').replace(':', '')[:10] in name.replace('-', '').replace(':', ''):
                assets[href] = name
    client = boto3.client('s3', aws_access_key_id=access, aws_secret_access_key=secret, endpoint_url=endpoint, verify=False)
    records = []
    for href, name in assets.items():
        parts = href.removeprefix('s3://').lstrip('/').split('/', 1)
        if len(parts) != 2: continue
        target = folder / name; partial = target.with_name(target.name + '.part')
        client.download_file(parts[0], parts[1], str(partial)); partial.replace(target)
        records.append({'name': name, 'href': href, 'sha256': digest(target), 'bytes': target.stat().st_size})
    save_json(folder / 'download_receipt.json', {'product': 'S5-02-04', 'hour': hour, 'retrieved_at': datetime.now(timezone.utc).isoformat(), 'assets': records})


def _summary(values: np.ndarray, tolerance_m: float) -> dict:
    values = np.asarray(values, dtype=float)
    return {"median": float(np.median(values)), "p95": float(np.percentile(values, 95)),
            "max": float(np.max(values)), "below_tolerance_pct": float(np.mean(values < tolerance_m) * 100)}


def _read_sources(folder: Path, start: pd.Timestamp) -> pd.DataFrame:
    import pandas as pd
    paths = sorted(folder.glob("*.csv"))
    radar = next((p for p in paths if p.name == "data.csv"), None)
    h40 = [p for p in paths if "h40B_C_LIIB_" in p.name]
    frames = []
    if radar:
        frame = pd.read_csv(radar, usecols=["time", "latitude", "longitude", "rr"])
        frame["time"] = pd.to_datetime(frame["time"])
        frame = frame[(frame.time >= start) & (frame.time < start + pd.Timedelta(hours=1)) & (frame.time.dt.minute % 10 == 5)]
        frame["radar"], frame["H40"] = True, False
        frames.append(frame)
    for path in h40:
        frame = pd.read_csv(path, usecols=["latitude", "longitude", "rr"])
        stamp = path.stem.split("h40B_C_LIIB_")[1][:12]
        frame["time"] = pd.Timestamp(stamp)
        frame["radar"], frame["H40"] = False, True
        frames.append(frame)
    if not frames:
        raise RuntimeError("No preprocessed HSAF/MISTRAL source CSVs found")
    all_rows = pd.concat(frames, ignore_index=True)
    times = all_rows.time.nunique()
    all_rows["precip"] = (all_rows.rr / (times - 1)).round(1) if times > 1 else all_rows.rr
    fused = all_rows.groupby(["latitude", "longitude"], sort=True).agg(precip=("precip", "sum"), radar=("radar", "max"), H40=("H40", "max")).reset_index()
    return fused[fused.precip >= .2].copy()


def run_grid(source_dir: Path, final_tif: Path, output_dir: Path, hour: str, tolerance_m: float = 4000.0) -> dict:
    start = pd.Timestamp(hour).tz_localize(None)
    fused = _read_sources(source_dir, start)
    output_dir.mkdir(parents=True, exist_ok=True)
    with rasterio.open(final_tif) as raster:
        row, col = rasterio.transform.rowcol(raster.transform, fused.longitude.to_numpy(), fused.latitude.to_numpy())
        fused["row"], fused["col"] = row, col
        inside = (fused.row >= 0) & (fused.row < raster.height) & (fused.col >= 0) & (fused.col < raster.width)
        last = fused[inside].drop_duplicates(["row", "col"], keep="last").copy()
        delivered = raster.read(1)[last.row.to_numpy(), last.col.to_numpy()]
        matches = np.isfinite(delivered) & (delivered >= .2) & (np.abs(delivered - last.precip.to_numpy()) <= .051)
        last = last[matches].copy()
        if last.empty:
            raise RuntimeError("No source-to-final assignments matched rainy delivered cells")
        cx, cy = rasterio.transform.xy(raster.transform, last.row.to_numpy(), last.col.to_numpy(), offset="center")
        _, _, distance = GEOD.inv(last.longitude.to_numpy(), last.latitude.to_numpy(), cx, cy)
        source = np.select([last.radar & last.H40, last.radar, last.H40], ["both", "radar", "H40"], default="unknown")
        subareas = {}
        latitudes = np.asarray(cy)
        for name, mask in (("South", latitudes < 41.5), ("Center", (latitudes >= 41.5) & (latitudes < 44)), ("North", latitudes >= 44)):
            subareas[name] = {"assessed_cells": int(mask.sum()), "assignment_distance_m": _summary(distance[mask], tolerance_m)} if mask.any() else {"assessed_cells": 0, "assignment_distance_m": None}
        result = {"product": "S5-02-04", "hour": hour, "status": "MEASURED_LINEAGE", "tolerance_m": tolerance_m,
                  "final_tif": {"path": str(final_tif), "sha256": digest(final_tif)},
                  "fused_rainy_coordinates": int(len(fused)), "assessed_cells": int(len(last)),
                  "final_rainy_cells": int(np.sum(raster.read(1) >= .2)),
                  "source_counts": {name: int(np.sum(source == name)) for name in ("radar", "H40", "both", "unknown")},
                  "assignment_distance_m": _summary(distance, tolerance_m),
                  "sub_aois": subareas,
                  "mandatory_input_checksums": {str(p): digest(p) for p in sorted(source_dir.glob("*.csv"))},
                  "interpretation": "Source-to-final last-write geometry for verified rainy final cells; separate from gauge/reference support and thematic error."}
    save_json(output_dir / "result.json", result)
    return result


def _passing_hours(workdir: Path) -> dict[str, dict]:
    path = workdir / "report" / "hourly_scores.csv"
    if not path.exists():
        return {}
    selected = {}
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row.get("product") != "S5-02-04" or row.get("area") == "Whole AOI" or row.get("passes", "").lower() != "true":
                continue
            stamp = row["hour_start_utc"][:13]
            revision = row.get("revision")
            if not revision:
                raise RuntimeError(f"Thematic KPI row has no delivery revision: S5-02-04 {stamp}")
            if stamp in selected and selected[stamp]["revision"] != revision:
                raise RuntimeError(f"Thematic KPI revision is ambiguous for S5-02-04 {stamp}")
            selected.setdefault(stamp, {"revision": revision, "areas": []})["areas"].append(row["area"])
    return selected


def run_product04_positional(registry, config: dict, base: Path, workdir: Path) -> dict:
    from .report import generate
    generate(registry, config, workdir, "S5-02-04")
    settings = config.get("positional_accuracy", {}).get("S5-02-04", {})
    if not settings.get("enabled", True):
        return {"status": "DISABLED", "dates": []}
    results = []
    tolerance = float(settings.get("tolerance_m", 4000))
    for hour, selection in sorted(_passing_hours(workdir).items()):
        revision = selection["revision"]
        rows = [r for r in registry.rows("S5-02-04") if r["acquired_at"][:13] == hour and r["revision"] == revision]
        if not rows:
            continue
        row = rows[-1]; folder = workdir / "positional" / "inputs" / "S5-02-04" / hour.replace("-", "").replace("T", "") / revision
        evidence_path = workdir / "positional" / "evidence" / f"S5-02-04_{hour.replace('-', '').replace('T', '').replace(':', '')}_Whole_AOI.json"
        try:
            if not any(folder.glob('*.csv')) and settings.get('download', True):
                _download_from_dco(hour[:10], hour, folder, settings, config, base)
            _prepare_raw_sources(folder, hour)
            result = run_grid(folder, Path(row["uri"]), workdir / "positional" / "results" / "S5-02-04" / hour.replace("-", "").replace("T", "") / revision, hour, tolerance)
            evidence = {"product": "S5-02-04", "date": hour[:10], "hour_start_utc": hour + ":00:00Z", "area": "Whole AOI", "revision": revision,
                        "kpi_status": "OFFICIAL", "status": "MEASURED_LINEAGE", "quantity": "source_to_final_assigned_cell_centre_m",
                        "tolerance_m": tolerance, "max_m": result["assignment_distance_m"]["max"], "assessed_cells": result["assessed_cells"],
                        "conforming_fraction": result["assignment_distance_m"]["below_tolerance_pct"] / 100,
                        "centre_distance": result["assignment_distance_m"], "final_sha256": result["final_tif"]["sha256"],
                        "mandatory_input_checksums": result["mandatory_input_checksums"], "artifacts": [str((workdir / "positional" / "results" / "S5-02-04" / hour.replace("-", "").replace("T", "") / revision / "result.json").resolve())],
                        "thematic_trigger_areas": selection["areas"], "campaign_sample_counted": False, "interpretation": result["interpretation"]}
            save_json(evidence_path, evidence)
            for area in selection["areas"]:
                area_result = result["sub_aois"].get(area, {})
                area_distance = area_result.get("assignment_distance_m")
                if not area_distance:
                    continue
                area_evidence = dict(evidence, area=area, assessed_cells=area_result["assessed_cells"], max_m=area_distance["max"],
                                     conforming_fraction=area_distance["below_tolerance_pct"] / 100, centre_distance=area_distance)
                save_json(workdir / "positional" / "evidence" / f"S5-02-04_{hour.replace('-', '').replace('T', '').replace(':', '')}_{area.replace(' ', '_')}.json", area_evidence)
            results.append({"hour_start_utc": hour, "status": "MEASURED_LINEAGE", "assessed_cells": result["assessed_cells"], "conforming_fraction": evidence["conforming_fraction"]})
        except Exception as exc:
            save_json(evidence_path, {"product": "S5-02-04", "date": hour[:10], "hour_start_utc": hour + ":00:00Z", "area": "Whole AOI", "revision": revision,
                                      "kpi_status": "OFFICIAL", "status": "UNASSESSED", "quantity": "not measured", "tolerance_m": tolerance,
                                      "max_m": None, "assessed_cells": 0, "reason": str(exc), "campaign_sample_counted": False})
            results.append({"hour_start_utc": hour, "status": "UNASSESSED", "reason": str(exc)})
    save_json(workdir / "inventory" / "positional_accuracy_S5-02-04.json", {"product": "S5-02-04", "results": results})
    return {"status": "COMPLETED", "hours": results}

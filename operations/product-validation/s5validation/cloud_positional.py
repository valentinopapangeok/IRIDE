"""Official processing-grid positional KPI for S5-02-06.

The mandatory MTG/FCI Cloud Mask establishes the source geolocation.  The
service requests ``cloud_state`` through Satpy; GRIB2/ecCodes exposes the same
mandatory field as ``cloud_mask`` in the retained feed.  This alias is only a
decoder-name compatibility rule: no alternate reference or value comparison
is introduced here.
"""
from __future__ import annotations

import csv
import json
import os
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from pyproj import Geod

from .credentials import downloader_credentials
from .downloads import digest, save_json
from .positional_accuracy import _safe_part

GEOD = Geod(ellps="WGS84")
GRIB_RE = re.compile(r"^W_.*CLM.*GRIB2.*$")


def _summary(values: np.ndarray, tolerance_m: float) -> dict:
    values = np.asarray(values, dtype=float)
    below = int(np.sum(values < tolerance_m))
    return {"median_m": float(np.median(values)), "p95_m": float(np.percentile(values, 95)),
            "max_m": float(np.max(values)), "below_tolerance_pct": 100.0 * below / len(values),
            "tolerance_m": tolerance_m, "acceptance": "PASS" if below / len(values) * 100 >= 90 else "FAIL"}


def _sources(folder: Path) -> list[Path]:
    files = sorted(p for p in folder.iterdir() if p.is_file() and not p.name.endswith(('.json', '.part'))
                   and (zipfile.is_zipfile(p) or GRIB_RE.match(p.name)))
    for path in files:
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as archive:
                members = [m for m in archive.namelist() if m.lower().endswith(('.bin', '.grib', '.grib2', '.grb', '.grb2'))]
                if len(members) != 1:
                    raise ValueError(f"Expected one MTG Cloud Mask GRIB payload in {path.name}")
                if archive.testzip() is not None:
                    raise ValueError(f"Corrupt MTG Cloud Mask archive: {path.name}")
    return files


def _download_from_dco(hour: str, folder: Path, settings: dict, config: dict, base: Path) -> list[Path]:
    """Download the mandatory MTG Cloud Mask assets through the service DCO contract."""
    try:
        import boto3
        from prefect_common.dco_bs3 import get_input
    except ImportError as exc:
        raise RuntimeError("S5-02-06 positional download requires boto3 and prefect_common") from exc
    creds = downloader_credentials(config, base)
    endpoint = settings.get("endpoint_url") or creds.get("DCO_ENDPOINT_URL")
    access, secret = creds.get("DCO_ACCESS_KEY"), creds.get("DCO_SECRET_KEY")
    catalog = settings.get("catalog_path") or os.environ.get("IRIDE_DCO_INPUT_PATH")
    psg_id = settings.get("psg_id") or os.environ.get("IRIDE_DCO_PSG_ID")
    ps_id = settings.get("ps_id") or os.environ.get("IRIDE_DCO_PS_ID")
    if not all((endpoint, access, secret, catalog, psg_id, ps_id)):
        raise RuntimeError("S5-02-06 positional DCO download is not configured; set catalog_path, psg_id, ps_id and external DCO credentials")
    start = f"{hour}:00:00Z"; end = f"{hour}:59:59Z"
    assets, seen = [], set()
    for scope in (None, ps_id):
        kwargs = {"activation_catalog_path": catalog.rstrip("/") + "/catalog.json", "psg_id": psg_id,
                  "start_datetime": start, "end_datetime": end}
        if scope:
            kwargs["ps_id"] = scope
        for asset in get_input(**kwargs):
            href = asset.get("href", ""); name = href.rstrip("/").split("/")[-1]
            if href in seen or "CLM" not in name or "GRIB2" not in name:
                continue
            seen.add(href); assets.append((href, name))
    if not assets:
        raise RuntimeError(f"No mandatory MTG Cloud Mask assets found for {hour}")
    client = boto3.client("s3", aws_access_key_id=access, aws_secret_access_key=secret, endpoint_url=endpoint, verify=False)
    folder.mkdir(parents=True, exist_ok=True); records = []
    for href, name in assets:
        parts = href.removeprefix("s3://").lstrip("/").split("/", 1)
        if len(parts) != 2:
            continue
        if not re.fullmatch(r"[A-Za-z0-9_.+,\-]+", name):
            raise ValueError(f"Unsafe MTG asset name from DCO: {name!r}")
        target = folder / name; partial = target.with_name(target.name + ".part")
        client.download_file(parts[0], parts[1], str(partial)); partial.replace(target)
        # Validate the archive before making it eligible for the KPI.
        _sources(folder)
        records.append({"name": name, "href": href, "sha256": digest(target), "bytes": target.stat().st_size})
    save_json(folder / "download_receipt.json", {"product": "S5-02-06", "hour": hour, "assets": records,
             "retrieved_at": datetime.now(timezone.utc).isoformat()})
    return _sources(folder)


def _payload(path: Path) -> bytes:
    if not zipfile.is_zipfile(path):
        return path.read_bytes()
    with zipfile.ZipFile(path) as archive:
        member = next(m for m in archive.namelist() if m.lower().endswith(('.bin', '.grib', '.grib2', '.grb', '.grb2')))
        return archive.read(member)


def run_grid(folder: Path, final_tif: Path, output_dir: Path, tolerance_m: float = 3000.0) -> dict:
    try:
        import rasterio
    except ImportError as exc:
        raise RuntimeError("Cloud positional assessment requires rasterio, xarray, cfgrib and scipy") from exc
    sources = _sources(folder)
    if not sources:
        raise RuntimeError("No mandatory MTG/FCI Cloud Mask GRIB2 inputs found")
    output_dir.mkdir(parents=True, exist_ok=True)
    all_distances = []
    source_records = []
    with rasterio.open(final_tif) as final:
        if str(final.crs) != "EPSG:4326":
            raise ValueError("S5-02-06 final grid must be EPSG:4326")
        delivered = final.read(1, masked=True)
        valid = ~np.ma.getmaskarray(delivered) & np.isfinite(np.asarray(delivered))
        rows, cols = np.where(valid)
        fx, fy = final.transform * (cols + 0.5, rows + 0.5)
        # The final raster is the authoritative population; each cell is
        # assigned to the nearest geolocated mandatory MTG source sample.
        final_xy = np.column_stack([fx, fy])
        # The geolocation section is shared by the quarter-hour MTG scans.  All
        # archives remain checksummed below, while one validated scan supplies
        # the common source grid for this hourly delivery.
        for source in sources[:1]:
            raw = _payload(source)
            offset = raw.find(b"GRIB")
            if offset < 0:
                raise ValueError(f"No GRIB message in {source.name}")
            payload = raw[offset:]
            # cfgrib requires a filesystem path for its ecCodes indexer.  The
            # extracted payload is kept under the runtime result directory and
            # is covered by the parent input archive checksum.
            payload_path = output_dir / f"{digest(source)}.grib2"
            payload_path.write_bytes(payload)
            try:
                import eccodes as ec
            except ImportError as exc:
                raise RuntimeError("Cloud positional assessment requires ecCodes") from exc
            stream = payload_path.open("rb")
            gid = ec.codes_grib_new_from_file(stream)
            if gid is None:
                stream.close(); raise ValueError(f"No GRIB message in {source.name}")
            try:
                names = [str(ec.codes_get(gid, "name"))]
                # Read and filter coordinates sequentially to avoid materialising
                # the 31-million-pixel MTG value array.
                lat_all = np.asarray(ec.codes_get_array(gid, "latitudes"), dtype=float)
                lat_good = np.isfinite(lat_all) & (lat_all >= final.bounds.bottom - 0.1) & (lat_all <= final.bounds.top + 0.1)
                lat = lat_all[lat_good]; del lat_all
                lon_all = np.asarray(ec.codes_get_array(gid, "longitudes"), dtype=float)
                lon_all = (lon_all + 180.0) % 360.0 - 180.0
                lon = lon_all[lat_good]; del lon_all
            finally:
                ec.codes_release(gid); stream.close()
            finite = np.isfinite(lat) & np.isfinite(lon) & (lat != 0.0) & (lon != 0.0)
            inside = finite & (lon >= final.bounds.left - 0.1) & (lon <= final.bounds.right + 0.1) & (lat >= final.bounds.bottom - 0.1) & (lat <= final.bounds.top + 0.1)
            source_xy = np.column_stack([lon[inside], lat[inside]])
            if len(source_xy) == 0:
                raise ValueError(f"Mandatory MTG source does not overlap final grid: {source.name}")
            # Avoid a heavyweight spatial-index dependency.  The MTG geolocation
            # is dense; a longitude-binned nearest search is exact within the
            # local candidate window and is deterministic for this grid.
            order = np.argsort(source_xy[:, 0]); ordered = source_xy[order]
            chosen = np.empty(len(final_xy), dtype=int)
            for start in range(0, len(final_xy), 512):
                stop = min(start + 512, len(final_xy)); q = final_xy[start:stop]
                lo = np.searchsorted(ordered[:, 0], q[:, 0].min() - 0.10, side="left")
                hi = np.searchsorted(ordered[:, 0], q[:, 0].max() + 0.10, side="right")
                candidates = ordered[lo:hi]
                if len(candidates) == 0:
                    raise ValueError(f"No local MTG source candidates for {source.name}")
                scale = np.cos(np.deg2rad(np.mean(q[:, 1])))
                delta_lon = (q[:, None, 0] - candidates[None, :, 0]) * scale
                delta_lat = q[:, None, 1] - candidates[None, :, 1]
                chosen[start:stop] = lo + np.argmin(delta_lon * delta_lon + delta_lat * delta_lat, axis=1)
            nearest = ordered[chosen]
            _, _, distances_m = GEOD.inv(fx, fy, nearest[:, 0], nearest[:, 1])
            all_distances.append(np.abs(np.asarray(distances_m, dtype=float)))
            source_records.append({"name": source.name, "sha256": digest(source), "source_points_in_final_window": int(len(source_xy)),
                                   "assigned_final_cells": int(len(distances_m)), "decoder_field": names[0]})
        source_records.extend({"name": source.name, "sha256": digest(source), "role": "same_hour_shared_geolocation"}
                              for source in sources[1:])
    if not all_distances:
        raise RuntimeError("No final cells could be assigned to the mandatory MTG source")
    distances = np.concatenate(all_distances)
    result = {"product": "S5-02-06", "status": "MEASURED_LINEAGE", "quantity": "MTG_source_to_final_cell_centre_distance_m",
              "tolerance_m": tolerance_m, "target_conformity_pct": 90.0, "assessed_cells": int(len(distances)),
              "source_to_final_centre": _summary(distances, tolerance_m),
              "final_tif": {"path": str(final_tif), "sha256": digest(final_tif)}, "mandatory_inputs": source_records,
              "interpretation": "Official processing-grid geometry KPI for the mandatory MTG/FCI Cloud Mask. Decoder cloud_mask is the feed name for the service-requested cloud_state field; no thematic or absolute geolocation claim is made.",
              "method_version": "2026-11-17-cloud-grid-v1"}
    save_json(output_dir / "result.json", result)
    return result


def _passing_hours(workdir: Path) -> dict[str, str]:
    path = workdir / "report" / "hourly_scores.csv"
    if not path.exists():
        return {}
    selected = {}
    with path.open(newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            if row.get("product") != "S5-02-06" or row.get("area") != "Whole AOI" or row.get("passes", "").lower() != "true":
                continue
            hour = row["hour_start_utc"][:13]
            revision = row.get("revision")
            if not revision:
                raise RuntimeError(f"Thematic KPI row has no delivery revision: S5-02-06 {hour}")
            if hour in selected and selected[hour] != revision:
                raise RuntimeError(f"Thematic KPI revision is ambiguous for S5-02-06 {hour}")
            selected[hour] = revision
    return selected


def run_product06_positional(registry, config: dict, base: Path, workdir: Path) -> dict:
    from .report import generate
    generate(registry, config, workdir, "S5-02-06")
    settings = config.get("positional_accuracy", {}).get("S5-02-06", {})
    if not settings.get("enabled", True):
        return {"status": "DISABLED", "hours": []}
    results = []
    tolerance = float(settings.get("tolerance_m", 3000.0))
    for hour, revision in sorted(_passing_hours(workdir).items()):
        rows = [r for r in registry.rows("S5-02-06") if r["acquired_at"][:13] == hour and r["revision"] == revision]
        if not rows:
            continue
        row = rows[-1]
        folder = workdir / "positional" / "inputs" / "S5-02-06" / _safe_part(hour.replace("-", "").replace("T", "")) / _safe_part(revision)
        evidence_path = workdir / "positional" / "evidence" / f"S5-02-06_{hour.replace('-', '').replace('T', '').replace(':', '')}_Whole_AOI.json"
        try:
            sources = _sources(folder)
            if not sources and settings.get("download", True):
                sources = _download_from_dco(hour, folder, settings, config, base)
            if not sources:
                raise RuntimeError("Mandatory MTG Cloud Mask inputs are missing")
            result = run_grid(folder, Path(row["uri"]), workdir / "positional" / "results" / "S5-02-06" / hour.replace("-", "").replace("T", "") / revision, tolerance)
            method = result["source_to_final_centre"]
            evidence = {"product": "S5-02-06", "date": hour[:10], "hour_start_utc": hour + ":00:00Z", "area": "Whole AOI", "revision": revision,
                        "kpi_status": "OFFICIAL", "status": "MEASURED_LINEAGE", "quantity": result["quantity"], "tolerance_m": tolerance,
                        "max_m": method["max_m"], "assessed_cells": result["assessed_cells"], "conforming_fraction": method["below_tolerance_pct"] / 100,
                        "centre_distance": method, "footprint_distance": {"below_tolerance_pct": method["below_tolerance_pct"]},
                        "final_sha256": result["final_tif"]["sha256"], "mandatory_input_checksums": result["mandatory_inputs"],
                        "artifacts": [str((workdir / "positional" / "results" / "S5-02-06" / hour.replace("-", "").replace("T", "") / revision / "result.json").resolve())],
                        "campaign_sample_counted": False, "interpretation": result["interpretation"]}
            save_json(evidence_path, evidence)
            results.append({"hour_start_utc": hour, "status": "MEASURED_LINEAGE", "assessed_cells": result["assessed_cells"], "conforming_fraction": evidence["conforming_fraction"]})
        except Exception as exc:
            save_json(evidence_path, {"product": "S5-02-06", "date": hour[:10], "hour_start_utc": hour + ":00:00Z", "area": "Whole AOI", "revision": revision,
                                      "kpi_status": "OFFICIAL", "status": "UNASSESSED", "quantity": "not measured", "max_m": None, "assessed_cells": 0,
                                      "reason": str(exc), "campaign_sample_counted": False})
            results.append({"hour_start_utc": hour, "status": "UNASSESSED", "reason": str(exc)})
    save_json(workdir / "inventory" / "positional_accuracy_S5-02-06.json", {"product": "S5-02-06", "results": results})
    return {"status": "COMPLETED", "hours": results}

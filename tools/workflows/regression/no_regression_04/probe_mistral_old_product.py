#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests


BASE = Path(__file__).resolve().parent
OUT = BASE / "downloads" / "mistral_old_product"

ROUTES = [
    (
        "old_tfs_route",
        "https://meteohub.mistralportal.it",
        "radar_dpc",
    ),
    (
        "old_dataset_new_host",
        "https://meteohub.agenziaitaliameteo.it",
        "radar_dpc",
    ),
    (
        "current_dataset_new_host",
        "https://meteohub.agenziaitaliameteo.it",
        "radar_sri_dpc",
    ),
]


def fetch_listing(base_url: str, dataset: str) -> tuple[requests.Response, list[dict] | None]:
    url = f"{base_url}/api/datasets/{dataset}/opendata?q=q"
    response = requests.get(url, headers={"accept": "application/json"}, timeout=120, verify=False)
    try:
        data = response.json()
    except ValueError:
        data = None
    return response, data if isinstance(data, list) else None


def download_file(base_url: str, filename: str, route_name: str) -> Path:
    dest_dir = OUT / route_name
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / filename
    url = f"{base_url}/api/opendata/{filename}"
    with requests.get(url, stream=True, timeout=600, verify=False) as response:
        response.raise_for_status()
        with dest.open("wb") as fh:
            for chunk in response.iter_content(1024 * 1024):
                if chunk:
                    fh.write(chunk)
    return dest


def probe(target_date: str, download: bool) -> list[dict]:
    OUT.mkdir(parents=True, exist_ok=True)
    results = []

    for route_name, base_url, dataset in ROUTES:
        response, listing = fetch_listing(base_url, dataset)
        result = {
            "route": route_name,
            "base_url": base_url,
            "dataset": dataset,
            "listing_url": f"{base_url}/api/datasets/{dataset}/opendata?q=q",
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type", ""),
            "final_url": response.url,
            "json_listing": listing is not None,
            "listing_count": len(listing or []),
            "target_date": target_date,
            "matched": False,
            "filename": "",
            "downloaded_file": "",
            "notes": "",
        }

        if listing is None:
            result["notes"] = response.text[:500].replace("\n", " ")
            results.append(result)
            continue

        match = next((row for row in listing if row.get("date") == target_date), None)
        if match:
            result["matched"] = True
            result["filename"] = match.get("filename", "")
            result["notes"] = json.dumps(match, ensure_ascii=True)
            if download and result["filename"]:
                try:
                    downloaded = download_file(base_url, result["filename"], route_name)
                    result["downloaded_file"] = str(downloaded)
                    result["downloaded_bytes"] = downloaded.stat().st_size
                except Exception as exc:
                    result["notes"] += f"; download_error={type(exc).__name__}: {exc}"
        elif listing:
            dates = sorted(row.get("date", "") for row in listing if row.get("date"))
            result["notes"] = f"available_range={dates[0]}..{dates[-1]}; latest_dates={dates[-7:]}"
        else:
            result["notes"] = "empty JSON listing"

        results.append(result)

    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="2025-04-01", help="Target date as YYYY-MM-DD")
    parser.add_argument("--download", action="store_true", help="Download the matched GRIB file")
    args = parser.parse_args()

    requests.packages.urllib3.disable_warnings()
    results = probe(args.date, args.download)
    report = BASE / f"mistral_old_product_probe_{args.date}.json"
    report.write_text(json.dumps(results, indent=2, ensure_ascii=True))

    for row in results:
        print(f"\n## {row['route']}")
        print(f"listing_url={row['listing_url']}")
        print(f"status={row['status_code']} content_type={row['content_type']} final_url={row['final_url']}")
        print(f"json_listing={row['json_listing']} listing_count={row['listing_count']}")
        print(f"matched={row['matched']} filename={row['filename'] or '-'}")
        if row.get("downloaded_file"):
            print(f"downloaded={row['downloaded_file']} bytes={row.get('downloaded_bytes')}")
        print(f"notes={row['notes']}")

    print(f"\nreport={report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

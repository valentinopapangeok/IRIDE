#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import requests


BASE = Path(__file__).resolve().parent
CONFIG = BASE.parents[1] / "operations" / "input_availability" / "config.json"
DOWNLOADS = BASE / "downloads" / "mistral_archive_jobs"
REPORTS = BASE / "reports"


def login() -> str:
    config = json.loads(CONFIG.read_text())
    env = config["providers"]["meteohub"]["env"]
    response = requests.post(
        "https://meteohub.agenziaitaliameteo.it/auth/login",
        json={"username": env["METEOHUB_USER"], "password": env["METEOHUB_PASSWORD"]},
        headers={"accept": "application/json", "content-type": "application/json"},
        timeout=60,
        verify=False,
    )
    response.raise_for_status()
    return response.json()


def request_rows(token: str) -> list[dict]:
    response = requests.get(
        "https://meteohub.agenziaitaliameteo.it/api/requests",
        headers={"Authorization": f"Bearer {token}", "accept": "application/json"},
        timeout=60,
        verify=False,
    )
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, list) else []


def find_request(rows: list[dict], request_id: int) -> dict | None:
    return next((row for row in rows if row.get("id") == request_id), None)


def download_file(token: str, fileoutput: str, request_id: int) -> Path:
    dest_dir = DOWNLOADS / str(request_id)
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = Path(fileoutput).name
    dest = dest_dir / filename
    url = f"https://meteohub.agenziaitaliameteo.it/api/data/{fileoutput}"
    with requests.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        stream=True,
        timeout=900,
        verify=False,
    ) as response:
        response.raise_for_status()
        with dest.open("wb") as fh:
            for chunk in response.iter_content(1024 * 1024):
                if chunk:
                    fh.write(chunk)
    return dest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--request-id", type=int, default=4197310)
    parser.add_argument("--download", action="store_true", help="Download automatically when fileoutput is available")
    args = parser.parse_args()

    requests.packages.urllib3.disable_warnings()
    REPORTS.mkdir(parents=True, exist_ok=True)

    token = login()
    row = find_request(request_rows(token), args.request_id)
    result = {
        "request_id": args.request_id,
        "found": row is not None,
        "request": row,
        "downloaded_file": "",
        "downloaded_bytes": 0,
    }

    if row and args.download and row.get("fileoutput"):
        downloaded = download_file(token, row["fileoutput"], args.request_id)
        result["downloaded_file"] = str(downloaded)
        result["downloaded_bytes"] = downloaded.stat().st_size

    report = REPORTS / f"mistral_archive_job_{args.request_id}.json"
    report.write_text(json.dumps(result, indent=2, ensure_ascii=True))
    print(json.dumps(result, indent=2, ensure_ascii=True))
    print(f"report={report}")

    if not row:
        return 2
    if args.download and not row.get("fileoutput"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

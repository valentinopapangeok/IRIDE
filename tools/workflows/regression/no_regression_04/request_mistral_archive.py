#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import requests


BASE = Path(__file__).resolve().parent
CONFIG = BASE.parents[1] / "operations" / "input_availability" / "config.json"
REPORTS = BASE / "reports"


def meteohub_credentials() -> tuple[str, str]:
    config = json.loads(CONFIG.read_text())
    env = config["providers"]["meteohub"]["env"]
    return env["METEOHUB_USER"], env["METEOHUB_PASSWORD"]


def login() -> str:
    user, password = meteohub_credentials()
    response = requests.post(
        "https://meteohub.agenziaitaliameteo.it/auth/login",
        json={"username": user, "password": password},
        headers={"accept": "application/json", "content-type": "application/json"},
        timeout=60,
        verify=False,
    )
    response.raise_for_status()
    return response.json()


def auth_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "accept": "application/json",
        "content-type": "application/json",
    }


def submit_request(token: str, date: str, hour_from: int, hour_to: int) -> dict:
    name = f"no_regression_04_radar_dpc_{date.replace('-', '')}_{hour_from:02d}00_{hour_to:02d}00"
    payload = {
        "request_name": name,
        "reftime": {
            "from": f"{date}T{hour_from:02d}:00:00.000Z",
            "to": f"{date}T{hour_to:02d}:00:00.000Z",
        },
        "dataset_names": ["radar_dpc"],
    }
    response = requests.post(
        "https://meteohub.agenziaitaliameteo.it/api/data",
        json=payload,
        headers=auth_headers(token),
        timeout=120,
        verify=False,
    )
    return {
        "status_code": response.status_code,
        "payload": payload,
        "response": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
    }


def list_requests(token: str) -> list[dict]:
    response = requests.get(
        "https://meteohub.agenziaitaliameteo.it/api/requests",
        headers=auth_headers(token),
        timeout=60,
        verify=False,
    )
    response.raise_for_status()
    data = response.json()
    return data if isinstance(data, list) else []


def poll_request(token: str, request_id: int, polls: int, sleep_seconds: int) -> list[dict]:
    rows = []
    for _ in range(polls):
        matching = [row for row in list_requests(token) if row.get("id") == request_id]
        row = matching[0] if matching else {"id": request_id, "status": "not_found"}
        rows.append(row)
        if row.get("status") not in {"PENDING", "STARTED", "RETRY", None} or row.get("fileoutput") or row.get("error"):
            break
        time.sleep(sleep_seconds)
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="2025-04-01")
    parser.add_argument("--hour-from", type=int, default=0)
    parser.add_argument("--hour-to", type=int, default=1)
    parser.add_argument("--polls", type=int, default=20)
    parser.add_argument("--sleep", type=int, default=10)
    args = parser.parse_args()

    requests.packages.urllib3.disable_warnings()
    REPORTS.mkdir(parents=True, exist_ok=True)

    token = login()
    submitted = submit_request(token, args.date, args.hour_from, args.hour_to)
    response = submitted["response"]
    request_id = response.get("request_id") if isinstance(response, dict) else None
    polls = poll_request(token, request_id, args.polls, args.sleep) if request_id else []

    report = {
        "submitted": submitted,
        "polls": polls,
    }
    report_path = REPORTS / f"radar_dpc_archive_request_{args.date}_{args.hour_from:02d}_{args.hour_to:02d}.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True))

    print(json.dumps(report, indent=2, ensure_ascii=True))
    print(f"report={report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

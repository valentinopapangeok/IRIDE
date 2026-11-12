from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path


CREDS_FILE = Path.home() / ".config" / "iride-s3" / "credentials.env"
ENDPOINT_VAR = "IRIDE_S3_ENDPOINT"
ENV_VARS = {
    "int": ("IRIDE_INT_ACCESS_KEY", "IRIDE_INT_SECRET_KEY"),
    "uat": ("IRIDE_UAT_ACCESS_KEY", "IRIDE_UAT_SECRET_KEY"),
    "prod": ("IRIDE_PROD_ACCESS_KEY", "IRIDE_PROD_SECRET_KEY"),
}


def parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        raise SystemExit(f"Missing credentials file: {path}")

    values: dict[str, str] = {}
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = shlex.split(value.strip())[0] if value.strip() else ""
    return values


def run(args: list[str]) -> None:
    try:
        subprocess.run(args, check=True)
    except FileNotFoundError:
        raise SystemExit("Missing `mc`. Install it with: brew install minio/stable/mc")
    except subprocess.CalledProcessError as exc:
        raise SystemExit(exc.returncode)


def alias_name(env_name: str) -> str:
    return f"iride-{env_name}"


def remote(env_name: str, path: str | None = None) -> str:
    base = alias_name(env_name)
    if not path:
        return base
    return f"{base}/{path.lstrip('/')}"


def setup_aliases(_args: argparse.Namespace) -> None:
    values = parse_env_file(CREDS_FILE)
    endpoint = values.get(ENDPOINT_VAR, "")
    if not endpoint:
        raise SystemExit(f"{ENDPOINT_VAR} is empty in {CREDS_FILE}")

    for env_name, (access_var, secret_var) in ENV_VARS.items():
        access_key = values.get(access_var, "")
        secret_key = values.get(secret_var, "")
        if not access_key or not secret_key:
            print(f"Skipping {alias_name(env_name)}: missing credentials")
            continue
        run(["mc", "alias", "set", alias_name(env_name), endpoint, access_key, secret_key])


def list_path(args: argparse.Namespace) -> None:
    run(["mc", "ls", remote(args.env, args.path)])


def download(args: argparse.Namespace) -> None:
    run(["mc", "cp", remote(args.env, args.source), os.path.expanduser(args.destination)])


def upload(args: argparse.Namespace) -> None:
    run(["mc", "cp", os.path.expanduser(args.source), remote(args.env, args.destination)])


def sync_down(args: argparse.Namespace) -> None:
    run(["mc", "mirror", remote(args.env, args.source), os.path.expanduser(args.destination)])


def sync_up(args: argparse.Namespace) -> None:
    run(["mc", "mirror", os.path.expanduser(args.source), remote(args.env, args.destination)])


def find(args: argparse.Namespace) -> None:
    run(["mc", "find", remote(args.env, args.path), "--name", args.name])



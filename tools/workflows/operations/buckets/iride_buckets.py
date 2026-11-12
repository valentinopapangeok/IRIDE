#!/usr/bin/env python3
"""Command-line interface for reusable eo_utils.buckets helpers."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Support direct execution from either canonical or compatibility paths.
REPO_ROOT = next(p for p in Path(__file__).resolve().parents
                 if (p / "src" / "eo_utils").is_dir())
sys.path.insert(0, str(REPO_ROOT / "src"))

from eo_utils.buckets import (
    CREDS_FILE,
    ENDPOINT_VAR,
    ENV_VARS,
    parse_env_file,
    run,
    alias_name,
    remote,
    setup_aliases,
    list_path,
    download,
    upload,
    sync_down,
    sync_up,
    find,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="IRIDE S3 bucket helper")
    subparsers = parser.add_subparsers(dest="command", required=True)

    setup = subparsers.add_parser("setup", help="Configure mc aliases from credentials.env")
    setup.set_defaults(func=setup_aliases)

    list_cmd = subparsers.add_parser("list", help="List buckets, bucket contents, or prefix contents")
    list_cmd.add_argument("env", choices=ENV_VARS)
    list_cmd.add_argument("path", nargs="?")
    list_cmd.set_defaults(func=list_path)

    dl = subparsers.add_parser("download", help="Download one object")
    dl.add_argument("env", choices=ENV_VARS)
    dl.add_argument("source", help="Remote path, e.g. bucket/path/file.zip")
    dl.add_argument("destination", help="Local destination")
    dl.set_defaults(func=download)

    ul = subparsers.add_parser("upload", help="Upload one file")
    ul.add_argument("env", choices=ENV_VARS)
    ul.add_argument("source", help="Local file")
    ul.add_argument("destination", help="Remote destination, e.g. bucket/path/")
    ul.set_defaults(func=upload)

    sd = subparsers.add_parser("sync-down", help="Mirror a remote prefix to a local directory")
    sd.add_argument("env", choices=ENV_VARS)
    sd.add_argument("source", help="Remote prefix, e.g. bucket/path/")
    sd.add_argument("destination", help="Local directory")
    sd.set_defaults(func=sync_down)

    su = subparsers.add_parser("sync-up", help="Mirror a local directory to a remote prefix")
    su.add_argument("env", choices=ENV_VARS)
    su.add_argument("source", help="Local directory")
    su.add_argument("destination", help="Remote prefix, e.g. bucket/path/")
    su.set_defaults(func=sync_up)

    find_cmd = subparsers.add_parser("find", help="Find remote objects by name")
    find_cmd.add_argument("env", choices=ENV_VARS)
    find_cmd.add_argument("path", help="Remote bucket or prefix")
    find_cmd.add_argument("name", help='Name pattern, e.g. "*.zip"')
    find_cmd.set_defaults(func=find)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())

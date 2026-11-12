"""Exercise bucket command dispatch offline; no credentials or network required."""
import argparse
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from eo_utils import buckets


class BucketTests(unittest.TestCase):
    def test_remote_prefix_normalization(self):
        self.assertEqual(buckets.remote('uat', '/bucket/path'), 'iride-uat/bucket/path')
        self.assertEqual(buckets.remote('prod', None), 'iride-prod')

    def test_credentials_parser_preserves_quoted_values(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'example.env'
            path.write_text('# example\nENDPOINT="https://example.invalid"\nVALUE="two words"\nEMPTY=\n')
            self.assertEqual(buckets.parse_env_file(path), {
                'ENDPOINT': 'https://example.invalid', 'VALUE': 'two words', 'EMPTY': ''})

    def test_download_dispatches_expected_mc_command(self):
        args = argparse.Namespace(env='uat', source='bucket/object.zip', destination='/tmp/example.zip')
        with patch.object(buckets.subprocess, 'run') as run:
            buckets.download(args)
        run.assert_called_once_with(['mc', 'cp', 'iride-uat/bucket/object.zip', '/tmp/example.zip'], check=True)

    def test_missing_mc_has_actionable_error(self):
        with patch.object(buckets.subprocess, 'run', side_effect=FileNotFoundError):
            with self.assertRaisesRegex(SystemExit, 'Missing `mc`'):
                buckets.run(['mc', 'ls'])

    def test_canonical_and_legacy_cli_dispatch_share_library(self):
        for relative in ['workflows/operations/buckets/iride_buckets.py', 'buckets/iride_buckets.py']:
            spec = importlib.util.spec_from_file_location('bucket_cli_probe', ROOT / relative)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            args = module.build_parser().parse_args(['download', 'uat', 'bucket/object.zip', '/tmp/example.zip'])
            self.assertIs(args.func, buckets.download)
            self.assertEqual(args.source, 'bucket/object.zip')


if __name__ == '__main__':
    unittest.main()

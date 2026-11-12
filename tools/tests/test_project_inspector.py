"""Offline regression checks for bounded, non-destructive README generation."""
import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from eo_utils.project_inspector import update_readme


class ReadmeMapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.readme = self.root / 'README.md'

    def refresh(self, **kwargs):
        with contextlib.redirect_stdout(io.StringIO()):
            update_readme(self.root, self.readme, **kwargs)
        return self.readme.read_text()

    def test_preserves_manual_guidance_and_is_idempotent(self):
        original = '# Maintained guide\n\nUse the approved workflow.\n'
        self.readme.write_text(original)
        (self.root / 'src').mkdir()
        first = self.refresh()
        self.assertTrue(first.startswith(original))
        self.readme.write_text(first + '\nManual footer.\n')
        second = self.refresh()
        self.assertTrue(second.endswith('\nManual footer.\n'))
        self.assertEqual(second, self.refresh())
        self.assertEqual(second.count('<!-- BEGIN GENERATED DIRECTORY MAP -->'), 1)

    def test_bounds_depth_and_entries_and_omits_data_filenames(self):
        for i in range(30):
            directory = self.root / f'workflow{i:02d}'
            (directory / 'nested' / 'too_deep').mkdir(parents=True)
            (directory / 'sample.tif').write_text('data')
        result = self.refresh(max_depth=2, max_entries=3)
        self.assertIn('... 27 more directories', result)
        self.assertIn('nested/', result)
        self.assertNotIn('too_deep', result)
        self.assertNotIn('sample.tif', result)
        self.assertNotIn('workflow03', result)

    def test_skips_hidden_runtime_and_symlink_directories(self):
        for name in ['.venv_py314_unused', 'downloads', 'src']:
            (self.root / name).mkdir()
        (self.root / 'linked').symlink_to(self.root / 'src', target_is_directory=True)
        result = self.refresh()
        self.assertIn('src/', result)
        self.assertNotIn('.venv_py314_unused', result)
        self.assertNotIn('downloads/', result)
        self.assertNotIn('linked/', result)

    def test_rejects_broken_markers_without_overwriting(self):
        for original in [
            '# Guide\n<!-- BEGIN GENERATED DIRECTORY MAP -->\n',
            '<!-- END GENERATED DIRECTORY MAP --><!-- BEGIN GENERATED DIRECTORY MAP -->',
        ]:
            self.readme.write_text(original)
            with self.assertRaises(ValueError):
                self.refresh()
            self.assertEqual(original, self.readme.read_text())

    def test_rejects_unbounded_parameters(self):
        for kwargs in [{'max_depth': 0}, {'max_entries': 0}]:
            with self.assertRaises(ValueError):
                self.refresh(**kwargs)


if __name__ == '__main__':
    unittest.main()

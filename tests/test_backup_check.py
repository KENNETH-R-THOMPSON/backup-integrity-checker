import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from backup_check import main, scan, compare, load_manifest


class BackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'files'
        self.root.mkdir()
        (self.root / 'note.txt').write_text('hello', encoding='utf-8')
        self.manifest = self.base / 'baseline.json'

    def run_cli(self, command):
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return main([command, str(self.root), str(self.manifest)])

    def test_text_report_and_default_json(self):
        self.assertEqual(self.run_cli('snapshot'), 0)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(['verify', str(self.root), str(self.manifest)]), 0)
        self.assertEqual(json.loads(output.getvalue())['unchanged'], 1)
        (self.root / 'note.txt').write_text('changed')
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = main(['verify', str(self.root), str(self.manifest), '--format', 'text'])
        self.assertEqual(result, 1)
        self.assertIn('Changed: 1', output.getvalue())
        self.assertIn('"note.txt"', output.getvalue())

    def test_known_digest(self):
        self.assertEqual(scan(self.root)['note.txt'], '2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824')

    def test_roundtrip_and_changed_content(self):
        self.assertEqual(self.run_cli('snapshot'), 0)
        self.assertEqual(self.run_cli('verify'), 0)
        (self.root / 'note.txt').write_text('HELLO')
        self.assertEqual(self.run_cli('verify'), 1)

    def test_missing_unexpected_and_unchanged(self):
        self.assertEqual(compare({'a': '1', 'b': '2'}, {'b': '2', 'c': '3'}),
                         {'missing': ['a'], 'unexpected': ['c'], 'changed': [], 'unchanged': 1})

    def test_nested_unicode_and_empty(self):
        (self.root / 'nested').mkdir()
        (self.root / 'nested' / 'café.txt').write_bytes(b'')
        self.assertEqual(self.run_cli('snapshot'), 0)
        self.assertEqual(self.run_cli('verify'), 0)
        self.assertIn('nested/café.txt', load_manifest(self.manifest))

    def test_baseline_cannot_be_overwritten(self):
        self.assertEqual(self.run_cli('snapshot'), 0)
        before = self.manifest.read_bytes()
        self.assertEqual(self.run_cli('snapshot'), 2)
        self.assertEqual(self.manifest.read_bytes(), before)
        self.assertEqual(sorted(p.name for p in self.base.iterdir()), ['baseline.json', 'files'])

    def test_reject_internal_manifest(self):
        self.manifest = self.root / 'baseline.json'
        self.assertEqual(self.run_cli('snapshot'), 2)
        self.assertFalse(self.manifest.exists())

    def test_reject_symlink(self):
        (self.root / 'link').symlink_to(self.root / 'note.txt')
        self.assertEqual(self.run_cli('snapshot'), 2)

    def test_invalid_manifest_and_missing_directory(self):
        self.manifest.write_text('{')
        self.assertEqual(self.run_cli('verify'), 2)
        self.root = self.base / 'absent'
        self.assertEqual(self.run_cli('snapshot'), 2)

    def test_reject_traversal_manifest(self):
        self.manifest.write_text(json.dumps({'version': 1, 'algorithm': 'sha256', 'files': {'../secret': 'a' * 64}}))
        with self.assertRaises(ValueError):
            load_manifest(self.manifest)


    def test_publish_failure_leaves_no_partial_baseline(self):
        with patch('backup_check.os.link', side_effect=OSError('simulated publish failure')):
            self.assertEqual(self.run_cli('snapshot'), 2)
        self.assertFalse(self.manifest.exists())
        self.assertEqual(sorted(p.name for p in self.base.iterdir()), ['files'])

    def test_write_failure_cleans_up_temporary_file(self):
        with patch('backup_check.json.dump', side_effect=OSError('simulated write failure')):
            self.assertEqual(self.run_cli('snapshot'), 2)
        self.assertFalse(self.manifest.exists())
        self.assertEqual(sorted(p.name for p in self.base.iterdir()), ['files'])

    def test_reject_file_modified_while_hashing(self):
        real_sha256 = hashlib.sha256
        target = self.root / 'note.txt'

        class MutatingHash:
            def __init__(self):
                self.inner = real_sha256()

            def update(self, data):
                self.inner.update(data)
                target.write_text('changed during scan', encoding='utf-8')

            def hexdigest(self):
                return self.inner.hexdigest()

        with patch('backup_check.hashlib.sha256', side_effect=MutatingHash):
            self.assertEqual(self.run_cli('snapshot'), 2)
        self.assertFalse(self.manifest.exists())

    def test_reject_file_replaced_while_hashing(self):
        real_sha256 = hashlib.sha256
        target = self.root / 'note.txt'

        class ReplacingHash:
            def __init__(self):
                self.inner = real_sha256()

            def update(self, data):
                self.inner.update(data)
                replacement = self.root / 'new.txt'
                replacement.write_text('HELLO', encoding='utf-8')  # Same byte length as original.
                os.replace(replacement, target)

            def hexdigest(self):
                return self.inner.hexdigest()

        ReplacingHash.root = self.root
        with patch('backup_check.hashlib.sha256', side_effect=ReplacingHash):
            self.assertEqual(self.run_cli('snapshot'), 2)
        self.assertFalse(self.manifest.exists())

    def test_verify_rejects_change_during_hashing(self):
        self.assertEqual(self.run_cli('snapshot'), 0)
        original_sha256 = hashlib.sha256
        target = self.root / 'note.txt'

        class MutatingHash:
            def __init__(self):
                self.inner = original_sha256()

            def update(self, data):
                self.inner.update(data)
                target.write_text('changed during verification', encoding='utf-8')

            def hexdigest(self):
                return self.inner.hexdigest()

        output = io.StringIO()
        with patch('backup_check.hashlib.sha256', side_effect=MutatingHash):
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
                result = main(['verify', str(self.root), str(self.manifest)])
        self.assertEqual(result, 2)
        self.assertEqual(output.getvalue(), '')

if __name__ == '__main__':
    unittest.main()

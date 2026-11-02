import contextlib
import csv
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

    def test_cli_error_escaping_preserves_readable_names(self):
        from backup_check import safe_error_text
        unsafe = 'backup' + '\x1b[31m' + '\n' + '\u202e' + '\\' + 'café'
        self.assertEqual(
            safe_error_text(unsafe),
            r'backup\x1b[31m\n\u202e\\café',
        )
        self.assertEqual(safe_error_text('ordinary-file.txt'), 'ordinary-file.txt')

    def test_verify_error_does_not_print_terminal_controls(self):
        unsafe_name = 'fictional' + '\x1b[31m' + '\u202e'
        self.manifest.write_text(
            json.dumps({'version': 1, 'algorithm': 'sha256',
                        'files': {unsafe_name: 'invalid-hash'}}),
            encoding='utf-8',
        )
        output, error = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(error):
            code = main(['verify', str(self.root), str(self.manifest)])
        self.assertEqual(code, 2)
        self.assertEqual(output.getvalue(), '')
        self.assertNotIn('\x1b', error.getvalue())
        self.assertNotIn('\u202e', error.getvalue())
        self.assertIn(r'fictional\x1b[31m\u202e', error.getvalue())

    def test_csv_and_text_reports_escape_filename_controls(self):
        # Use a synthetic manifest path so this test works on Windows too.
        name = "fictional\\x1b[31m\\u202e\\n.csv"
        self.manifest.write_text(json.dumps({
            'version': 1, 'algorithm': 'sha256', 'files': {name: 'a' * 64},
        }), encoding='utf-8')
        with patch('backup_check.scan', return_value={name: 'b' * 64}):
            for output_format in ('csv', 'text'):
                with self.subTest(output_format=output_format):
                    output = io.StringIO()
                    with contextlib.redirect_stdout(output):
                        code = main(['verify', str(self.root), str(self.manifest),
                                     '--format', output_format])
                    self.assertEqual(code, 1)
                    report = output.getvalue()
                    self.assertNotIn('\\x1b', report)
                    self.assertNotIn('\\u202e', report)
                    self.assertNotIn('\\n.csv', report)
                    escaped = r'fictional\\x1b[31m\\u202e\\n.csv'
                    if output_format == 'csv':
                        self.assertIn(['changed', escaped],
                                      list(csv.reader(io.StringIO(report))))
                    else:
                        self.assertIn(json.dumps(escaped), report)

    def test_csv_unchanged_filename_escapes_controls(self):
        name = "fictional\\x1b[31m\\u202e.csv"
        self.manifest.write_text(json.dumps({
            'version': 1, 'algorithm': 'sha256', 'files': {name: 'a' * 64},
        }), encoding='utf-8')
        output = io.StringIO()
        with patch('backup_check.scan', return_value={name: 'a' * 64}):
            with contextlib.redirect_stdout(output):
                code = main(['verify', str(self.root), str(self.manifest),
                             '--format', 'csv'])
        self.assertEqual(code, 0)
        self.assertEqual(list(csv.reader(io.StringIO(output.getvalue()))), [
            ['status', 'path'],
            ['unchanged', r'fictional\\x1b[31m\\u202e.csv'],
        ])

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

    def test_csv_report_lists_each_file_and_escapes_spreadsheet_formulas(self):
        (self.root / '=SUM(1,1).txt').write_text('example', encoding='utf-8')
        (self.root / 'quarter,1.txt').write_text('keep', encoding='utf-8')
        self.assertEqual(self.run_cli('snapshot'), 0)

        (self.root / 'note.txt').write_text('changed', encoding='utf-8')
        (self.root / 'quarter,1.txt').unlink()
        (self.root / 'extra.txt').write_text('new', encoding='utf-8')

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(['verify', str(self.root), str(self.manifest), '--format', 'csv'])
        self.assertEqual(code, 1)
        self.assertEqual(list(csv.reader(io.StringIO(output.getvalue()))), [
            ['status', 'path'],
            ['changed', 'note.txt'],
            ['missing', 'quarter,1.txt'],
            ['unexpected', 'extra.txt'],
            ['unchanged', "'=SUM(1,1).txt"],
        ])

    def test_csv_report_for_unchanged_files_exits_zero(self):
        self.assertEqual(self.run_cli('snapshot'), 0)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(['verify', str(self.root), str(self.manifest), '--format', 'csv'])
        self.assertEqual(code, 0)
        self.assertEqual(list(csv.reader(io.StringIO(output.getvalue()))),
                         [['status', 'path'], ['unchanged', 'note.txt']])

    def test_spreadsheet_prefix_covers_whitespace_and_formula_markers(self):
        from backup_check import spreadsheet_safe_name
        for name in ('=cmd', '+cmd', '-cmd', '@cmd', '  =cmd', '\t+cmd'):
            with self.subTest(name=name):
                self.assertEqual(spreadsheet_safe_name(name), "'" + name)
        self.assertEqual(spreadsheet_safe_name('ordinary.csv'), 'ordinary.csv')

    def test_path_walk_accepts_unchanged_nested_directories(self):
        nested = self.root / 'nested'
        nested.mkdir()
        (nested / 'inside.txt').write_text('fictional data', encoding='utf-8')

        def path_fwalk(root, **kwargs):
            for folder, dirs, names in os.walk(root, onerror=kwargs.get('onerror')):
                yield folder, dirs, names, None

        # Exercise the path-based code path on Unix as well as Windows.
        with patch('backup_check.os.fwalk', side_effect=path_fwalk, create=True):
            result = scan(self.root)
        self.assertEqual(sorted(result), ['nested/inside.txt', 'note.txt'])

    def test_path_walk_rejects_replaced_nested_directory(self):
        parent = self.root / 'nested'
        parent.mkdir()
        child = parent / 'child'
        child.mkdir()
        replacement = self.base / 'replacement'
        replacement.mkdir()

        def path_walk(*args, **kwargs):
            yield str(self.root), ['nested'], ['note.txt']
            yield str(parent), ['child'], []
            # A directory changes after its parent was checked.
            child.rmdir()
            os.replace(replacement, child)
            yield str(child), [], []

        def path_fwalk(*args, **kwargs):
            for folder, dirs, names in path_walk():
                yield folder, dirs, names, None

        with patch('backup_check.os.walk', side_effect=path_walk):
            with patch('backup_check.os.fwalk', side_effect=path_fwalk, create=True):
                with self.assertRaisesRegex(ValueError, 'Directory changed during scan'):
                    scan(self.root)

    def test_windows_reparse_metadata_is_rejected(self):
        import stat
        from types import SimpleNamespace
        from backup_check import is_link_or_reparse

        regular = SimpleNamespace(st_mode=stat.S_IFREG, st_file_attributes=0)
        junction = SimpleNamespace(
            st_mode=stat.S_IFDIR,
            st_file_attributes=stat.FILE_ATTRIBUTE_REPARSE_POINT,
        )
        self.assertFalse(is_link_or_reparse(regular))
        self.assertTrue(is_link_or_reparse(junction))
        self.assertTrue(is_link_or_reparse(SimpleNamespace(st_mode=stat.S_IFLNK)))

    @unittest.skipUnless(os.name == 'nt', 'requires Windows directory junctions')
    def test_windows_junction_directory_and_root_are_rejected(self):
        import subprocess

        outside = self.base / 'outside'
        outside.mkdir()
        (outside / 'private.txt').write_text('fictional private file', encoding='utf-8')

        def junction(link):
            result = subprocess.run(
                ['cmd', '/c', 'mklink', '/J', str(link), str(outside)],
                capture_output=True, text=True, check=False,
            )
            if result.returncode:
                self.skipTest('Windows junction creation unavailable: ' + result.stderr.strip())

        nested = self.root / 'linked'
        junction(nested)
        self.assertEqual(self.run_cli('snapshot'), 2)
        self.assertFalse(self.manifest.exists())
        nested.rmdir()

        root_link = self.base / 'linked_root'
        junction(root_link)
        self.root = root_link
        self.assertEqual(self.run_cli('snapshot'), 2)
        self.assertFalse(self.manifest.exists())
        self.assertEqual((outside / 'private.txt').read_text(encoding='utf-8'),
                         'fictional private file')

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

    @unittest.skipIf(os.name == 'nt', 'backslash is a path separator on Windows')
    def test_snapshot_rejects_backslash_filename(self):
        (self.root / 'notes\\2026.txt').write_text('fictional', encoding='utf-8')
        error = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(error):
            code = main(['snapshot', str(self.root), str(self.manifest)])
        self.assertEqual(code, 2)
        self.assertIn('Invalid manifest path', error.getvalue())
        self.assertFalse(self.manifest.exists())

    @unittest.skipIf(os.name == 'nt', 'backslash is a path separator on Windows')
    def test_snapshot_rejects_backslash_directory(self):
        (self.root / 'folder\\archive').mkdir()
        self.assertEqual(self.run_cli('snapshot'), 2)
        self.assertFalse(self.manifest.exists())

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

    @unittest.skipUnless(hasattr(os, 'O_NOFOLLOW'), 'requires no-follow file opens')
    def test_reject_symlink_swapped_in_just_before_open(self):
        target = self.root / 'note.txt'
        outside = self.base / 'private.txt'
        outside.write_text('private example', encoding='utf-8')
        original_open = os.open
        swapped = False

        def swap_before_open(path, flags, *args, **kwargs):
            nonlocal swapped
            if (Path(path) == target or (path == target.name and kwargs.get('dir_fd') is not None)) and not swapped:
                swapped = True
                target.unlink()
                target.symlink_to(outside)
            return original_open(path, flags, *args, **kwargs)

        with patch('backup_check.os.open', side_effect=swap_before_open):
            with self.assertRaises(OSError):
                scan(self.root)
        self.assertTrue(swapped)
        self.assertFalse(self.manifest.exists())

    def test_reject_replacement_between_stat_and_open(self):
        target = self.root / 'note.txt'
        original_open = os.open
        swapped = False

        def swap_before_open(path, flags, *args, **kwargs):
            nonlocal swapped
            if (Path(path) == target or (path == target.name and kwargs.get('dir_fd') is not None)) and not swapped:
                swapped = True
                replacement = self.base / 'replacement.txt'
                replacement.write_text('hello', encoding='utf-8')
                os.replace(replacement, target)
            return original_open(path, flags, *args, **kwargs)

        with patch('backup_check.os.open', side_effect=swap_before_open):
            with self.assertRaisesRegex(ValueError, 'File changed during scan'):
                scan(self.root)
        self.assertTrue(swapped)

    @unittest.skipUnless(hasattr(os, 'fwalk') and hasattr(os, 'O_NOFOLLOW'),
                         'requires descriptor-based directory walking')
    def test_reject_parent_directory_swap_during_file_open(self):
        nested = self.root / 'nested'
        nested.mkdir()
        (nested / 'inside.txt').write_text('original', encoding='utf-8')
        outside = self.base / 'outside'
        outside.mkdir()
        (outside / 'inside.txt').write_text('private example', encoding='utf-8')
        original_open = os.open
        swapped = False

        def swap_parent(path, flags, *args, **kwargs):
            nonlocal swapped
            if path == 'inside.txt' and kwargs.get('dir_fd') is not None and not swapped:
                swapped = True
                nested.rename(self.base / 'moved')
                nested.symlink_to(outside, target_is_directory=True)
            return original_open(path, flags, *args, **kwargs)

        with patch('backup_check.os.open', side_effect=swap_parent):
            with self.assertRaisesRegex(ValueError, 'Directory changed during scan'):
                scan(self.root)
        self.assertTrue(swapped)
        self.assertFalse(self.manifest.exists())

    @unittest.skipUnless(hasattr(os, 'fwalk') and hasattr(os, 'O_NOFOLLOW'),
                         'requires descriptor-based directory walking')
    def test_reject_nested_symlink_directory(self):
        outside = self.base / 'outside'
        outside.mkdir()
        (outside / 'secret.txt').write_text('private example', encoding='utf-8')
        (self.root / 'nested').symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'Links and junctions are not supported'):
            scan(self.root)

    def test_invalid_manifest_and_missing_directory(self):
        self.manifest.write_text('{')
        self.assertEqual(self.run_cli('verify'), 2)
        self.root = self.base / 'absent'
        self.assertEqual(self.run_cli('snapshot'), 2)

    def test_reject_traversal_manifest(self):
        self.manifest.write_text(json.dumps({'version': 1, 'algorithm': 'sha256', 'files': {'../secret': 'a' * 64}}))
        with self.assertRaises(ValueError):
            load_manifest(self.manifest)


    def test_reject_duplicate_json_keys(self):
        digest = 'a' * 64
        examples = (
            '{"version":1,"version":1,"algorithm":"sha256","files":{}}',
            '{"version":1,"algorithm":"sha256","files":{},"files":{}}',
            '{"version":1,"algorithm":"sha256","files":'
            '{"note.txt":"' + digest + '","note.txt":"' + digest + '"}}',
        )
        for content in examples:
            with self.subTest(content=content):
                self.manifest.write_text(content, encoding='utf-8')
                with self.assertRaisesRegex(ValueError, 'Duplicate manifest key'):
                    load_manifest(self.manifest)
                self.assertEqual(self.run_cli('verify'), 2)

    def test_reject_boolean_manifest_version(self):
        self.manifest.write_text(
            '{"version":true,"algorithm":"sha256","files":{}}',
            encoding='utf-8',
        )
        with self.assertRaisesRegex(ValueError, 'Unsupported manifest format'):
            load_manifest(self.manifest)
        self.assertEqual(self.run_cli('verify'), 2)

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

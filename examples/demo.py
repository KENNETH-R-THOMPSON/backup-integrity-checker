"""Run a repeatable backup check with synthetic files in a temporary folder."""
import csv
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory


CHECKER = Path(__file__).resolve().parents[1] / 'backup_check.py'


def run_checker(command, source, baseline, report_format=None):
    arguments = [sys.executable, str(CHECKER), command, str(source), str(baseline)]
    if report_format:
        arguments.extend(['--format', report_format])
    return subprocess.run(
        arguments,
        capture_output=True, text=True, check=False,
    )


def main():
    with TemporaryDirectory(prefix='backup-demo-') as temporary:
        workspace = Path(temporary)
        source = workspace / 'example_files'
        (source / 'nested').mkdir(parents=True)
        (source / 'inventory.csv').write_text('item,quantity\nrouter,2\n', encoding='utf-8')
        (source / 'note.txt').write_text('Fictional test data\n', encoding='utf-8')
        (source / 'nested' / 'guide.txt').write_text('Demo only\n', encoding='utf-8')
        baseline = workspace / 'baseline.json'

        snapshot = run_checker('snapshot', source, baseline)
        if snapshot.returncode != 0:
            raise RuntimeError('Snapshot failed: ' + snapshot.stderr.strip())
        if snapshot.stdout.strip() != 'Recorded 3 files':
            raise RuntimeError('Unexpected snapshot count')
        print('Snapshot: recorded 3 synthetic files')

        backup_copy = workspace / 'backup_copy'
        shutil.copytree(source, backup_copy)
        copied = run_checker('verify', backup_copy, baseline)
        if copied.returncode != 0 or json.loads(copied.stdout) != {
            'missing': [], 'unexpected': [], 'changed': [], 'unchanged': 3,
        }:
            raise RuntimeError('Copied backup did not match the baseline')
        print('Copied backup: 3 unchanged (exit 0)')

        clean = run_checker('verify', source, baseline)
        if clean.returncode != 0:
            raise RuntimeError('Clean verification failed: ' + clean.stderr.strip())
        clean_report = json.loads(clean.stdout)
        if clean_report != {'missing': [], 'unexpected': [], 'changed': [], 'unchanged': 3}:
            raise RuntimeError('Unexpected clean verification report')
        print('Clean verification: 3 unchanged (exit 0)')

        (source / 'inventory.csv').write_text('item,quantity\nrouter,3\n', encoding='utf-8')
        (source / 'note.txt').unlink()
        (source / 'extra.txt').write_text('New fictional file\n', encoding='utf-8')
        changed = run_checker('verify', source, baseline)
        if changed.returncode != 1:
            raise RuntimeError('Expected difference exit code 1; got {}'.format(changed.returncode))
        report = json.loads(changed.stdout)
        expected = {
            'missing': ['note.txt'], 'unexpected': ['extra.txt'],
            'changed': ['inventory.csv'], 'unchanged': 1,
        }
        if report != expected:
            raise RuntimeError('Unexpected difference report: ' + repr(report))
        print('Changed verification: 1 unchanged, 1 changed, 1 missing, 1 unexpected (exit 1)')
        csv_result = run_checker('verify', source, baseline, 'csv')
        if csv_result.returncode != 1:
            raise RuntimeError('CSV verification should report differences with exit code 1')
        reader = csv.DictReader(io.StringIO(csv_result.stdout))
        rows = list(reader)
        expected_rows = [
            {'status': 'changed', 'path': 'inventory.csv'},
            {'status': 'missing', 'path': 'note.txt'},
            {'status': 'unexpected', 'path': 'extra.txt'},
            {'status': 'unchanged', 'path': 'nested/guide.txt'},
        ]
        if reader.fieldnames != ['status', 'path'] or rows != expected_rows:
            raise RuntimeError('Unexpected CSV verification report: ' + repr(rows))
        print('CSV verification: 4 file statuses checked (exit 1)')
        print(csv_result.stdout.rstrip())
        print('Changed: inventory.csv')
        print('Missing: note.txt')
        print('Unexpected: extra.txt')

        restored = workspace / 'restored_files'
        shutil.copytree(backup_copy, restored)
        restored_check = run_checker('verify', restored, baseline)
        if restored_check.returncode != 0 or json.loads(restored_check.stdout) != {
            'missing': [], 'unexpected': [], 'changed': [], 'unchanged': 3,
        }:
            raise RuntimeError('Restored copy did not match the baseline')
        if (restored / 'note.txt').read_text(encoding='utf-8') != 'Fictional test data\n':
            raise RuntimeError('Restored sample content differs')
        if (source / 'note.txt').exists():
            raise RuntimeError('Restore exercise unexpectedly changed the source')
        print('Synthetic restore: 3 files verified in a separate folder (exit 0)')
        print('Demo complete. Temporary files were cleaned up.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError) as error:
        print('Demo failed: {}'.format(error), file=sys.stderr)
        sys.exit(2)

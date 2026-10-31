"""Run a repeatable backup check with synthetic files in a temporary folder."""
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


CHECKER = Path(__file__).resolve().parents[1] / 'backup_check.py'


def run_checker(command, source, baseline):
    return subprocess.run(
        [sys.executable, str(CHECKER), command, str(source), str(baseline)],
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
        print('Changed: inventory.csv')
        print('Missing: note.txt')
        print('Unexpected: extra.txt')
        print('Demo complete. Temporary files were cleaned up.')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError) as error:
        print('Demo failed: {}'.format(error), file=sys.stderr)
        sys.exit(2)

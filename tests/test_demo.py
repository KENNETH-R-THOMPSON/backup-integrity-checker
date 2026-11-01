"""Smoke test the documented synthetic demonstration."""
from pathlib import Path
import subprocess
import sys
import unittest


class DemoTests(unittest.TestCase):
    def test_demo_reports_clean_and_modified_backups(self):
        root = Path(__file__).resolve().parents[1]
        result = subprocess.run(
            [sys.executable, str(root / 'examples' / 'demo.py')],
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('Copied backup: 3 unchanged (exit 0)', result.stdout)
        self.assertIn('Clean verification: 3 unchanged (exit 0)', result.stdout)
        self.assertIn('Changed verification: 1 unchanged, 1 changed, 1 missing, 1 unexpected (exit 1)', result.stdout)
        self.assertIn('CSV verification: 4 file statuses checked (exit 1)', result.stdout)
        self.assertIn('status,path\nchanged,inventory.csv\nmissing,note.txt\nunexpected,extra.txt\nunchanged,nested/guide.txt', result.stdout)
        self.assertIn('Synthetic restore: 3 files verified in a separate folder (exit 0)', result.stdout)
        self.assertIn('Demo complete. Temporary files were cleaned up.', result.stdout)


if __name__ == '__main__':
    unittest.main()

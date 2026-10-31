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
        self.assertIn('Clean verification: 3 unchanged (exit 0)', result.stdout)
        self.assertIn('Changed verification: 1 unchanged, 1 changed, 1 missing, 1 unexpected (exit 1)', result.stdout)
        self.assertIn('Demo complete. Temporary files were cleaned up.', result.stdout)


if __name__ == '__main__':
    unittest.main()

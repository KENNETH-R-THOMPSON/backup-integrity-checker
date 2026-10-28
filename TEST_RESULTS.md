# Test results

Local verification date: October 20, 2026.
Interpreter: Python 3.13.5.
Platform: Linux x86_64.

Command: `python3 -m unittest discover -s tests -v`
Result: 15 tests passed; 0 failures or errors.

Commands: `python3 backup_check.py snapshot sample <temporary>/baseline.json`, `python3 backup_check.py verify sample <temporary>/baseline.json`, and `python3 backup_check.py verify sample <temporary>/baseline.json --format text`.
Results: snapshot created one-file manifest; JSON verification reported 1 unchanged, 0 changed, 0 missing, 0 unexpected; text verification reported the same. All three commands returned exit code 0.

GitHub Actions status: unverified for the October 20 revision at the time of local testing. Review the corresponding commit workflow run for independent CI evidence.

The tests use synthetic files and simulated failures. They don't establish production reliability or backup restorability.

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

## Hosted GitHub Actions verification, October 31, 2026

The CSV reporting feature passed all 21 automated tests on Python 3.11 in merged-main CI: https://github.com/KENNETH-R-THOMPSON/backup-integrity-checker/actions/runs/41256443229 .

The updated synthetic demo, including checks for the four CSV file statuses, passed the unit-test job on hosted Python 3.11 in branch CI: https://github.com/KENNETH-R-THOMPSON/backup-integrity-checker/actions/runs/41261128427 . This run checked the code before the documentation-only edits in the same pull request. The demo uses temporary fictional files; no Mac execution or actual backup restoration was verified.

## Hosted cross-platform verification, November 1, 2026

[PR #10](https://github.com/KENNETH-R-THOMPSON/backup-integrity-checker/pull/10) expanded the Python 3.11 workflow to hosted Ubuntu, macOS, and Windows runners without changing application code or tests. [Merged-main CI](https://github.com/KENNETH-R-THOMPSON/backup-integrity-checker/actions/runs/41326447624) completed successfully on all three systems.

* Linux: 25 tests passed, 0 skipped.
* macOS: 25 tests passed, 0 skipped.
* Windows: 22 tests passed, 3 skipped because descriptor-based directory walking and `O_NOFOLLOW` aren't available in this environment.

The [PR workflow](https://github.com/KENNETH-R-THOMPSON/backup-integrity-checker/actions/runs/41326384018) also completed successfully. Hosted macOS CI isn't a test on my own Mac. No NAS integration or real backup restoration was performed.

## Windows junction checks and fictional restore, November 1, 2026

[PR #12](https://github.com/KENNETH-R-THOMPSON/backup-integrity-checker/pull/12) rejects Windows reparse points, including directory junctions, using no-follow metadata. A Windows-only test created nested and root junctions and confirmed that snapshots fail without publishing a manifest. [PR #13](https://github.com/KENNETH-R-THOMPSON/backup-integrity-checker/pull/13) expanded the temporary-file demo to verify a copied backup, alter the original folder, restore the copy elsewhere, and verify the restored hashes and a sample's contents.

[Successful merged-main CI](https://github.com/KENNETH-R-THOMPSON/backup-integrity-checker/actions/runs/41331757715) ran 27 tests on each Python 3.11 runner: 26 passed and one Windows-only test skipped on Linux and macOS; 24 passed and three Unix-specific tests skipped on Windows. The [PR run](https://github.com/KENNETH-R-THOMPSON/backup-integrity-checker/actions/runs/41331704075) passed on all three systems. The prior 25-test cross-platform results are historical.

This verifies a synthetic file-level restore exercise and common junction checks. It doesn't establish a real NAS restore, consistent application data, Windows path-walk race freedom, or testing on the owner's Mac.

## Path-based directory identity checks, November 1, 2026

[PR #15](https://github.com/KENNETH-R-THOMPSON/backup-integrity-checker/pull/15) added directory identity tracking between parent enumeration and child traversal, plus post-scan folder checks. Two regression tests exercise an unchanged nested folder and a simulated nested directory replacement. [PR CI](https://github.com/KENNETH-R-THOMPSON/backup-integrity-checker/actions/runs/41336786639) and [merged-main CI](https://github.com/KENNETH-R-THOMPSON/backup-integrity-checker/actions/runs/41336856797) completed successfully on Python 3.11.

* Linux: 29 tests run, 28 passed, 1 Windows-only skip.
* macOS: 29 tests run, 28 passed, 1 Windows-only skip.
* Windows: 29 tests run, 26 passed, 3 Unix-only skips.

These are hosted runner results using synthetic files and simulated replacements. Windows traversal remains path-based and vulnerable to some concurrent swaps. No real backup restore, owner Mac test or NAS integration was performed.

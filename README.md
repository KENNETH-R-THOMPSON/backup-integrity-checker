# Backup Integrity Checker

A Python command-line utility for checking whether files in a copied folder still match a saved SHA-256 baseline. It reports changed, missing, unexpected, and unchanged files. It reads source files without modifying them and uses only Python's standard library. All example data is synthetic.

## Setup and run

Requires Python 3.9 or newer. From the repository root:

```sh
python3 backup_check.py snapshot sample baseline.json
python3 backup_check.py verify sample baseline.json
python3 backup_check.py verify sample baseline.json --format text
python3 backup_check.py verify sample baseline.json --format csv > report.csv
python3 -m unittest discover -s tests -v
```

The first command creates `baseline.json` outside `sample`. Verification compares the sample against it. Snapshot creation refuses to replace an existing manifest. Use a fresh manifest filename for another snapshot. The manifest destination must support hard links and temporary file creation.

Exit codes: `0` for successful snapshot or unchanged verification, `1` for content differences, and `2` for invalid input, unstable source files, or filesystem errors. JSON verification output is the default; `--format text` prints a readable report. `--format csv` prints one row per file with `status,path` columns, including unchanged files. CSV fields use standard quoting for commas and quotes in filenames. Paths beginning with spreadsheet formula characters (`=`, `+`, `-`, `@`), including after leading whitespace, receive an apostrophe prefix in CSV output to reduce spreadsheet formula injection risk. This changes the displayed path value; the JSON report preserves the exact filenames. Treat CSV exports as reports, not as input manifests.

## Reproducible synthetic demo

Run `python3 examples/demo.py` from the repository root. The script creates three fictional files in a temporary directory, saves a baseline, checks an unchanged copy, then simulates one changed file, one missing file, and one unexpected file. It checks JSON and CSV reports and exit codes, then prints the four CSV file statuses. No personal files are read. Temporary files are cleaned up automatically.

This demo doesn't read your documents or prove that a real backup can be restored. The smoke test runs with `python3 -m unittest discover -s tests -v`.

## Concurrent-change detection

The scanner compares each file's device, inode, size, modification time, and change time before and after hashing. It checks both the open file and its path to detect common concurrent edits or file replacement. If a change is detected, it stops with exit code `2` rather than publishing a misleading baseline or verification report. Regression tests simulate an in-place edit, an atomic same-size replacement, and a change during verification.

## Design and limits

* SHA-256 hashing streams 1 MiB blocks rather than loading entire files into memory.
* Relative manifest paths allow checking a copied folder in another location.
* Symbolic links and nonregular files cause an error. Windows reparse points, including directory junctions, are also rejected before hashing. On Linux and macOS, `O_NOFOLLOW` rejects symlinks swapped into the final file path, and descriptor-based directory walking reduces parent-directory replacement risks. Windows uses path-based walking and file identity checks, so a concurrent directory replacement race remains possible. These checks don't make a multi-file scan atomic or prevent every adversarial rename.
* Manifest parsing rejects duplicate JSON keys and boolean version fields instead of accepting ambiguous baselines.
* Snapshot publishing syncs a temporary manifest and uses an exclusive hard link to preserve existing baselines and prevent partially written final manifests.
* Metadata checks protect each individual read. They don't guarantee a consistent multi-file snapshot or detect every adversarial modification. Use a stable filesystem snapshot for higher assurance.
* Empty directories, permissions, ownership, and timestamps aren't compared.
* A matching hash doesn't authenticate the baseline or prove that a backup can restore an application.
* The tool never repairs or deletes source files.
* CSV reports can include filenames. Review reports before sharing them, especially when working with private directories.

## Verified tests

On November 1, 2026 (Louisville time), [PR #10](https://github.com/KENNETH-R-THOMPSON/backup-integrity-checker/pull/10) added a Python 3.11 test matrix for hosted Linux, macOS, and Windows. The [merged-main GitHub Actions run](https://github.com/KENNETH-R-THOMPSON/backup-integrity-checker/actions/runs/41326447624) passed on all three systems. Linux and macOS each ran all 25 tests successfully. Windows ran 22 tests successfully and skipped three Unix-specific descriptor and `O_NOFOLLOW` tests, as expected. The [PR run](https://github.com/KENNETH-R-THOMPSON/backup-integrity-checker/actions/runs/41326384018) also passed on all three systems. The earlier [Linux-only 25-test run](https://github.com/KENNETH-R-THOMPSON/backup-integrity-checker/actions/runs/41273204067) is historical. These are hosted runner results; they don't establish testing on my own Mac, NAS, or a real backup restoration.

## Résumé bullets

* Built a Python backup integrity utility using streamed SHA-256 hashes, portable JSON manifests, and machine-readable verification reports.
* Implemented change and replacement detection during file hashing, plus strict JSON manifest parsing to reject duplicate entries and invalid version types.
* Added failure-safe manifest publishing, a repeatable fictional demo, and CSV reporting with formula-safe filenames; verified 25 tests on hosted Linux and macOS, plus 22 passing and three platform-specific skips on Windows.

## Interview demonstration

Run `python3 examples/demo.py` to show clean verification, then a changed, missing, unexpected, and unchanged file in a CSV report. Explain why the verification exits with code 1 after differences and why a trusted baseline and an actual restore test are separate checks.

Independent personal portfolio project. No school assignments, team ITAM systems, or patient records are included.

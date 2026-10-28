# Backup Integrity Checker

A Python command-line utility for checking whether files in a copied folder still match a saved SHA-256 baseline. It reports changed, missing, unexpected, and unchanged files. It reads source files without modifying them and uses only Python's standard library. All example data is synthetic.

## Setup and run

Requires Python 3.9 or newer. From the repository root:

```sh
python3 backup_check.py snapshot sample baseline.json
python3 backup_check.py verify sample baseline.json
python3 backup_check.py verify sample baseline.json --format text
python3 -m unittest discover -s tests -v
```

The first command creates `baseline.json` outside `sample`. Verification compares the sample against it. Snapshot creation refuses to replace an existing manifest. Use a fresh manifest filename for another snapshot. The manifest destination must support hard links and temporary file creation.

Exit codes: `0` for successful snapshot or unchanged verification, `1` for content differences, and `2` for invalid input, unstable source files, or filesystem errors. JSON verification output is the default; `--format text` prints a readable report.

## Concurrent-change detection

The scanner compares each file's device, inode, size, modification time, and change time before and after hashing. It checks both the open file and its path to detect common concurrent edits or file replacement. If a change is detected, it stops with exit code `2` rather than publishing a misleading baseline or verification report. Regression tests simulate an in-place edit, an atomic same-size replacement, and a change during verification.

## Design and limits

* SHA-256 hashing streams 1 MiB blocks rather than loading entire files into memory.
* Relative manifest paths allow checking a copied folder in another location.
* Symbolic links and nonregular files cause an error.
* Snapshot publishing syncs a temporary manifest and uses an exclusive hard link to preserve existing baselines and prevent partially written final manifests.
* Metadata checks protect each individual read. They don't guarantee a consistent multi-file snapshot or detect every adversarial modification. Use a stable filesystem snapshot for higher assurance.
* Empty directories, permissions, ownership, and timestamps aren't compared.
* A matching hash doesn't authenticate the baseline or prove that a backup can restore an application.
* The tool never repairs or deletes source files.

## Verified tests

On October 20, 2026, all 15 automated tests passed locally with Python 3.13.5 on Linux. A sample snapshot and JSON verification also passed. See `TEST_RESULTS.md` for the commands and results. GitHub Actions status is tracked separately; local results don't establish CI success.

## Résumé bullets

* Built a Python backup integrity utility using streamed SHA-256 hashes, portable JSON manifests, and machine-readable verification reports.
* Implemented change and replacement detection during file hashing, with regression tests for concurrent edits, same-size replacements, and verification errors.
* Added failure-safe manifest publishing and validated 15 automated tests using Python's standard library.

## Interview demonstration

Create a baseline for `sample`, verify it, edit the CSV, and run verification again. Explain the difference between a hash mismatch and an unstable file detected during scanning. Discuss why a filesystem snapshot and a trusted baseline matter for reliable backup verification.

Independent personal portfolio project. No school assignments, team ITAM systems, or patient records are included.

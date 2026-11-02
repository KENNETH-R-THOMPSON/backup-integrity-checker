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

Run `python3 examples/demo.py` from the repository root. The script creates three fictional files in a temporary directory, saves a baseline, copies the folder as a synthetic backup, and verifies that copy. It then changes and removes files in the original folder, verifies the differences, and copies the saved backup into a separate restore folder. The restored copy must match the original baseline and sample content. It checks JSON and CSV reports and exit codes. No personal files are read, and temporary files are cleaned up automatically.

This is a small file-level copy and restore exercise using invented files. It doesn't test a NAS, permissions, application databases, or restoration of a real backup. The smoke test runs with `python3 -m unittest discover -s tests -v`.

## Concurrent-change detection

The scanner compares each file's device, inode, size, modification time, and change time before and after hashing. It checks both the open file and its path to detect common concurrent edits or file replacement. If a change is detected, it stops with exit code `2` rather than publishing a misleading baseline or verification report. Regression tests simulate an in-place edit, an atomic same-size replacement, and a change during verification.

## Design and limits

* SHA-256 hashing streams 1 MiB blocks rather than loading entire files into memory.
* Relative manifest paths allow checking a copied folder in another location.
* Snapshot creation rejects Unix filenames and directory names containing a literal backslash. The manifest uses forward-slash paths, and a backslash would make the saved baseline fail validation during verification. The tool reports an error before writing that baseline.
* Symbolic links and nonregular files cause an error. Windows reparse points, including directory junctions, are also rejected before hashing. On Linux and macOS, `O_NOFOLLOW` rejects symlinks swapped into the final file path, and descriptor-based directory walking reduces parent-directory replacement risks. On Windows, path-based walking also checks each directory's identity against its parent listing and rechecks the folder after processing. This catches some nested replacements, but concurrent path swaps remain possible. A multi-file scan isn't atomic.
* Manifest parsing rejects duplicate JSON keys and boolean version fields instead of accepting ambiguous baselines.
* Snapshot publishing syncs a temporary manifest and uses an exclusive hard link to preserve existing baselines and prevent partially written final manifests.
* Metadata checks protect each individual read. They don't guarantee a consistent multi-file snapshot or detect every adversarial modification. Use a stable filesystem snapshot for higher assurance.
* Empty directories, permissions, ownership, and timestamps aren't compared.
* A matching hash doesn't authenticate the baseline or prove that a backup can restore an application.
* The tool never repairs or deletes source files.
* CLI errors escape terminal control characters, Unicode formatting characters and unpaired surrogates in untrusted filenames or filesystem error text. Ordinary filenames remain readable. This doesn't make a file safe to open.
* CSV reports can include filenames. Review reports before sharing them, especially when working with private directories.

## Verified tests

On November 1, 2026, [PR #17](https://github.com/KENNETH-R-THOMPSON/backup-integrity-checker/pull/17) fixed a snapshot portability bug: Unix filenames or directories with a literal backslash could produce manifests that verification later rejected. Two regression tests cover the failure and confirm no baseline is published. All 31 tests ran on hosted Python 3.11 in [merged-main GitHub Actions](https://github.com/KENNETH-R-THOMPSON/backup-integrity-checker/actions/runs/41341400605): Linux and macOS passed 30 with one Windows-only skip each; Windows passed 26 with five expected Unix-specific skips. The [PR workflow](https://github.com/KENNETH-R-THOMPSON/backup-integrity-checker/actions/runs/41341333747) also passed on all three systems. The earlier [29-test run](https://github.com/KENNETH-R-THOMPSON/backup-integrity-checker/actions/runs/41336856797) is historical. Hosted testing doesn't establish testing on my own Mac or NAS, restoration of a real backup, or complete protection against concurrent path replacement.

## Résumé bullets

* Built a Python backup integrity utility using streamed SHA-256 hashes, portable JSON manifests, and machine-readable verification reports.
* Implemented change and replacement detection during file hashing, plus strict JSON manifest parsing to reject duplicate entries and invalid version types.
* Added failure-safe manifest publishing, a repeatable fictional demo, and CSV reporting with formula-safe filenames; verified a 31-test suite on hosted Linux, macOS and Windows, with platform-specific skips.

## Interview demonstration

Run `python3 examples/demo.py` to show clean verification, then a changed, missing, unexpected, and unchanged file in a CSV report. Explain why the verification exits with code 1 after differences and why a trusted baseline and an actual restore test are separate checks.

Independent personal portfolio project. No school assignments, team ITAM systems, or patient records are included.

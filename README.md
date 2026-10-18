# Backup Integrity Checker

A personal portfolio utility that answers a practical question: did the files in a copied folder keep the same contents?

It records SHA-256 fingerprints, then reports changed, missing, unexpected, and unchanged files. No third-party packages, network access, or real patient data are needed.

## Run

Requires Python 3.9 or newer. Run these commands from this project's folder:

```sh
python3 backup_check.py snapshot sample baseline.json
python3 backup_check.py verify sample baseline.json
python3 -m unittest discover -s tests -v
```

The first command creates a baseline. The second prints a JSON report with one unchanged file and empty difference lists. Copy `sample` to a temporary folder, edit its CSV, then verify that folder with the same baseline to see a changed file reported.

Exit codes: `0` means success or no differences, `1` means differences found, and `2` means input or filesystem errors. Existing baselines cannot be overwritten. Store the manifest outside the folder being checked.

## Readable report

For an interview demonstration or a quick check, use:

```sh
python3 backup_check.py verify sample baseline.json --format text
```

This prints category counts and quoted filenames. JSON remains the default for scripts. Both formats use the same exit codes.

## IntelliJ IDEA

Open this folder as a project. Use its terminal to run the commands above. A Python editor integration is optional; the program and tests run with the system Python interpreter.

## Design and limits

* Hashes are streamed in 1 MiB chunks to avoid loading large files into memory.
* Relative paths let a baseline verify a copy in another location.
* Symbolic links and nonregular files cause an error instead of silently leaving gaps.
* Snapshot creation writes and syncs a temporary file before publishing the baseline with an exclusive hard link. Interrupted writes won't leave a partial baseline at the requested path, and existing baselines are preserved.
* The manifest destination must support hard links and allow temporary file creation in the same directory. Unsupported filesystems return exit code `2` without creating the baseline.
* Empty directories, permissions, ownership, and timestamps are not compared.
* Use a stable directory or filesystem snapshot. Concurrent changes during scanning are not supported.
* Protect your baseline separately. This tool detects content differences; it does not prove that a baseline is authentic or that a backup can restore an application.
* The tool never repairs or deletes source files.

## Test results

On October 18, 2026, all 12 automated tests passed locally with Python 3.13.5. Tests cover snapshot verification, changed files, malformed manifests, nested Unicode paths, symlinks, baseline replacement protection, and cleanup after simulated write and publish failures. GitHub Actions status should be checked separately.

## Portfolio talking points

Implemented a Python command-line utility that compares streamed SHA-256 manifests and produces machine-readable backup verification reports. Added failure-safe baseline publishing that preserves existing manifests and cleans up temporary files after write errors. Validated behavior with 12 automated tests.

Interview demo: create a baseline, verify an unchanged copy, edit a file, and explain why a mismatch signals investigation rather than proving malicious activity. Discuss streaming versus reading entire files, atomic publication versus durability, and why a trusted baseline matters.

## Next improvements

* Stable snapshot integration and detection of files modified during scanning.
* Filesystem compatibility checks for locations that do not support hard links.

This is an independent personal portfolio project, separate from school and team repositories.

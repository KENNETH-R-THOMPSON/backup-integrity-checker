# Changelog

## 2026-09-24

Initial implementation with snapshot and verify commands, synthetic sample data, and nine passing tests. An initial test invocation from the parent workspace could not import the module; running from the documented project directory resolved the working-directory issue. No algorithm changes were needed for that failure.

## 2026-09-26

Added `verify --format text` for readable category counts and filenames, preserving the default JSON output and exit codes. Ten tests pass. Repository renamed to `backup-integrity-checker` with history preserved.

## 2026-10-18

Snapshot publishing now writes a temporary manifest in the destination directory, syncs its contents, and publishes it with an exclusive hard link. This prevents incomplete final manifests after a write failure and continues to protect existing baselines from replacement. Added two regression tests for simulated write and publish failures. All 12 tests passed locally with Python 3.13.5. GitHub Actions was not yet verified.

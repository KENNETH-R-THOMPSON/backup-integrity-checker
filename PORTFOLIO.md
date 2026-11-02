# Personal software and cybersecurity portfolio

These are AI-assisted personal practice projects using fictional examples. Each repository contains the source code, setup instructions, tests, and limitations. The GitHub Actions results below came from hosted runners, not my own Mac or NAS.

## Backup Integrity Checker (Python)

[Repository](https://github.com/KENNETH-R-THOMPSON/backup-integrity-checker)

Checks a copied folder against a saved SHA-256 manifest and reports changed, missing, and extra files. It detects common file changes during hashing, rejects links and junctions, and includes a temporary-file copy-and-restore exercise. I added terminal-safe error messages for untrusted filenames in [PR #19](https://github.com/KENNETH-R-THOMPSON/backup-integrity-checker/pull/19). Two regression tests raised the suite to 33. [Merged-main Python 3.11 CI](https://github.com/KENNETH-R-THOMPSON/backup-integrity-checker/actions/runs/41372752361) passed: 32 tests and one skip on Linux and macOS; 28 tests and five skips on Windows. A real restore, NAS use, and owner Mac testing remain unverified.

## Security Log Explorer (Java 17)

[Repository](https://github.com/KENNETH-R-THOMPSON/security-log-explorer)

Reads fictional sign-in logs and flags addresses with repeated failures. Supports rolling time windows, quoted CSV, UTF-8 BOM headers, and JSON reports. CLI and text output escape unsafe characters. All 71 checks and sample demonstrations passed in [hosted Java 17 CI](https://github.com/KENNETH-R-THOMPSON/security-log-explorer/actions/runs/41362268297) on November 1, 2026. Live monitoring and owner Mac testing remain unverified.

## Document Intake Automation (C#/.NET 10)

[Repository](https://github.com/KENNETH-R-THOMPSON/document-intake-automation)

Previews file sorting, copies fictional documents into category folders, and checks copied contents using SHA-256. The read-only exact verification mode detects extra files and empty destination folders. The Release build, all 27 tests, and fictional CLI examples passed on hosted Linux, macOS, and Windows in [merged-main CI](https://github.com/KENNETH-R-THOMPSON/document-intake-automation/actions/runs/41357277707). Owner Mac/NAS testing and real document verification remain unverified.

## Sharing status

These are public personal repositories suitable for reviewing code and limitations. LinkedIn Projects and Featured publication haven't been verified. School assignments, team work, patient records, credentials, and private documents stay outside public project repositories.

Last reviewed: November 1, 2026.

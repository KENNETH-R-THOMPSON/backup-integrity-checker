# Kenneth Thompson | Software and Cybersecurity Projects

Projects available for review. Code, setup instructions, test notes, and limitations are in each repository.

## Backup Integrity Checker (Python)
[Source and documentation](https://github.com/KENNETH-R-THOMPSON/backup-integrity-checker)

Checks copied files against SHA-256 hashes and reports missing, changed, or extra files. It detects common changes during hashing and rejects Windows directory junctions and reparse points. A temporary-file demo verifies a fictional backup copy, changes the original, and verifies a restored copy in another folder. [PR #12](https://github.com/KENNETH-R-THOMPSON/backup-integrity-checker/pull/12) and [PR #13](https://github.com/KENNETH-R-THOMPSON/backup-integrity-checker/pull/13) passed [merged-main Python 3.11 CI](https://github.com/KENNETH-R-THOMPSON/backup-integrity-checker/actions/runs/41331757715): 26 passed and one skipped on hosted Linux and macOS, 24 passed and three skipped on Windows. A real restore, NAS use, and testing on my own Mac remain unverified.

## Security Log Explorer (Java)
[Source and documentation](https://github.com/KENNETH-R-THOMPSON/security-log-explorer)

Reads example sign-in activity and identifies addresses with repeated failed login attempts. Supports rolling time windows and works in IntelliJ IDEA. All 69 automated checks and the fictional CSV demonstrations passed on hosted Java 17 on November 1, 2026: https://github.com/KENNETH-R-THOMPSON/security-log-explorer/actions/runs/41321230535 . This doesn't establish live monitoring or testing on my own Mac.

## Document Intake Automation (C#)
[Source and documentation](https://github.com/KENNETH-R-THOMPSON/document-intake-automation)

Previews how files would be organized, copies them into category folders, and checks file hashes. Original files remain unchanged. Includes a local test runner; .NET Release build, 19 tests, and the fictional preview passed on hosted Linux, macOS, and Windows in GitHub Actions on October 31, 2026: https://github.com/KENNETH-R-THOMPSON/document-intake-automation/actions/runs/41188712552 . Owner Mac testing remains unverified.

## How to review the work
Each project includes its own README, sample data, usage instructions and limitations. The sample files are fictional and intended for learning and demonstrations.

I keep personal school assignments and team repositories separate. School work will be added only after its requirements and testing are complete, and team work requires permission before publication.

*Last reviewed: November 1, 2026.*

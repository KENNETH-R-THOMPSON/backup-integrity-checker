# Kenneth Thompson | Software and Cybersecurity Projects

Projects available for review. Code, setup instructions, test notes, and limitations are in each repository.

## Backup Integrity Checker (Python)
[Source and documentation](https://github.com/KENNETH-R-THOMPSON/backup-integrity-checker)

Checks copied files against SHA-256 hashes and reports missing, changed, or extra files. Includes safety checks for files that change during scanning. The project includes a temporary-file demo that checks JSON and CSV reports for changed, missing, unexpected, and unchanged files. All 21 tests passed on hosted Python 3.11 in GitHub Actions on October 31, 2026: https://github.com/KENNETH-R-THOMPSON/backup-integrity-checker/actions/runs/41261128427 . A real backup restoration and testing on my Mac remain unverified.

## Security Log Explorer (Java)
[Source and documentation](https://github.com/KENNETH-R-THOMPSON/security-log-explorer)

Reads example sign-in activity and identifies addresses with repeated failed login attempts. Supports rolling time windows and works in IntelliJ IDEA. The project documents 37 local checks. Java 17 GitHub Actions passed on October 30, 2026: https://github.com/KENNETH-R-THOMPSON/security-log-explorer/actions/runs/41163980810

## Document Intake Automation (C#)
[Source and documentation](https://github.com/KENNETH-R-THOMPSON/document-intake-automation)

Previews how files would be organized, copies them into category folders, and checks file hashes. Original files remain unchanged. Includes a local test runner; .NET release build, regression tests and sample preview passed in GitHub Actions on October 30, 2026: https://github.com/KENNETH-R-THOMPSON/document-intake-automation/actions/runs/41163861050

## How to review the work
Each project includes its own README, sample data, usage instructions and limitations. The sample files are fictional and intended for learning and demonstrations.

I keep personal school assignments and team repositories separate. School work will be added only after its requirements and testing are complete, and team work requires permission before publication.

*Last reviewed: October 31, 2026.*

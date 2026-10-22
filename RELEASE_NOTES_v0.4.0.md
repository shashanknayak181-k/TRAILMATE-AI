# TrailMate AI v0.4.0 — Engineering Reliability Release

This release focuses on making local setup and verification more diagnosable. It does not claim to add live traffic, weather, booking, or Google Maps integrations.

## Changes
- Setup checks Python and Node availability and Python version.
- Native command failures are checked explicitly, so a failed `pip install`, `npm ci`, build, migration, or test run cannot silently be reported as successful.
- Frontend dependencies use `npm ci` when a lockfile exists.
- Frontend production build and backend tests run during setup.
- Backend startup verifies imports before running migrations and Uvicorn.
- Clearer remediation messages for missing backend dependencies.
- Added a hackathon demo flow and release acceptance checklist.

## Verification status
The package's scripts were reviewed and updated. This environment has not completed a fresh Windows PowerShell run, a clean npm install, or browser-based end-to-end verification. Run `setup-local.ps1` on the target Windows machine and retain the actual output as the release verification record.

# Run TRAILMATE AI locally (Windows)

## Requirements
- Python 3.11 or newer
- Node.js 20 or newer (includes npm)
- Internet access for the first dependency installation
- Windows PowerShell

For local development the app uses SQLite. PostgreSQL is intended for deployment; `backend/requirements.txt` includes its driver, while `backend/requirements-local.txt` avoids downloading an unused PostgreSQL driver for SQLite-only local runs.

## 1. Extract the ZIP
Extract the project folder somewhere writable, for example `C:\Users\YOUR_NAME\Projects\trailmate-ai`. Do not run commands from the ZIP preview or from its parent directory.

## 2. Install dependencies and prepare the database
Open PowerShell in the extracted `trailmate-ai` folder and run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\setup-local.ps1
```

This creates a Python virtual environment, installs backend packages, installs npm packages, copies `.env.example` to `.env` if needed, applies Alembic migrations, and runs backend tests. Initial installation requires internet access.

## 3. Start the backend
Open a PowerShell terminal in the project root:

```powershell
.\start-backend.ps1
```

Check `http://127.0.0.1:8000/health` and open API docs at `http://127.0.0.1:8000/docs`.

## 4. Start the frontend
Open a SECOND PowerShell terminal in the same project root:

```powershell
.\start-frontend.ps1
```

Open `http://localhost:5173` in your browser. Keep both terminals running.

## Troubleshooting
- `python` not found: install Python 3.11+ and enable the PATH option in the installer.
- `npm` not found: install Node.js 20+ and reopen PowerShell.
- Execution policy error: run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal only.
- Dependency download fails: check internet/proxy/firewall and rerun `.\setup-local.ps1`; do not delete the source code. `npm install` must complete before the frontend can start.
- Port 8000 or 5173 in use: stop the other process or change the port in the relevant startup command/configuration.
- Development email verification and password reset codes are not sent by email. They are available only through development-mode behavior; never deploy this configuration publicly.

@echo off
REM Weekly report-only sync. Appends the pending-entry decision table to
REM state\sync-report.log. Creates nothing: --dry-run makes no WordPress call
REM and writes no ledger entry, so this can never publish or draft anything.
REM
REM Registered as the scheduled task "blog-engine weekly report".
REM Runs Sunday 09:00 local — deliberately clear of the 03:00-05:00
REM America/Los_Angeles window reserved for the earnings-summary pipeline.

cd /d "%~dp0.."
if not exist "state" mkdir "state"

echo.>> "state\sync-report.log"
echo ===== %DATE% %TIME% =====>> "state\sync-report.log"
".venv\Scripts\blog-engine.exe" sync --source all --dry-run >> "state\sync-report.log" 2>&1

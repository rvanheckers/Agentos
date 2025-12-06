@echo off
REM AgentOS Endpoint Health Check Runner voor Windows
REM Dubbelklik dit bestand om de endpoint check te draaien

echo 🚀 Starting AgentOS Endpoint Health Checker...
echo.

REM Change to the script directory
cd /d "%~dp0"

REM Run the Python script
python run_endpoint_check.py

REM Keep terminal open to see results
echo.
echo Press any key to close...
pause >nul
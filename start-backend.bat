@echo off
title CampusVerse FastAPI Backend (Port 5000)
echo ========================================================
echo Starting CampusVerse FastAPI Backend on http://localhost:5000
echo API Docs: http://localhost:5000/docs
echo ========================================================
cd /d "%~dp0backend"
python -m uvicorn main:app --reload --port 5000
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Backend failed with error code %ERRORLEVEL%.
    pause
)

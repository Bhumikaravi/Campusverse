@echo off
echo ========================================================
echo Starting CampusVerse (FastAPI + Vite Frontend)
echo ========================================================

echo [1/2] Starting FastAPI Backend on http://localhost:5000 ...
start "CampusVerse FastAPI Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn main:app --reload --port 5000"

echo [2/2] Starting Vite Frontend on http://localhost:5173 ...
start "CampusVerse Vite Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo ========================================================
echo Both servers have been launched in separate windows!
echo Web App: http://localhost:5173
echo API Docs: http://localhost:5000/docs
echo ========================================================
pause

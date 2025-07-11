@echo off
setlocal

git remote show upstream >nul 2>nul
if %errorlevel% neq 0 (
    git remote add upstream https://github.com/abaire/xemu-perf-tester_results.git
)

git checkout main
git pull upstream main
git push origin main

set "VENV_DIR=venv"
if not exist "%VENV_DIR%" (
    call run.bat
)

%VENV_DIR%\Scripts\pip3.exe install -r requirements.txt

endlocal

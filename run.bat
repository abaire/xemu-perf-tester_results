@ECHO OFF

SETLOCAL

python --version >NUL 2>NUL
IF %ERRORLEVEL% NEQ 0 (
    ECHO ERROR: Python is not installed or not found in your PATH.
    ECHO Please install Python ^(e.g., from python.org or by running `python` with no arguments^) and ensure it's added to your system PATH.
    EXIT /B 1
)

FOR /F "tokens=2" %%V IN ('python --version 2^>^&1') DO (
    SET "PYTHON_VERSION=%%V"
)

FOR /F "tokens=1,2 delims=." %%A IN ("%PYTHON_VERSION%") DO (
    SET "MAJOR_VER=%%A"
    SET "MINOR_VER=%%B"
)

IF %MAJOR_VER% LSS 3 (
    GOTO VERSION_FAIL
)

IF %MAJOR_VER% EQU 3 IF %MINOR_VER% LSS 10 (
    GOTO VERSION_FAIL
)
GOTO VERSION_PASS
:VERSION_FAIL
ECHO ERROR: Python 3.10 or higher is required. Found version %PYTHON_VERSION%.
ECHO Please upgrade your Python installation.
EXIT /B 1
:VERSION_PASS

IF NOT EXIST "venv\" (
    ECHO Creating Python virtual environment...

    python -m venv venv
    IF %ERRORLEVEL% NEQ 0 (
        ECHO ERROR: Failed to create virtual environment.
        ECHO Make sure Python is installed and accessible in your PATH.
        EXIT /B 1
    )

    ECHO Installing required packages from requirements.txt...

    "venv\Scripts\pip.exe" install -r requirements.txt
    IF %ERRORLEVEL% NEQ 0 (
        ECHO ERROR: Failed to install Python packages.
        EXIT /B 1
    )

    ECHO.
    ECHO Initial setup complete.
    ECHO Please run this command to import your settings:
    ECHO   run.bat --import-install ^<path_to_your_xemu_toml_file^>
    EXIT /B 1
)

CALL "venv\Scripts\activate.bat"

xemu-perf-run %*

ENDLOCAL

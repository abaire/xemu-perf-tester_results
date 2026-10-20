@ECHO OFF

REM Runs the benchmarks against the CI build of one or more xemu pull requests and submits the results.
REM
REM Usage: run_pr.bat <pr_url_or_number> [<pr_url_or_number> ...] [-- <extra run.bat arguments>]
REM   e.g., run_pr.bat https://github.com/xemu-project/xemu/pull/3088
REM         run_pr.bat 3088 3090 -- --just-suites FillRate

SETLOCAL ENABLEDELAYEDEXPANSION

SET "PRS="
SET "EXTRA_ARGS="
SET "IN_EXTRA="

:PARSE_ARGS
IF "%~1"=="" GOTO ARGS_DONE
IF DEFINED IN_EXTRA (
    SET "EXTRA_ARGS=!EXTRA_ARGS! %1"
) ELSE IF "%~1"=="--" (
    SET "IN_EXTRA=1"
) ELSE (
    SET "ARG=%~1"
    ECHO !ARG!| FINDSTR /R "^[0-9][0-9]*$" >NUL
    IF !ERRORLEVEL! EQU 0 (
        SET "PRS=!PRS! https://github.com/xemu-project/xemu/pull/!ARG!"
    ) ELSE (
        ECHO !ARG!| FINDSTR /R "^https://github.com/[^/]*/[^/]*/pull/[0-9]" >NUL
        IF !ERRORLEVEL! NEQ 0 (
            ECHO !ARG!| FINDSTR /R "^https://github.com/[^/]*/[^/]*/actions/runs/[0-9]" >NUL
            IF !ERRORLEVEL! NEQ 0 (
                ECHO Unrecognized PR '!ARG!'. Expected a PR number or URL like https://github.com/xemu-project/xemu/pull/3088
                EXIT /B 1
            )
        )
        SET "PRS=!PRS! !ARG!"
    )
)
SHIFT
GOTO PARSE_ARGS

:ARGS_DONE
IF "%PRS%"=="" (
    ECHO Usage: run_pr.bat ^<pr_url_or_number^> [...] [-- ^<extra run.bat arguments^>]
    EXIT /B 1
)

REM PR support requires a newer xemu-perf-tester than older installs may have.
IF EXIST "%~dp0venv\" (
    "%~dp0venv\Scripts\pip.exe" install -q --upgrade -r "%~dp0requirements.txt"
)

FOR %%P IN (%PRS%) DO (
    ECHO Testing %%P
    CALL "%~dp0run.bat" --xemu-tag %%P %EXTRA_ARGS%
    IF !ERRORLEVEL! NEQ 0 EXIT /B !ERRORLEVEL!
    CALL "%~dp0run.bat" --xemu-tag %%P --use-vulkan %EXTRA_ARGS%
    IF !ERRORLEVEL! NEQ 0 EXIT /B !ERRORLEVEL!
)

ENDLOCAL

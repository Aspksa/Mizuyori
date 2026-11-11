@echo off
rem ============================================================
rem  Mizuyori launcher
rem  This file is ASCII-only on purpose: Cyrillic text inside
rem  .bat files breaks cmd.exe depending on the code page.
rem  All Russian text is printed by Python (main.py).
rem ============================================================
setlocal EnableExtensions DisableDelayedExpansion
cd /d "%~dp0"
title Mizuyori

rem Project folder WITHOUT trailing backslash (a trailing \ before a
rem closing quote breaks argument parsing in many programs).
set "ROOT=%~dp0"
set "ROOT=%ROOT:~0,-1%"

set "PYDIR=%ROOT%\python"
set "VENV=%ROOT%\.venv"
set "PYEXE="
set "ENVDIR="

rem Python: UTF-8 everywhere, no pip nagging
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"

rem ---- 1. Portable Python already downloaded? -----------------
if exist "%PYDIR%\.ready" goto use_portable

rem ---- 2. Virtual environment already created? ---------------
if exist "%VENV%\Scripts\python.exe" goto use_venv

rem ---- 3. System Python 3.10+ installed? ----------------------
call :find_system
if defined SYSPY goto make_venv
goto download

rem ============================================================
:find_system
set "SYSPY="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul && set "SYSPY=py -3" && exit /b 0
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>nul && set "SYSPY=python" && exit /b 0
exit /b 0

rem ============================================================
:make_venv
echo [Mizuyori] Creating virtual environment...
%SYSPY% -m venv "%VENV%"
if not errorlevel 1 goto use_venv
echo [Mizuyori] venv failed, switching to portable Python.
rmdir /s /q "%VENV%" >nul 2>nul
goto download

:use_venv
set "PYEXE=%VENV%\Scripts\python.exe"
set "ENVDIR=%VENV%"
goto deps

rem ============================================================
:download
echo [Mizuyori] Python 3.10+ not found. Downloading portable Python...
powershell -NoProfile -ExecutionPolicy Bypass -File "%ROOT%\tools\get-python.ps1"
if errorlevel 1 goto fail
if not exist "%PYDIR%\.ready" goto fail

:use_portable
set "PYEXE=%PYDIR%\python.exe"
set "ENVDIR=%PYDIR%"
goto deps

rem ============================================================
:deps
if not exist "%ROOT%\requirements.txt" goto run
fc /b "%ROOT%\requirements.txt" "%ENVDIR%\requirements.installed" >nul 2>nul
if not errorlevel 1 goto run
echo [Mizuyori] Installing dependencies...
"%PYEXE%" -m pip install -q --no-warn-script-location -r "%ROOT%\requirements.txt"
if errorlevel 1 goto fail
copy /y "%ROOT%\requirements.txt" "%ENVDIR%\requirements.installed" >nul

rem ============================================================
:run
"%PYEXE%" "%ROOT%\main.py" %*
if errorlevel 1 goto fail
endlocal
exit /b 0

:fail
echo.
echo [Mizuyori] Something went wrong. See the error message above.
pause
endlocal
exit /b 1

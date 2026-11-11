@echo off
rem Mizuyori. This file is ASCII-only on purpose: Cyrillic inside .bat
rem breaks cmd.exe. All logic and Russian messages are in tools\launch.ps1
setlocal
cd /d "%~dp0"
title Mizuyori
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\launch.ps1" %*
if errorlevel 1 pause
endlocal

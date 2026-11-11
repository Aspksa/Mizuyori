@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title Mizuyori

rem --- Ищем Python ---
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
    where python >nul 2>nul && set "PY=python"
)
if not defined PY (
    echo [Mizuyori] Python не найден. Установи Python 3.10+ с python.org
    echo            и отметь галочку "Add Python to PATH".
    pause
    exit /b 1
)

rem --- Виртуальное окружение ---
if not exist ".venv\Scripts\python.exe" (
    echo [Mizuyori] Создаю виртуальное окружение...
    %PY% -m venv .venv || goto :fail
)
set "VPY=.venv\Scripts\python.exe"

rem --- Зависимости (ставятся только если requirements.txt изменился) ---
if exist "requirements.txt" (
    fc /b "requirements.txt" ".venv\requirements.installed" >nul 2>nul
    if errorlevel 1 (
        echo [Mizuyori] Устанавливаю зависимости...
        "%VPY%" -m pip install --upgrade pip -q
        "%VPY%" -m pip install -r requirements.txt -q || goto :fail
        copy /y "requirements.txt" ".venv\requirements.installed" >nul
    )
)

rem --- Запуск ---
"%VPY%" main.py %*
if errorlevel 1 goto :fail
exit /b 0

:fail
echo.
echo [Mizuyori] Что-то пошло не так. Сообщение об ошибке выше.
pause
exit /b 1

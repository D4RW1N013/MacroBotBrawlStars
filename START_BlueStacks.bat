@echo off
chcp 65001 >nul
title BlueStacks Macro Tool

cd /d "%~dp0"

echo.
echo  BlueStacks Macro Tool - Setup
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo  [FEHLER] Python nicht gefunden!
    echo  https://www.python.org/downloads/
    pause
    exit /b 1
)

echo  [OK] Python gefunden.
echo  Installiere Pakete...
echo.

pip install pynput --quiet

echo.
echo  Starte BlueStacks Macro Tool...
echo  Tipp: Nach dem Start hast du einige Sekunden
echo  um BlueStacks in den Fokus zu klicken!
echo.

python "%~dp0bluestacks_macro.py"

if errorlevel 1 (
    echo.
    echo  [FEHLER] Programm mit Fehler beendet.
    pause
)

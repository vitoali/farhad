@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo Installing deps...
python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo Building DiceBot67.exe ...
python -m PyInstaller --noconfirm --onefile --console --name DiceBot67 ^
  --add-data "config.example.json;." ^
  --add-data "assets;assets" ^
  main.py

echo.
echo Done. File: dist\DiceBot67.exe
echo Copy config.example.json next to the exe as config.json and run --calibrate first.
pause

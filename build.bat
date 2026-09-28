@echo off
rem Construit dist\War-Auto.exe (Python 3.10+ requis)
python -m pip install -r requirements-dev.txt || exit /b 1
python -m PyInstaller --onefile --noconsole --name War-Auto --icon assets/war-auto.ico War-Auto.py || exit /b 1
echo.
echo OK : dist\War-Auto.exe

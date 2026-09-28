@echo off
rem Construit dist\War-Auto.exe (Python 3.10+ requis)
cd /d "%~dp0"
python -m pip install -r requirements-dev.txt || goto erreur
python -m PyInstaller --clean --noconfirm War-Auto.spec || goto erreur
echo.
echo === Verification de dist\War-Auto.exe ===
python assets\verifier_exe.py || goto erreur
rem Vide le cache d'icones de l'explorateur (sinon il garde l'ancienne icone).
ie4uinit.exe -show >nul 2>&1
echo.
echo OK : dist\War-Auto.exe
pause
exit /b 0
:erreur
echo.
echo ECHEC, voir les messages ci-dessus.
pause
exit /b 1

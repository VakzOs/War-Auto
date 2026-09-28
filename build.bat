@echo off
rem Construit dist\War-Auto.exe (Python 3.10+ requis)
cd /d "%~dp0"
python -m pip install -r requirements-dev.txt || goto erreur
python -m PyInstaller --clean --noconfirm War-Auto.spec || goto erreur
echo.
echo OK : dist\War-Auto.exe
echo Si l'ancienne icone s'affiche encore, c'est le cache de Windows :
echo deplace ou renomme l'exe pour la voir.
pause
exit /b 0
:erreur
echo.
echo ECHEC de la construction, voir les messages ci-dessus.
pause
exit /b 1

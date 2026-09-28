# Configuration PyInstaller de War-Auto : python -m PyInstaller --clean War-Auto.spec
# Chemins relatifs à ce fichier (SPECPATH), pour que l'icône soit toujours trouvée.
import os

ICI = SPECPATH
ICONE = os.path.join(ICI, "assets", "war-auto.ico")
if not os.path.isfile(ICONE):
    raise SystemExit(f"Icône introuvable : {ICONE}")

a = Analysis([os.path.join(ICI, "War-Auto.py")], pathex=[ICI])
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="War-Auto",
    console=False,
    upx=False,
    icon=ICONE,
    version=os.path.join(ICI, "assets", "version.txt"),
)

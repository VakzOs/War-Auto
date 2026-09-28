"""Vérifie ce que contient vraiment dist/War-Auto.exe : icône et propriétés.

Usage : python assets/verifier_exe.py [chemin de l'exe]
Lancé automatiquement à la fin de build.bat.
"""

import struct
import sys
from pathlib import Path

import pefile

ICI = Path(__file__).parent
RT_ICON = 3


def images_ico(chemin: Path) -> set[bytes]:
    """Images brutes d'un fichier .ico (celles que Windows range dans l'exe)."""
    donnees = chemin.read_bytes()
    nombre = struct.unpack_from("<H", donnees, 4)[0]
    images = set()
    for i in range(nombre):
        taille, position = struct.unpack_from("<II", donnees, 6 + 16 * i + 8)
        images.add(donnees[position:position + taille])
    return images


def images_exe(pe: pefile.PE) -> list[bytes]:
    images = []
    if not hasattr(pe, "DIRECTORY_ENTRY_RESOURCE"):
        return images
    for type_ in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if type_.struct.Id != RT_ICON:
            continue
        for nom in type_.directory.entries:
            for langue in nom.directory.entries:
                d = langue.data.struct
                images.append(pe.get_data(d.OffsetToData, d.Size))
    return images


def proprietes(pe: pefile.PE) -> dict[str, str]:
    resultat = {}
    for groupe in getattr(pe, "FileInfo", []):
        for info in groupe:
            for table in getattr(info, "StringTable", []):
                resultat.update({k.decode(): v.decode() for k, v in table.entries.items()})
    return resultat


def verifier(exe: Path) -> bool:
    pe = pefile.PE(str(exe))
    attendues = images_ico(ICI / "war-auto.ico")
    presentes = images_exe(pe)
    icone_ok = bool(presentes) and all(i in attendues for i in presentes)
    print(f"Icône   : {'War-Auto (OK)' if icone_ok else 'PAS celle de War-Auto'}"
          f" - {len(presentes)} image(s) dans l'exe")
    editeur = proprietes(pe).get("CompanyName", "absent")
    print(f"Éditeur : {editeur}", "(OK)" if editeur == "VakzOs" else "(propriétés absentes)")
    return icone_ok and editeur == "VakzOs"


if __name__ == "__main__":
    chemin = Path(sys.argv[1]) if len(sys.argv) > 1 else ICI.parent / "dist" / "War-Auto.exe"
    sys.exit(0 if verifier(chemin) else 1)

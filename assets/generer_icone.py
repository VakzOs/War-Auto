"""Génère l'icône de War-Auto (assets/war-auto.ico + PNG embarqué).

Trois arcs aux couleurs des factions autour d'un curseur de souris :
« choisir une faction » + « clic automatique ».
Usage : python assets/generer_icone.py
"""

import base64
import io
from pathlib import Path

from PIL import Image, ImageDraw

ICI = Path(__file__).parent
T = 1024  # dessin en grand, réduit ensuite (anticrénelage)
FOND = (21, 21, 21, 255)
BORD = (48, 48, 48, 255)
FACTIONS = [(79, 175, 231), (241, 85, 63), (34, 215, 96)]  # bleu, rouge, vert
BLANC = (236, 236, 236, 255)


def dessiner() -> Image.Image:
    img = Image.new("RGBA", (T, T), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    marge = 40
    d.rounded_rectangle([marge, marge, T - marge, T - marge], radius=200, fill=FOND,
                        outline=BORD, width=16)

    # Anneau en trois arcs (un par faction), séparés par des espaces.
    centre, rayon, epaisseur, ecart = T / 2, 330, 78, 14
    boite = [centre - rayon, centre - rayon, centre + rayon, centre + rayon]
    # Angles PIL : 0° à droite, sens horaire. Bleu en haut à gauche, rouge en
    # haut à droite, vert en bas (ordre de lecture du jeu).
    for i, couleur in enumerate(FACTIONS):
        debut = 150 + i * 120 + ecart
        d.arc(boite, debut, debut + 120 - 2 * ecart, fill=couleur + (255,), width=epaisseur)

    # Curseur de souris au centre (pointe légèrement au-dessus du centre).
    x, y, k = centre - 95, centre - 175, 1.25
    fleche = [(0, 0), (0, 250), (62, 190), (105, 290), (150, 270), (108, 172), (190, 172)]
    points = [(x + px * k, y + py * k) for px, py in fleche]
    d.polygon(points, fill=BLANC)
    d.line(points + [points[0]], fill=FOND, width=18, joint="curve")
    return img


def main() -> None:
    img = dessiner()
    img.resize((256, 256), Image.LANCZOS).save(
        ICI / "war-auto.ico", sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    )
    img.resize((512, 512), Image.LANCZOS).save(ICI / "war-auto.png")
    # Icône de fenêtre embarquée dans le code (évite un fichier à côté de l'exe).
    tampon = io.BytesIO()
    img.resize((64, 64), Image.LANCZOS).save(tampon, "PNG", optimize=True)
    code = base64.b64encode(tampon.getvalue()).decode()
    (ICI.parent / "war_auto" / "icone.py").write_text(
        '"""Icône de fenêtre (PNG 64 px en base64), générée par assets/generer_icone.py."""\n\n'
        f'ICONE = (\n    "{code}"\n)\n',
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

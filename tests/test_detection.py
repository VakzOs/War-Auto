from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from war_auto.detection import trouver_factions

CAPTURE = Path(__file__).parent / "fixtures" / "choix_faction.png"
# Centres attendus des logos sur la capture d'origine (617x355).
ATTENDU = {"bleu": (153, 181), "rouge": (303, 181), "vert": (453, 181)}


def _capture(echelle=1.0):
    im = Image.open(CAPTURE).convert("RGB")
    if echelle != 1.0:
        im = im.resize((round(im.width * echelle), round(im.height * echelle)))
    return np.array(im)


def _verifier(res, echelle, decalage=(0, 0), tolerance=15):
    assert res is not None
    for cle, (x, y) in ATTENDU.items():
        ex, ey = x * echelle + decalage[0], y * echelle + decalage[1]
        assert abs(res[cle][0] - ex) <= tolerance * echelle, cle
        assert abs(res[cle][1] - ey) <= tolerance * echelle, cle


@pytest.mark.parametrize("echelle", [1.0, 2.0, 3.5])
def test_capture_a_differentes_tailles(echelle):
    _verifier(trouver_factions(_capture(echelle)), echelle)


@pytest.mark.parametrize("taille", [(1920, 1080), (2560, 1440), (3840, 2160)])
def test_fenetre_dans_un_grand_ecran(taille):
    w, h = taille
    echelle = h / 1080 * 1.5
    fenetre = _capture(echelle)
    ecran = np.full((h, w, 3), 20, dtype=np.uint8)
    ox, oy = (w - fenetre.shape[1]) // 2, (h - fenetre.shape[0]) // 2
    ecran[oy:oy + fenetre.shape[0], ox:ox + fenetre.shape[1]] = fenetre
    _verifier(trouver_factions(ecran), echelle, (ox, oy))


def test_ecran_sans_factions():
    assert trouver_factions(np.full((1080, 1920, 3), 20, dtype=np.uint8)) is None


def test_un_seul_logo_ne_suffit_pas():
    img = _capture()
    img[:, 230:] = 20  # on masque le rouge et le vert
    assert trouver_factions(img) is None


def test_capture_windows_bgra():
    img = _capture(2.0)
    bgra = np.dstack([img[..., ::-1], np.full(img.shape[:2], 255, np.uint8)])
    _verifier(trouver_factions(bgra, bgr=True), 2.0)

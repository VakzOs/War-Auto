"""Détection des logos de faction par couleur, indépendante de la résolution.

On cherche à l'écran les trois logos (bleu, rouge, vert). L'écran de choix
n'est considéré comme visible que si les trois sont présents, de taille
comparable et alignés horizontalement : cela évite de cliquer sur n'importe
quel élément bleu ou rouge du jeu.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Plages HSV relevées sur la capture du jeu (teinte en degrés, s et v sur 0-1).
# Bleu ~ 202°, rouge ~ 5°, vert ~ 140°.
FACTIONS = {
    "bleu": {"teinte": (190, 220), "nom": "Bleu"},
    "rouge": {"teinte": (355, 15), "nom": "Rouge"},
    "vert": {"teinte": (125, 160), "nom": "Vert"},
}
SAT_MIN = 0.5
VAL_MIN = 0.6

LARGEUR_ANALYSE = 640  # l'image est réduite à ~640 px de large avant analyse
TAILLE_CELLULE = 3  # pixels réduits par cellule de la grille
REMPLISSAGE_CELLULE = 0.25  # part de pixels colorés pour qu'une cellule compte
RAYON_FUSION = 1  # cellules : voisinage des composantes connexes
ECART_FUSION = 0.25  # fusionne deux taches séparées de moins de 25 % de leur taille
HAUTEUR_MIN = 0.03  # un logo fait au moins 3 % de la hauteur de l'écran
HAUTEUR_MAX = 0.40


@dataclass
class Tache:
    x0: int
    y0: int
    x1: int
    y1: int
    cellules: int

    @property
    def centre(self) -> tuple[float, float]:
        return (self.x0 + self.x1) / 2, (self.y0 + self.y1) / 2

    @property
    def largeur(self) -> int:
        return self.x1 - self.x0

    @property
    def hauteur(self) -> int:
        return self.y1 - self.y0


def _hsv(rgb: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    rgb = rgb.astype(np.float32) / 255.0
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    maxi = rgb.max(axis=-1)
    mini = rgb.min(axis=-1)
    delta = maxi - mini
    sat = np.where(maxi > 0, delta / np.maximum(maxi, 1e-6), 0)
    d = np.maximum(delta, 1e-6)
    teinte = np.where(
        maxi == r,
        ((g - b) / d) % 6,
        np.where(maxi == g, (b - r) / d + 2, (r - g) / d + 4),
    ) * 60
    return teinte, sat, maxi


def _masque(teinte, sat, val, plage) -> np.ndarray:
    lo, hi = plage
    if lo <= hi:
        dans = (teinte >= lo) & (teinte <= hi)
    else:  # plage qui passe par 0° (rouge)
        dans = (teinte >= lo) | (teinte <= hi)
    return dans & (sat >= SAT_MIN) & (val >= VAL_MIN)


def _taches(masque: np.ndarray) -> list[Tache]:
    """Composantes connexes sur une grille grossière, en reliant les cellules
    distantes d'au plus RAYON_FUSION (les logos sont faits de plusieurs morceaux)."""
    c = TAILLE_CELLULE
    h, w = masque.shape
    gh, gw = h // c, w // c
    grille = masque[: gh * c, : gw * c].reshape(gh, c, gw, c).mean(axis=(1, 3))
    actives = grille >= REMPLISSAGE_CELLULE
    vu = np.zeros_like(actives)
    taches = []
    for y, x in zip(*np.nonzero(actives)):
        if vu[y, x]:
            continue
        pile = [(y, x)]
        vu[y, x] = True
        ys, xs = [], []
        while pile:
            cy, cx = pile.pop()
            ys.append(cy)
            xs.append(cx)
            for dy in range(-RAYON_FUSION, RAYON_FUSION + 1):
                for dx in range(-RAYON_FUSION, RAYON_FUSION + 1):
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < gh and 0 <= nx < gw and actives[ny, nx] and not vu[ny, nx]:
                        vu[ny, nx] = True
                        pile.append((ny, nx))
        taches.append(Tache(
            int(min(xs)) * c, int(min(ys)) * c,
            (int(max(xs)) + 1) * c, (int(max(ys)) + 1) * c, len(ys),
        ))
    return taches


def _fusionner(taches: list[Tache]) -> list[Tache]:
    """Regroupe les morceaux proches d'un même logo (le bleu en a quatre,
    le rouge plusieurs chevrons). L'écart toléré est relatif à la taille des
    morceaux, donc indépendant de la résolution."""
    # Le bruit (petits éléments colorés du jeu) est ignoré, et on borne le
    # nombre de morceaux pour garder une analyse rapide.
    taches = sorted((t for t in taches if t.cellules >= 2), key=lambda t: -t.cellules)[:60]
    fusion = True
    while fusion:
        fusion = False
        for i in range(len(taches)):
            for j in range(i + 1, len(taches)):
                a, b = taches[i], taches[j]
                ecart_x = max(a.x0, b.x0) - min(a.x1, b.x1)
                ecart_y = max(a.y0, b.y0) - min(a.y1, b.y1)
                taille = max(a.largeur, a.hauteur, b.largeur, b.hauteur)
                if max(ecart_x, ecart_y) <= ECART_FUSION * taille:
                    taches[i] = Tache(
                        min(a.x0, b.x0), min(a.y0, b.y0),
                        max(a.x1, b.x1), max(a.y1, b.y1),
                        a.cellules + b.cellules,
                    )
                    del taches[j]
                    fusion = True
                    break
            if fusion:
                break
    return taches


def trouver_factions(rgb: np.ndarray) -> dict[str, tuple[int, int]] | None:
    """Renvoie le centre (en pixels de l'image d'origine) de chaque logo,
    ou None si l'écran de choix de faction n'est pas visible."""
    h0, w0 = rgb.shape[:2]
    pas = max(1, round(w0 / LARGEUR_ANALYSE))
    petit = rgb[::pas, ::pas, :3]
    h = petit.shape[0]
    teinte, sat, val = _hsv(petit)

    logos: dict[str, Tache] = {}
    for cle, f in FACTIONS.items():
        candidates = [
            t for t in _fusionner(_taches(_masque(teinte, sat, val, f["teinte"])))
            if HAUTEUR_MIN * h <= t.hauteur <= HAUTEUR_MAX * h
            and 0.5 <= t.largeur / max(t.hauteur, 1) <= 2
        ]
        if not candidates:
            return None
        logos[cle] = max(candidates, key=lambda t: t.cellules)

    # Les trois logos doivent se ressembler : même hauteur à ±40 %, même ligne.
    hauteurs = [t.hauteur for t in logos.values()]
    if max(hauteurs) > 1.4 * min(hauteurs):
        return None
    centres_y = [t.centre[1] for t in logos.values()]
    if max(centres_y) - min(centres_y) > 0.5 * max(hauteurs):
        return None

    return {
        cle: (int(t.centre[0] * pas), int(t.centre[1] * pas))
        for cle, t in logos.items()
    }

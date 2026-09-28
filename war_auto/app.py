"""War-Auto : clique automatiquement sur la faction choisie.

1. Lancer le logiciel.
2. L'activer (bouton ou F8) : il ne fait rien tant qu'aucune équipe n'est choisie.
3. Choisir l'équipe : dès que l'écran « Choisir une faction » est visible,
   il clique sur le logo de cette équipe.
"""

from __future__ import annotations

import ctypes
import sys
import threading
import time
import tkinter as tk

import mss
import numpy as np

from war_auto.detection import FACTIONS, trouver_factions

INTERVALLE_RECHERCHE = 0.15  # s entre deux analyses de l'écran
INTERVALLE_CLIC = 0.4  # s entre deux clics tant que l'écran reste visible
TOUCHE_BASCULE = 0x77  # F8

COULEURS = {"bleu": "#4fafe7", "rouge": "#e8503a", "vert": "#1fd85e"}
FOND = "#141414"
CARTE = "#1f1f1f"
TEXTE = "#e6e6e6"
GRIS = "#8a8a8a"

user32 = ctypes.windll.user32 if sys.platform == "win32" else None


def rendre_dpi_aware() -> None:
    """Sans ça, Windows met les coordonnées à l'échelle (125 %, 150 %…) et le
    clic tombe à côté."""
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        user32.SetProcessDPIAware()


def cliquer(x: int, y: int) -> None:
    MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP = 0x0002, 0x0004
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.03)  # laisse le jeu voir le survol avant le clic
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.03)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


class Automate(threading.Thread):
    """Boucle d'arrière-plan : capture chaque écran, cherche les logos, clique."""

    def __init__(self, signaler):
        super().__init__(daemon=True)
        self.actif = False
        self.faction: str | None = None
        self._signaler = signaler
        self._dernier_message = ""

    def signaler(self, message: str) -> None:
        if message != self._dernier_message:
            self._dernier_message = message
            self._signaler(message)

    def run(self) -> None:
        with mss.mss() as capture:
            while True:
                if not (self.actif and self.faction):
                    time.sleep(INTERVALLE_RECHERCHE)
                    continue
                cible = self.trouver(capture)
                if cible:
                    cliquer(*cible)
                    self.signaler(f"Clic sur {FACTIONS[self.faction]['nom']} ({cible[0]}, {cible[1]})")
                    time.sleep(INTERVALLE_CLIC)
                else:
                    self.signaler("En attente de l'écran de faction…")
                    time.sleep(INTERVALLE_RECHERCHE)

    def trouver(self, capture) -> tuple[int, int] | None:
        for ecran in capture.monitors[1:]:
            image = np.asarray(capture.grab(ecran))[..., [2, 1, 0]]  # BGRA -> RGB
            logos = trouver_factions(image)
            if logos and self.faction in logos:
                x, y = logos[self.faction]
                return ecran["left"] + x, ecran["top"] + y
        return None


class Fenetre:
    def __init__(self) -> None:
        self.racine = tk.Tk()
        self.racine.title("War-Auto")
        self.racine.configure(bg=FOND, padx=16, pady=16)
        self.racine.resizable(False, False)
        self.racine.attributes("-topmost", True)

        self.statut = tk.StringVar(value="Inactif")
        self.automate = Automate(lambda msg: self.racine.after(0, self.statut.set, msg))

        tk.Label(self.racine, text="// CHOISIR UNE FACTION", bg=FOND, fg=TEXTE,
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")

        self.bouton_actif = tk.Button(self.racine, command=self.basculer, relief="flat",
                                      font=("Segoe UI", 10, "bold"), cursor="hand2", bd=0,
                                      padx=10, pady=8)
        self.bouton_actif.pack(fill="x", pady=(12, 12))

        ligne = tk.Frame(self.racine, bg=FOND)
        ligne.pack()
        self.boutons_faction = {}
        for i, (cle, f) in enumerate(FACTIONS.items()):
            b = tk.Button(ligne, text=f["nom"], width=8, relief="flat", bd=0, cursor="hand2",
                          font=("Segoe UI", 10, "bold"), pady=14,
                          command=lambda c=cle: self.choisir(c))
            b.grid(row=0, column=i, padx=4)
            self.boutons_faction[cle] = b

        tk.Label(self.racine, textvariable=self.statut, bg=FOND, fg=GRIS,
                 font=("Segoe UI", 9), wraplength=260, justify="left").pack(anchor="w", pady=(12, 0))
        tk.Label(self.racine, text="F8 : activer / désactiver", bg=FOND, fg=GRIS,
                 font=("Segoe UI", 8)).pack(anchor="w")

        self.f8_enfonce = False
        self.rafraichir()
        self.automate.start()
        self.surveiller_f8()

    def basculer(self) -> None:
        self.automate.actif = not self.automate.actif
        self.automate._dernier_message = ""
        if not self.automate.actif:
            self.statut.set("Inactif")
        elif not self.automate.faction:
            self.statut.set("Actif — choisis ton équipe")
        self.rafraichir()

    def choisir(self, cle: str) -> None:
        # Recliquer sur l'équipe déjà choisie la désélectionne.
        self.automate.faction = None if self.automate.faction == cle else cle
        if self.automate.actif and not self.automate.faction:
            self.statut.set("Actif — choisis ton équipe")
        self.rafraichir()

    def rafraichir(self) -> None:
        actif = self.automate.actif
        self.bouton_actif.configure(
            text="ACTIF" if actif else "ACTIVER",
            bg="#2e7d32" if actif else "#333333", fg="white",
            activebackground="#388e3c" if actif else "#444444", activeforeground="white",
        )
        for cle, b in self.boutons_faction.items():
            choisi = cle == self.automate.faction
            b.configure(
                bg=COULEURS[cle] if choisi else CARTE,
                fg="#000000" if choisi else COULEURS[cle],
                activebackground=COULEURS[cle], activeforeground="#000000",
            )

    def surveiller_f8(self) -> None:
        # Touche globale : marche même quand le jeu a le focus.
        enfonce = bool(user32.GetAsyncKeyState(TOUCHE_BASCULE) & 0x8000)
        if enfonce and not self.f8_enfonce:
            self.basculer()
        self.f8_enfonce = enfonce
        self.racine.after(50, self.surveiller_f8)

    def lancer(self) -> None:
        self.racine.mainloop()


def main() -> None:
    if sys.platform != "win32":
        sys.exit("War-Auto fonctionne uniquement sous Windows.")
    rendre_dpi_aware()
    Fenetre().lancer()


if __name__ == "__main__":
    main()

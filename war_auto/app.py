"""War-Auto : clique automatiquement sur la faction choisie.

1. Lancer le logiciel.
2. L'activer (bouton ou F8) : il ne fait rien tant qu'aucune équipe n'est choisie.
3. Choisir l'équipe (bouton ou raccourci, F5/F6/F7 par défaut) : dès que
   l'écran « Choisir une faction » est visible, il clique sur son logo.
"""

from __future__ import annotations

import ctypes
import io
import json
import os
import sys
import threading
import time
import tkinter as tk
import wave
import webbrowser
from pathlib import Path

import mss
import numpy as np

from war_auto.detection import FACTIONS, trouver_factions
from war_auto.icone import ICONE
from war_auto.logos import LOGOS

INTERVALLE_RECHERCHE = 0.02  # s entre deux analyses quand l'écran n'est pas là
ARRET_AUTO = 10  # s sans écran de faction après un clic -> désactivation

COULEURS = {"bleu": "#4fafe7", "rouge": "#f1553f", "vert": "#22d760"}
FOND = "#141414"
CARTE = "#1f1f1f"
CARTE_CHOISIE = "#2a2a2a"
TEXTE = "#e6e6e6"
GRIS = "#8a8a8a"
POLICE = "Segoe UI"

VK_F5, VK_F6, VK_F7, VK_F8 = 0x74, 0x75, 0x76, 0x77
CONFIG_DEFAUT = {
    "touches": {"activer": VK_F8, "bleu": VK_F5, "rouge": VK_F6, "vert": VK_F7},
    "delai_clic_ms": 50,
    "volume": 25,  # % (0 = muet)
}
FICHIER_CONFIG = Path(os.environ.get("APPDATA", Path.home())) / "War-Auto" / "config.json"

user32 = ctypes.windll.user32 if sys.platform == "win32" else None


def charger_config() -> dict:
    config = json.loads(json.dumps(CONFIG_DEFAUT))
    try:
        lu = json.loads(FICHIER_CONFIG.read_text(encoding="utf-8"))
        config["touches"].update(lu.get("touches", {}))
        config["delai_clic_ms"] = int(lu.get("delai_clic_ms", config["delai_clic_ms"]))
        config["volume"] = int(lu.get("volume", config["volume"]))
    except (OSError, ValueError):
        pass
    return config


def sauver_config(config: dict) -> None:
    try:
        FICHIER_CONFIG.parent.mkdir(parents=True, exist_ok=True)
        FICHIER_CONFIG.write_text(json.dumps(config, indent=2), encoding="utf-8")
    except OSError:
        pass


def nom_touche(vk: int) -> str:
    if 0x70 <= vk <= 0x87:
        return f"F{vk - 0x6F}"
    if 0x60 <= vk <= 0x69:
        return f"Num {vk - 0x60}"
    if 0x30 <= vk <= 0x39 or 0x41 <= vk <= 0x5A:
        return chr(vk)
    code = user32.MapVirtualKeyW(vk, 0) << 16
    tampon = ctypes.create_unicode_buffer(32)
    if user32.GetKeyNameTextW(code, tampon, 32):
        return tampon.value
    return f"Touche {vk}"


def touche_enfoncee(vk: int) -> bool:
    return bool(user32.GetAsyncKeyState(vk) & 0x8000)


def son_bip(frequence: int, volume: int) -> bytes:
    """WAV d'un bip doux (sinus avec fondu), au volume voulu (0-100)."""
    taux, duree = 44100, 0.09
    t = np.arange(int(taux * duree)) / taux
    fondu = np.minimum(1, np.minimum(t, duree - t) / 0.015)
    amplitude = (volume / 100) ** 2 * 0.6 * 32767  # courbe douce : 25 % reste discret
    donnees = (np.sin(2 * np.pi * frequence * t) * fondu * amplitude).astype("<i2")
    tampon = io.BytesIO()
    with wave.open(tampon, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(taux)
        w.writeframes(donnees.tobytes())
    return tampon.getvalue()


def bip(frequence: int, volume: int) -> None:
    """Petit son pour savoir, en jeu, ce qu'un raccourci a fait."""
    if volume <= 0:
        return
    import winsound
    son = son_bip(frequence, volume)
    threading.Thread(target=winsound.PlaySound, args=(son, winsound.SND_MEMORY),
                     daemon=True).start()


def rendre_dpi_aware() -> None:
    """Sans ça, Windows met les coordonnées à l'échelle (125 %, 150 %…) et le
    clic tombe à côté."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        user32.SetProcessDPIAware()


def facteur_echelle(racine: tk.Tk) -> float:
    """Taille de l'interface : suit la mise à l'échelle Windows (150 %, 200 %…)
    et grossit aussi sur les grands écrans (4K à 100 %)."""
    try:
        dpi = user32.GetDpiForSystem()
    except Exception:
        dpi = 96
    return max(1.0, dpi / 96, racine.winfo_screenheight() / 1080)


def cliquer(x: int, y: int) -> None:
    MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP = 0x0002, 0x0004
    user32.SetCursorPos(int(x), int(y))
    time.sleep(0.005)  # laisse le jeu voir le survol avant le clic
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.01)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


class Automate(threading.Thread):
    """Boucle d'arrière-plan : capture chaque écran, cherche les logos, clique."""

    def __init__(self, signaler, arret_auto, delai_clic_ms: int):
        super().__init__(daemon=True)
        self.actif = False
        self.faction: str | None = None
        self.delai_clic_ms = delai_clic_ms
        self._signaler = signaler
        self._arret_auto = arret_auto
        self._dernier_clic: float | None = None
        self._dernier_message = ""
        self._ecran_prefere = 0  # on commence par l'écran où les logos étaient

    def signaler(self, message: str) -> None:
        if message != self._dernier_message:
            self._dernier_message = message
            self._signaler(message)

    def run(self) -> None:
        with mss.mss() as capture:
            while True:
                if not (self.actif and self.faction):
                    self._dernier_clic = None
                    time.sleep(INTERVALLE_RECHERCHE)
                    continue
                cible = self.trouver(capture)
                if cible:
                    cliquer(*cible)
                    self._dernier_clic = time.monotonic()
                    self.signaler(f"Clic sur {FACTIONS[self.faction]['nom']} ({cible[0]}, {cible[1]})")
                    time.sleep(self.delai_clic_ms / 1000)
                elif self._dernier_clic and time.monotonic() - self._dernier_clic >= ARRET_AUTO:
                    # L'écran a disparu depuis 10 s après nos clics : la faction
                    # est prise, on s'arrête.
                    self.actif = False
                    self._dernier_clic = None
                    self._arret_auto()
                else:
                    self.signaler("En attente de l'écran de faction…")
                    time.sleep(INTERVALLE_RECHERCHE)

    def trouver(self, capture) -> tuple[int, int] | None:
        ecrans = capture.monitors[1:]
        ordre = sorted(range(len(ecrans)), key=lambda i: i != self._ecran_prefere)
        for i in ordre:
            ecran = ecrans[i]
            logos = trouver_factions(np.asarray(capture.grab(ecran)), bgr=True)
            if logos and self.faction in logos:
                self._ecran_prefere = i
                x, y = logos[self.faction]
                return ecran["left"] + x, ecran["top"] + y
        return None


class Fenetre:
    def __init__(self) -> None:
        self.config = charger_config()
        self.racine = tk.Tk()
        self.echelle = facteur_echelle(self.racine)
        # Polices en points : Tk les convertit avec ce facteur.
        self.racine.tk.call("tk", "scaling", self.echelle * 96 / 72)
        s = self.s
        self.racine.title("War-Auto")
        self.racine.configure(bg=FOND, padx=s(16), pady=s(16))
        self.racine.resizable(False, False)
        self.racine.attributes("-topmost", True)
        self.icone = tk.PhotoImage(data=ICONE)
        self.racine.iconphoto(True, self.icone)

        self.statut = tk.StringVar(value="Inactif")
        self.automate = Automate(lambda msg: self.racine.after(0, self.statut.set, msg),
                                 lambda: self.racine.after(0, self.arret_auto),
                                 self.config["delai_clic_ms"])
        self.en_attente_touche: str | None = None  # action dont on change la touche
        self.touches_enfoncees: set[int] = set()

        tk.Label(self.racine, text="// CHOISIR UNE FACTION", bg=FOND, fg=TEXTE,
                 font=(POLICE, 11, "bold")).pack(anchor="w")

        # Activer / désactiver
        ligne_actif = tk.Frame(self.racine, bg=FOND)
        ligne_actif.pack(fill="x", pady=(s(12), s(12)))
        self.bouton_actif = tk.Button(ligne_actif, command=self.basculer, relief="flat",
                                      font=(POLICE, 10, "bold"), cursor="hand2", bd=0, pady=s(8))
        self.bouton_actif.pack(side="left", fill="x", expand=True)
        self.boutons_touche = {"activer": self.bouton_touche(ligne_actif, "activer")}
        self.boutons_touche["activer"].pack(side="left", padx=(s(6), 0), fill="y")

        # Cartes des factions
        ligne = tk.Frame(self.racine, bg=FOND)
        ligne.pack()
        # Logos en 128 px : réduits de moitié sous 150 %.
        self.images = {cle: tk.PhotoImage(data=LOGOS[cle]) for cle in FACTIONS}
        if self.echelle < 1.5:
            self.images = {cle: img.subsample(2) for cle, img in self.images.items()}
        self.cartes = {}
        for i, (cle, f) in enumerate(FACTIONS.items()):
            carte = tk.Frame(ligne, bg=CARTE, highlightthickness=s(2), highlightbackground=CARTE,
                             cursor="hand2", padx=s(10), pady=s(10))
            carte.grid(row=0, column=i, padx=s(4))
            logo = tk.Label(carte, image=self.images[cle], bg=CARTE)
            logo.pack()
            nom = tk.Label(carte, text=f["nom"].upper(), bg=CARTE, fg=COULEURS[cle],
                           font=(POLICE, 9, "bold"))
            nom.pack(pady=(s(6), s(6)))
            for w in (carte, logo, nom):
                w.bind("<Button-1>", lambda _e, c=cle: self.choisir(c))
            self.boutons_touche[cle] = self.bouton_touche(carte, cle)
            self.boutons_touche[cle].pack(fill="x")
            self.cartes[cle] = (carte, logo, nom)

        # Vitesse
        ligne_vitesse = tk.Frame(self.racine, bg=FOND)
        ligne_vitesse.pack(fill="x", pady=(s(12), 0))
        tk.Label(ligne_vitesse, text="Délai entre clics (ms)", bg=FOND, fg=TEXTE,
                 font=(POLICE, 9)).pack(side="left")
        self.delai = tk.IntVar(value=self.config["delai_clic_ms"])
        tk.Spinbox(ligne_vitesse, from_=0, to=1000, increment=10, width=5,
                   textvariable=self.delai, command=self.changer_delai, relief="flat",
                   bg=CARTE, fg=TEXTE, buttonbackground=CARTE, insertbackground=TEXTE,
                   font=(POLICE, 9)).pack(side="right")
        self.delai.trace_add("write", lambda *_: self.changer_delai())

        # Volume des bips
        ligne_volume = tk.Frame(self.racine, bg=FOND)
        ligne_volume.pack(fill="x", pady=(s(8), 0))
        tk.Label(ligne_volume, text="Volume des bips (%)", bg=FOND, fg=TEXTE,
                 font=(POLICE, 9)).pack(side="left")
        self.volume = tk.IntVar(value=self.config["volume"])
        tk.Spinbox(ligne_volume, from_=0, to=100, increment=5, width=5,
                   textvariable=self.volume, command=lambda: self.bip(880), relief="flat",
                   bg=CARTE, fg=TEXTE, buttonbackground=CARTE, insertbackground=TEXTE,
                   font=(POLICE, 9)).pack(side="right")
        self.volume.trace_add("write", lambda *_: self.changer_volume())

        tk.Label(self.racine, textvariable=self.statut, bg=FOND, fg=GRIS,
                 font=(POLICE, 9), wraplength=s(300), justify="left").pack(anchor="w", pady=(s(12), 0))
        pied = tk.Frame(self.racine, bg=FOND)
        pied.pack(fill="x")
        tk.Label(pied, text="Clique sur une touche pour la changer.", bg=FOND, fg=GRIS,
                 font=(POLICE, 8)).pack(side="left")
        credit = tk.Label(pied, text="@VakzOs", bg=FOND, fg=TEXTE, cursor="hand2",
                          font=(POLICE, 8, "bold"))
        credit.pack(side="right")
        credit.bind("<Button-1>", lambda _e: webbrowser.open("https://github.com/VakzOs"))

        self.rafraichir()
        self.automate.start()
        self.surveiller_clavier()

    def s(self, pixels: int) -> int:
        return round(pixels * self.echelle)

    def bouton_touche(self, parent, action: str) -> tk.Button:
        return tk.Button(parent, relief="flat", bd=0, cursor="hand2", font=(POLICE, 8),
                         bg="#333333", fg=TEXTE, activebackground="#444444",
                         activeforeground=TEXTE, padx=self.s(8),
                         command=lambda: self.attendre_touche(action))

    # --- Actions -----------------------------------------------------------

    def basculer(self) -> None:
        self.automate.actif = not self.automate.actif
        self.automate._dernier_message = ""
        if not self.automate.actif:
            self.statut.set("Inactif")
        elif not self.automate.faction:
            self.statut.set("Actif — choisis ton équipe")
        self.rafraichir()

    def arret_auto(self) -> None:
        self.automate._dernier_message = ""
        self.statut.set(f"Désactivé : plus d'écran de faction depuis {ARRET_AUTO} s")
        self.rafraichir()
        self.bip(520)

    def choisir(self, cle: str) -> None:
        # Recliquer sur l'équipe déjà choisie la désélectionne.
        self.automate.faction = None if self.automate.faction == cle else cle
        if self.automate.actif and not self.automate.faction:
            self.statut.set("Actif — choisis ton équipe")
        self.rafraichir()

    def raccourci_faction(self, cle: str) -> None:
        """En jeu, le raccourci d'une équipe la choisit et active l'autoclick."""
        self.automate.faction = cle
        if not self.automate.actif:
            self.basculer()
        self.rafraichir()
        self.bip(880)

    def changer_delai(self) -> None:
        try:
            delai = max(0, min(1000, int(self.delai.get())))
        except (tk.TclError, ValueError):
            return
        self.automate.delai_clic_ms = delai
        self.config["delai_clic_ms"] = delai
        sauver_config(self.config)

    def changer_volume(self) -> None:
        try:
            self.config["volume"] = max(0, min(100, int(self.volume.get())))
        except (tk.TclError, ValueError):
            return
        sauver_config(self.config)

    def bip(self, frequence: int) -> None:
        bip(frequence, self.config["volume"])

    def attendre_touche(self, action: str) -> None:
        self.en_attente_touche = action
        self.rafraichir()

    # --- Affichage ---------------------------------------------------------

    def rafraichir(self) -> None:
        actif = self.automate.actif
        self.bouton_actif.configure(
            text="ACTIF" if actif else "ACTIVER",
            bg="#2e7d32" if actif else "#333333", fg="white",
            activebackground="#388e3c" if actif else "#444444", activeforeground="white",
        )
        for cle, (carte, logo, nom) in self.cartes.items():
            choisi = cle == self.automate.faction
            fond = CARTE_CHOISIE if choisi else CARTE
            carte.configure(bg=fond, highlightbackground=COULEURS[cle] if choisi else CARTE)
            logo.configure(bg=fond)
            nom.configure(bg=fond)
        for action, bouton in self.boutons_touche.items():
            if action == self.en_attente_touche:
                bouton.configure(text="Appuie…", bg="#8a6d1f")
            else:
                bouton.configure(text=nom_touche(self.config["touches"][action]), bg="#333333")

    # --- Clavier global (marche même quand le jeu a le focus) --------------

    def surveiller_clavier(self) -> None:
        if self.en_attente_touche:
            self.capturer_touche()
        else:
            for action, vk in self.config["touches"].items():
                enfonce = touche_enfoncee(vk)
                if enfonce and vk not in self.touches_enfoncees:
                    if action == "activer":
                        self.basculer()
                        self.bip(1040 if self.automate.actif else 520)
                    else:
                        self.raccourci_faction(action)
                if enfonce:
                    self.touches_enfoncees.add(vk)
                else:
                    self.touches_enfoncees.discard(vk)
        self.racine.after(20, self.surveiller_clavier)

    def capturer_touche(self) -> None:
        souris = {0x01, 0x02, 0x04, 0x05, 0x06}
        for vk in range(0x08, 0xFF):
            if vk in souris or vk in (0x10, 0x11, 0x12):  # Maj/Ctrl/Alt génériques
                continue
            if touche_enfoncee(vk):
                if vk == 0x1B:  # Échap : annuler
                    self.en_attente_touche = None
                else:
                    # Une touche ne sert qu'à une action : on l'échange si besoin.
                    touches = self.config["touches"]
                    for autre, v in touches.items():
                        if v == vk:
                            touches[autre] = touches[self.en_attente_touche]
                    touches[self.en_attente_touche] = vk
                    sauver_config(self.config)
                    self.en_attente_touche = None
                self.touches_enfoncees.add(vk)  # évite de déclencher l'action tout de suite
                self.rafraichir()
                return

    def lancer(self) -> None:
        self.racine.mainloop()


def main() -> None:
    if sys.platform != "win32":
        sys.exit("War-Auto fonctionne uniquement sous Windows.")
    rendre_dpi_aware()
    try:  # icône de l'app (et non celle de Python) dans la barre des tâches
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("VakzOs.WarAuto")
    except Exception:
        pass
    Fenetre().lancer()


if __name__ == "__main__":
    main()

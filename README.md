# War-Auto

Petit autoclicker Windows qui choisit automatiquement ta faction sur l'écran
« Choisir une faction » (Bleu, Rouge, Vert).

## Utilisation

1. Lance `War-Auto.exe`.
2. Clique sur **ACTIVER** (ou appuie sur **F8**, même en jeu) : il ne fait rien
   tant qu'aucune équipe n'est choisie.
3. Choisis ton équipe (**Bleu**, **Rouge** ou **Vert**). Dès que l'écran de
   faction apparaît, il clique sur le logo de cette équipe (toutes les 0,4 s
   tant que l'écran reste affiché).

F8 désactive à tout moment. Recliquer sur l'équipe choisie la désélectionne.

## Comment il trouve les logos

Il capture chaque écran et cherche les couleurs des trois logos (bleu ~202°,
rouge ~5°, vert ~140° de teinte). Il ne clique que si **les trois** logos sont
visibles, de taille proche et alignés : un autre élément bleu du jeu ne le fait
pas cliquer. Tout est relatif à la taille de l'image, donc ça marche quelle que
soit la résolution (1080p, 1440p, 4K, fenêtré) et sur plusieurs écrans.

## Récupérer l'exe

Chaque push construit `War-Auto.exe` sur GitHub Actions : onglet **Actions** →
dernier run **Build** → artefact **War-Auto**.

Ou en local (Python 3.10+) : `build.bat` → `dist\War-Auto.exe`.

Pour lancer sans compiler : `pip install -r requirements.txt` puis
`python War-Auto.py`.

## Tests

`pip install -r requirements-dev.txt` puis `python -m pytest` : vérifie la
détection sur la capture du jeu à plusieurs échelles et dans des écrans 1080p,
1440p et 4K.

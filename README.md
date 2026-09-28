# War-Auto

Petit autoclicker Windows qui choisit automatiquement ta faction sur l'écran
« Choisir une faction » (Bleu, Rouge, Vert).

## Utilisation

1. Lance `War-Auto.exe`.
2. Clique sur **ACTIVER** (ou **F8**, même en jeu) : il ne fait rien tant
   qu'aucune équipe n'est choisie.
3. Choisis ton équipe : clic sur son logo, ou raccourci en jeu
   (**F5** Bleu, **F6** Rouge, **F7** Vert). Le raccourci d'une équipe
   l'active aussi. Dès que l'écran de faction apparaît, il clique sur le logo.

- Un bip confirme chaque raccourci (aigu : activé, grave : désactivé).
  **Volume des bips** réglable (25 % par défaut, 0 = muet).
- Une équipe pleine a son logo **grisé** : il continue de cliquer dessus,
  pour prendre une place dès qu'elle se libère.
- Clique sur une touche affichée (F5, F8…) puis appuie sur la nouvelle touche
  pour la changer (Échap annule).
- **Délai entre clics** : 50 ms par défaut, réglable de 0 à 1000 ms.
- Réglages enregistrés dans `%APPDATA%\War-Auto\config.json`.
- L'interface s'agrandit seule selon la mise à l'échelle Windows et en 4K.

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

## Icône

`assets/war-auto.ico` (exe) et `war_auto/icone.py` (fenêtre) sont générés par
`python assets/generer_icone.py`.

## Tests

`pip install -r requirements-dev.txt` puis `python -m pytest` : vérifie la
détection sur la capture du jeu à plusieurs échelles et dans des écrans 1080p,
1440p et 4K.

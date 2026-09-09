# Speak Helper — documentation française

[English README](../../README.md) · [Licence](../../LICENSE) ·
[État du développement](../missions/STATUS.md)

Speak Helper est un utilitaire de bureau qui lit à voix haute le texte sélectionné.
Il est conçu en priorité pour Windows 11 et fonctionne avec PyCharm, les navigateurs,
les éditeurs, Word, les lecteurs PDF et les terminaux lorsque leur commande Copier
est disponible.

Ce dépôt est un fork maintenu de
[archoor/speak-helper](https://github.com/archoor/speak-helper). L'historique Git et
la licence MIT du projet d'origine sont conservés.

## Démarrage rapide sous Windows

1. Lancez `SpeakHelper.exe` depuis le dossier autonome.
2. Ouvrez l'icône Speak Helper dans la zone de notification.
3. Dans **Paramètres → Voix**, choisissez une voix Edge française ou anglaise.
4. Sélectionnez du texte dans une autre application.
5. Appuyez sur `Ctrl+Alt+R`.

Si une autre application utilise déjà ce raccourci, Speak Helper affiche le conflit.
Choisissez alors une autre combinaison dans **Paramètres → Raccourcis**.

## Raccourcis par défaut

| Action | Raccourci |
| --- | --- |
| Lire le texte sélectionné | `Ctrl+Alt+R` |
| Arrêter | `Ctrl+Alt+Maj+X` |
| Pause / Reprendre | `Ctrl+Alt+Maj+P` |
| Relire le dernier texte | `Ctrl+Alt+Maj+R` |

Tous les raccourcis sont configurables.

## Langue de l'interface

Choisissez **English** ou **Français** dans **Paramètres → Général**. Le changement
est immédiat et persistant. Lors du premier lancement, une locale Windows française
sélectionne le français ; les autres locales utilisent l'anglais.

Sous Windows, **Paramètres → Général** permet aussi de lancer l'application à la
connexion de l'utilisateur. Ce réglage utilise l'exécutable autonome courant et
ne demande pas de droits administrateur.

## Modes du presse-papiers

- **Sélection manuelle uniquement** : mode par défaut et le plus prévisible.
- **Demander avant la lecture** : une confirmation apparaît après une copie manuelle.
- **Lire automatiquement le presse-papiers** : chaque nouveau texte copié est lu.

Pour Lire la sélection, l'application sauvegarde le presse-papiers, envoie Copier à
l'application active, attend un changement réel, récupère le texte Unicode puis
restaure le contenu précédent. Ses propres changements sont ignorés par la
surveillance automatique afin d'éviter les lectures en double.

## Synthèse vocale

### Edge-TTS

Edge-TTS est le moteur par défaut. Il ne demande pas de clé API, mais nécessite une
connexion Internet au service vocal Microsoft Edge. La liste proposée contient des
voix françaises de France, Belgique et Canada, ainsi que des voix anglaises.

Utilisez **Tester la synthèse vocale** pour vérifier la configuration.

Pour une validation automatisable de toute la chaîne avec le moteur configuré,
lancez `SpeakHelper.exe --tts-probe`. Le code de sortie `0` confirme la synthèse,
le démarrage de la lecture Qt et sa fin normale.

### Serveur compatible OpenAI

Le moteur générique envoie :

```text
POST {url_de_base}/audio/speech
```

Vous pouvez régler l'URL, le modèle, la voix, la vitesse, le délai et la clé API.
La clé est facultative pour un serveur local qui n'en exige pas. Les refus de
connexion, délais dépassés, erreurs HTTP, réponses vides et types audio invalides
sont signalés clairement.

### Qwen3-TTS local

Le préréglage **Qwen3-TTS local** utilise le même client compatible OpenAI et
préremplit une URL locale modifiable, le modèle publié
`Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice` et la voix `Vivian`. Lancez séparément un
serveur Qwen3-TTS qui expose `/audio/speech`, puis adaptez l'URL, le modèle et la
voix. Ce préréglage transmet aussi `language` avec la valeur `English` ou `French`
selon la langue de l'interface.

L'application de bureau n'installe ni PyTorch, ni CUDA, ni Qwen ; l'environnement
GPU reste complètement isolé. Consultez le
[projet officiel Qwen3-TTS](https://github.com/QwenLM/Qwen3-TTS). Des serveurs
compatibles existent, notamment
[qwen3_audio_api](https://github.com/second-state/qwen3_audio_api) et
[qwen3-tts-server](https://github.com/malaiwah/qwen3-tts-server), sans être
embarqués ni imposés par Speak Helper.

## Lecture et normalisation

- Une nouvelle sélection arrête immédiatement l'ancienne lecture et sa file.
- Les commandes Pause, Reprendre, Arrêter et Relire sont disponibles dans la zone
  de notification et par raccourci.
- Le nettoyage Markdown reste conservateur.
- Le code source entre blocs balisés est lu par défaut.
- Les accents français, Unicode et textes multilignes sont conservés.

## Diagnostic

Dans **Paramètres → Diagnostic**, vous trouverez : version, Windows, langue,
raccourci et état d'enregistrement, surveillance du presse-papiers, moteur/URL/modèle
TTS, état audio, chemins du cache et des journaux.

Les journaux structurés restent en anglais. Ils ne contiennent ni clé API, ni en-tête
d'autorisation, ni texte complet du presse-papiers ou de l'OCR.

## Dépannage

### Le raccourci ne produit rien

1. Consultez l'état d'enregistrement dans Diagnostic.
2. Changez le raccourci s'il est déjà utilisé.
3. Vérifiez que l'application cible accepte `Ctrl+C` sur la sélection.
4. Une application normale ne peut pas injecter Copier dans une application lancée
   comme administrateur ; utilisez le même niveau de privilège.
5. Augmentez le délai de sélection pour un fournisseur de presse-papiers lent.

### La voix échoue

- Lancez le test TTS dans Paramètres.
- Pour Edge-TTS, vérifiez Internet et choisissez une voix de la liste.
- Pour un serveur local, vérifiez l'URL et la route `/audio/speech`.
- Consultez le journal via Diagnostic pour identifier l'étape exacte.

## Développement et compilation

```powershell
uv sync --extra dev
.\scripts\check.ps1
.\scripts\build_win.ps1
```

La compilation produit `dist\SpeakHelper\SpeakHelper.exe` et une archive ZIP. Le
poste utilisateur final n'a besoin ni de Python, ni de `uv`.

Les validations encore nécessaires sont indiquées dans la
[matrice Windows](../development/windows_test_matrix.md) et la
[liste de publication](../development/release_checklist.md).

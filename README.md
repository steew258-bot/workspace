# Ops Agent

Assistant IA personnel modulaire : chaque tâche du quotidien (triage, veille,
planification) est un module avec un contrat d'entrée/sortie strict (JSON
structuré) et un test qui vérifie sa fiabilité, comme du vrai logiciel.

Voir [docs/Ops-Agent.pdf](docs/Ops-Agent.pdf) pour le cadrage complet du projet
(concept, monétisation, plan d'action).

## Modules

- **triage** — texte libre (email, tâche, notification) → action à
  entreprendre, niveau d'urgence, brouillon de réponse
- **veille** — liste brute d'infos/alertes → éléments prioritaires à traiter
  + archive
- **planification** — tâches et contraintes du jour → ordre optimisé et
  tâche à plus fort levier
- **resume** — texte long (compte-rendu, doc, fil d'emails) → résumé court
  + points clés

## Prérequis

- Python 3.12+
- Une clé API Anthropic (console.anthropic.com) — un usage quotidien léger
  (quelques appels/jour) coûte quelques centimes, un petit crédit de
  quelques euros suffit largement pour commencer.

## Installation

```bash
python -m venv .venv
.venv/Scripts/activate   # Windows
pip install -r requirements.txt
```

Définir la clé API Anthropic — copier `.env.example` en `.env` et y
renseigner la clé (chargé automatiquement au démarrage), ou l'exporter
directement :

```bash
cp .env.example .env   # puis editer .env
# ou
export ANTHROPIC_API_KEY=sk-...   # ou set sur Windows
```

## Utilisation

```bash
python app.py triage "Le client X demande un geste commercial avant vendredi"
python app.py veille "$(cat docs/veille-sources.txt)"          # liste manuelle
python app.py veille-feeds docs/veille-feeds.txt               # scraping RSS reel
python app.py planification "Repondre a 3 clients, preparer un devis, relancer un impaye"
python app.py resume "$(cat compte-rendu.txt)"
```

Chaque commande affiche un JSON structuré sur stdout.

## Automatisation

`.github/workflows/veille.yml` exécute chaque jour à 7h UTC
`veille-feeds` sur les flux RSS listés dans `docs/veille-feeds.txt`
(scraping réel, pas de watchlist manuelle à maintenir) et ouvre une
issue GitHub avec les résultats. Nécessite le secret de repo
`ANTHROPIC_API_KEY`.

## Développement

```bash
ruff check .
pytest
```

La CI (`.github/workflows/ci.yml`) lance ces deux commandes sur chaque
push/PR vers `master`.

## Ajouter un module

Chaque module suit le même contrat, dans `src/modules/<nom>.py` :

1. Un `SYSTEM_PROMPT` qui impose une réponse JSON stricte (liste des
   champs attendus).
2. `REQUIRED_KEYS` + une fonction `_parse_response(raw_text)` qui parse
   et valide ce JSON, et lève une exception dédiée (`<Nom>Error`) sinon.
3. Une fonction publique `<nom>(text, client=None)` qui appelle l'API et
   passe la réponse à `_parse_response`.
4. Un fichier `test/test_<nom>.py` qui teste `_parse_response` sur des
   cas fixes (valide, champ manquant, type invalide, JSON cassé) — pas
   d'appel réseau réel.
5. Un enregistrement dans `app.py` (import + sous-parser argparse +
   entrée dans le dict `handlers`) et un cas ajouté dans
   `test/test_app.py`.

## Licence

Voir [LICENSE.md](LICENSE.md) — usage personnel et commercial autorisé,
revente ou redistribution du template lui-même interdite.

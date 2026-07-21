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

## Installation

```bash
python -m venv .venv
.venv/Scripts/activate   # Windows
pip install -r requirements.txt
```

Définir la clé API Anthropic :

```bash
export ANTHROPIC_API_KEY=sk-...   # ou set sur Windows
```

## Utilisation

```bash
python app.py triage "Le client X demande un geste commercial avant vendredi"
python app.py veille "$(cat docs/veille-sources.txt)"          # liste manuelle
python app.py veille-feeds docs/veille-feeds.txt               # scraping RSS reel
python app.py planification "Repondre a 3 clients, preparer un devis, relancer un impaye"
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

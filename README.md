# Ops Agent

Assistant IA personnel modulaire : chaque tâche du quotidien (triage, veille,
planification) est un module avec un contrat d'entrée/sortie strict (JSON
structuré) et un test qui vérifie sa fiabilité, comme du vrai logiciel.

Premier démarrage ? Voir [GETTING_STARTED.md](GETTING_STARTED.md) pour
une installation guidée en une dizaine de minutes. Ce document-ci est la
référence technique complète.

## Modules

- **triage** — texte libre (email, tâche, notification) → action à
  entreprendre, niveau d'urgence, brouillon de réponse
- **veille** — liste brute d'infos/alertes → éléments prioritaires à traiter
  + archive
- **planification** — tâches et contraintes du jour → ordre optimisé et
  tâche à plus fort levier
- **resume** — texte long (compte-rendu, doc, fil d'emails) → résumé court
  + points clés. Avec `--export-docx`, génère en plus un vrai document
  Word (voir "Génération de fichiers réels" plus bas)
- **email** — email (expéditeur/objet/corps) → urgence, action, brouillon
  de réponse ; connecté en réel à une boîte mail (lecture IMAP des non-lus,
  envoi SMTP)
- **recherche** — question en langage naturel → réponse synthétique avec
  sources, via une recherche web en temps réel (API Perplexity)
- **crm** — notes d'échanges avec un client/prospect → statut du dossier,
  relance à faire, prochaine action, risque de churn. Avec
  `--export-xlsx`, génère en plus une vraie fiche Excel (voir
  "Génération de fichiers réels" plus bas)
- **agenda** — événements et contraintes du jour → conflits détectés,
  créneaux libres, suggestions de replanification ; `agenda-check`
  connecte ça en réel à Google Calendar (OAuth)
- **facturation** — description de prestation → brouillon de devis
  structuré (lignes, quantités, prix) ; n'invente jamais de prix non
  précisé dans le texte. Avec `--export-xlsx`, génère en plus un vrai
  fichier Excel (voir "Génération de fichiers réels" plus bas)

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
python app.py resume "..." --export-docx rapport.docx           # vrai document Word
python app.py email "De: client@exemple.com\nObjet: Urgent\n\nMerci de rappeler avant 18h."
python app.py email-check
python app.py email-send client@exemple.com "Re: Urgent" "C'est note, je vous rappelle."
python app.py whatsapp +33600000000 "Message a envoyer"
python app.py recherche "Quelles sont les dernieres annonces d'Anthropic ?"
python app.py crm "Appel du 12/07 : interesse mais budget pas encore valide, doit revenir vers nous."
python app.py crm "..." --export-xlsx fiches/dupont.xlsx        # vraie fiche Excel
python app.py agenda "RDV client 14h-15h ; appel fournisseur 14h30 ; dentiste 17h"
python app.py agenda-check                                      # vrais evenements Google Calendar
python app.py facturation "2 jours de dev a 500e/jour pour le client Dupont"
python app.py facturation "..." --export-xlsx factures/dupont.xlsx  # vrai fichier Excel
python app.py doctor                                            # diagnostic de la config
```

Chaque commande affiche un JSON structuré sur stdout.

## Diagnostic (`doctor`)

```bash
python app.py doctor
```

Vérifie `.env` et indique, module par module, ce qui manque, est resté à
la valeur d'exemple de `.env.example` (donc pas vraiment configuré), ou a
un format visiblement invalide (`EMAIL_ADDRESS` sans `@`,
`WHATSAPP_API_URL` sans `http(s)://`, port non numérique,
`WHATSAPP_NOTIFY_TO` pas au format E.164) — sans faire aucun appel
réseau. Renvoie aussi des avertissements de sécurité (ex :
`WHATSAPP_APP_SECRET` toujours à sa valeur d'exemple publique,
`WHATSAPP_NOTIFY_TO` absente ou mal formée). Code de sortie `0` si tous
les modules sont utilisables, `1` sinon — utilisable dans un script ou
avant de lancer une automatisation.

## Génération de fichiers réels (Agent Skills)

Trois modules peuvent, en plus de leur JSON habituel, générer un vrai
fichier via les **Agent Skills** d'Anthropic (fonctionnalité beta) — plus
besoin de retaper le résultat dans un tableur ou un traitement de texte :

| Module        | Flag            | Fichier généré                      |
| ------------- | --------------- | ------------------------------------ |
| `facturation` | `--export-xlsx` | Devis Excel (lignes, prix, total)    |
| `crm`         | `--export-xlsx` | Fiche de suivi client Excel          |
| `resume`      | `--export-docx` | Rapport Word (résumé + points clés)  |

```bash
python app.py facturation "2 jours de dev a 500e/jour pour le client Dupont" \
  --export-xlsx factures/dupont.xlsx
python app.py crm "Appel du 12/07 : interesse mais budget pas encore valide" \
  --export-xlsx fiches/dupont.xlsx
python app.py resume "$(cat compte-rendu.txt)" --export-docx rapport.docx
```

Le JSON de sortie contient alors une clé `fichier_xlsx` ou `fichier_docx`
avec le chemin du fichier généré. Le dossier de destination est créé
automatiquement s'il n'existe pas ; les dossiers d'export habituels
(`factures/`, `fiches/`) sont ignorés par git (`.gitignore`) puisque leur
contenu est propre à chaque utilisateur du template.

**Coût** : cette fonctionnalité consomme du temps de conteneur d'exécution
de code sur l'API Anthropic — gratuit jusqu'à un quota mensuel, puis
facturé. `python app.py doctor` rappelle ce point à chaque exécution.

## Recherche

Recherche web en temps réel via l'API Perplexity (modèle `sonar`) — utile
pour tout ce qui dépasse les flux RSS configurés dans `veille`. Contrairement
aux autres modules, la structure de sortie (`reponse`, `sources`) est
construite directement à partir de la réponse de l'API plutôt que demandée
au modèle : pas de parsing de JSON généré par un LLM, moins de risque
d'erreur de format.

```bash
python app.py recherche "Quelles sont les dernieres annonces d'Anthropic ?"
```

Renvoie `{"reponse": "...", "sources": ["<url>", ...]}`.

Nécessite dans `.env` :

- `PERPLEXITY_API_KEY` (perplexity.ai/settings/api)

## Agenda

`agenda` (analyse manuelle) fonctionne avec la seule clé Anthropic —
colle une liste d'événements en texte libre, reçois conflits/créneaux
libres/suggestions. `agenda-check` va plus loin : il lit tes vrais
événements du jour sur **Google Calendar** avant de lancer la même
analyse. Cette seconde partie demande une configuration OAuth 2.0, plus
lourde que les autres intégrations (mot de passe d'application ou clé
API simple) — compte une dizaine de minutes la première fois.

```bash
python app.py agenda "RDV client 14h-15h ; appel fournisseur 14h30 ; dentiste 17h"
python app.py agenda-check                    # aujourd'hui
python app.py agenda-check --date 2026-08-06   # une date precise
```

### Configuration de `agenda-check`

1. Sur [console.cloud.google.com](https://console.cloud.google.com),
   crée un projet (ou réutilise un projet existant).
2. **APIs & Services → Library** : active **Google Calendar API**.
3. **APIs & Services → OAuth consent screen** : configure un écran de
   consentement en mode "External" (ou "Internal" si tu as un Google
   Workspace) ; en mode test, ajoute ton propre compte Google comme
   utilisateur de test.
4. **APIs & Services → Credentials → Create Credentials → OAuth client
   ID**, type **Application de bureau**. Note le Client ID et le Client
   Secret.
5. Édite les identifiants créés et ajoute exactement cette URI de
   redirection autorisée : `http://localhost:8765/oauth2callback`
6. Renseigne dans `.env` :

   ```
   GOOGLE_CLIENT_ID=...
   GOOGLE_CLIENT_SECRET=...
   ```

7. Lance l'autorisation unique :

   ```bash
   python scripts/google_oauth_setup.py
   ```

   Une page Google s'ouvre dans ton navigateur ; après acceptation, le
   script affiche un `GOOGLE_REFRESH_TOKEN` à copier dans `.env`. Ce
   token ne change plus ensuite (sauf révocation manuelle de l'accès
   sur [myaccount.google.com/permissions](https://myaccount.google.com/permissions)).

`python app.py doctor` confirme quand tout est en place.

## Email

Intégration réelle avec une boîte mail (IMAP en lecture, SMTP en envoi),
sans dépendance externe (uniquement la bibliothèque standard Python).

### Analyse manuelle

```bash
python app.py email "De: ...\nObjet: ...\n\n<corps>"
```

Renvoie `urgence`, `necessite_reponse`, `action` et `brouillon_reponse`.

### Lecture automatique (`email-check`)

```bash
python app.py email-check [--mailbox INBOX] [--max 10]
```

Récupère les emails non lus par IMAP, les passe un par un au module
d'analyse, puis marque comme lus uniquement ceux traités avec succès (un
échec d'analyse sur un message ne fait pas perdre les autres, et le
message en échec reste non lu pour un prochain passage). C'est le pendant
de `veille-feeds` pour les emails : automatisé toutes les 30 minutes via
`.github/workflows/email-check.yml` (voir section Automatisation).

### Envoi (`email-send`)

```bash
python app.py email-send <destinataire> "<objet>" "<corps>"
```

Nécessite dans `.env` :

- `EMAIL_IMAP_HOST`, `EMAIL_IMAP_PORT` (défaut `993`) — pour `email-check`
- `EMAIL_SMTP_HOST`, `EMAIL_SMTP_PORT` (défaut `587`) — pour `email-send`
- `EMAIL_ADDRESS`, `EMAIL_PASSWORD`
- `EMAIL_MAILBOX` (défaut `INBOX`)

⚠️ Utiliser un **mot de passe d'application** (Gmail, Outlook...), jamais
le mot de passe principal du compte, et activer l'accès IMAP côté
fournisseur. La connexion IMAP se fait en SSL et l'envoi SMTP en
STARTTLS.

### Notifications proactives

Comme `triage`/`veille`, les commandes `email` (urgence `"haute"`) et
`email-check` (au moins un message à `"haute"` urgence parmi les traités)
déclenchent une notification WhatsApp proactive si `WHATSAPP_NOTIFY_TO`
est défini (voir section WhatsApp ci-dessous).

## WhatsApp

Intégration avec l'API WhatsApp Cloud de Meta, dans les deux sens.

### Envoi (sortant)

```bash
python app.py whatsapp <numero_E.164> "message"
```

Nécessite dans `.env` :

- `WHATSAPP_API_URL` (ex: `https://graph.facebook.com/v20.0`)
- `WHATSAPP_PHONE_NUMBER_ID`
- `WHATSAPP_ACCESS_TOKEN`

### Réception (webhook entrant)

```bash
python app.py webhook --port 8000
```

Démarre un serveur (WSGI de production, `waitress`) qui reçoit les
messages WhatsApp entrants, les passe au module `triage`, et renvoie le
résultat (action, urgence, brouillon de réponse) à l'expéditeur via
WhatsApp.

Nécessite en plus dans `.env` :

- `WHATSAPP_VERIFY_TOKEN` — valeur choisie par toi, à renseigner aussi
  côté config du webhook dans le dashboard Meta (handshake de
  vérification).
- `WHATSAPP_APP_SECRET` — utilisé pour vérifier la signature des
  requêtes entrantes (`X-Hub-Signature-256`). Optionnel mais fortement
  recommandé : sans lui, n'importe qui connaissant l'URL peut poster de
  faux messages sur le webhook.

Pour tester en local, le serveur doit être joignable depuis internet
(Meta appelle ton webhook) — utiliser un tunnel type `ngrok http 8000`
et renseigner l'URL publique + le verify token dans le dashboard
Meta (WhatsApp > Configuration > Webhook).

### Notifications proactives (sortant automatique)

Si `WHATSAPP_NOTIFY_TO` est défini dans `.env`, les commandes `triage`,
`veille`, `veille-feeds`, `email`, `email-check`, `crm` et `agenda`
envoient automatiquement un WhatsApp à ce numéro quand le résultat est
jugé important :

- `triage` / `email` : urgence `"haute"`
- `veille` / `veille-feeds` : au moins un élément dans `a_traiter`
- `email-check` : au moins un message traité à urgence `"haute"`
- `crm` : risque de churn `"eleve"`
- `agenda` : au moins un conflit détecté

Sans `WHATSAPP_NOTIFY_TO`, ce comportement est inactif (rien ne change).
Un échec d'envoi de notification n'interrompt jamais la commande — il
est juste signalé sur stderr.

⚠️ WhatsApp interdit l'envoi de texte libre à quelqu'un qui ne t'a pas
écrit dans les dernières 24h ("customer service window"). Pour des
notifications proactives fiables au-delà de cette fenêtre, crée un
[message template](https://business.facebook.com/wa/manage/message-templates/)
approuvé par Meta (une seule variable texte dans le corps) et renseigne :

- `WHATSAPP_NOTIFY_TEMPLATE` — le nom du template
- `WHATSAPP_NOTIFY_TEMPLATE_LANG` — son code langue (défaut `fr`)

Le contenu de la notification est alors envoyé comme variable du
template au lieu d'un message texte libre.

## Automatisation

`.github/workflows/veille.yml` exécute chaque jour à 7h UTC
`veille-feeds` sur les flux RSS listés dans `docs/veille-feeds.txt`
(scraping réel, pas de watchlist manuelle à maintenir) et ouvre une
issue GitHub avec les résultats. Nécessite le secret de repo
`ANTHROPIC_API_KEY`.

`.github/workflows/email-check.yml` exécute `email-check` toutes les 30
minutes (veille email quasi permanente) et ouvre une issue GitHub
uniquement s'il y a des emails traités (pas d'issue si la boîte est
vide, pour éviter le bruit). Si `WHATSAPP_NOTIFY_TO` est aussi configuré
en secret, les emails urgents déclenchent en plus une notification
WhatsApp immédiate (voir "Notifications proactives" dans la section
Email). Nécessite les secrets de repo :

- `ANTHROPIC_API_KEY`
- `EMAIL_IMAP_HOST`, `EMAIL_IMAP_PORT`, `EMAIL_ADDRESS`, `EMAIL_PASSWORD`,
  `EMAIL_MAILBOX` (mêmes valeurs que dans `.env`, voir section Email)
- optionnel : `WHATSAPP_API_URL`, `WHATSAPP_PHONE_NUMBER_ID`,
  `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_NOTIFY_TO` (et
  `WHATSAPP_NOTIFY_TEMPLATE`/`_LANG` si au-delà de la fenêtre de 24h) pour
  la notification proactive

Les secrets de repo (Settings > Secrets and variables > Actions) sont
indépendants du `.env` local — il faut les renseigner séparément pour que
les workflows fonctionnent.

## Développement

```bash
ruff check .
ruff format --check .           # verifie le style (ruff format . pour corriger)
mypy app.py src scripts
pytest
pip-audit -r requirements.txt   # scanne les dependances pour des CVE connues
```

La CI (`.github/workflows/ci.yml`) lance ces trois commandes sur chaque
push/PR vers `master`. `test/` n'est volontairement pas passé à mypy
(mocking intensif, peu de valeur à le typer strictement).

## Démo hors-ligne

```bash
python scripts/demo.py
```

Rejoue chaque module avec un exemple réaliste et sa sortie JSON
attendue, sans appeler l'API Anthropic ni nécessiter de configuration —
utile pour se faire une idée du résultat avant même d'avoir une clé
API. Les exemples sont vérifiés en test contre le vrai contrat de
chaque module (`test/test_demo.py`), donc jamais mensongers.

## Packaging pour distribution

```bash
python scripts/package_for_sale.py
```

Génère `dist/ops-agent-<date>.zip` : une copie propre du repo, sans
`.env` (jamais de vrais secrets dans l'archive), `.git`, `.venv` ni
caches. Inclut `.env.example`. C'est ce zip qui est fait pour être
uploadé tel quel sur une plateforme de vente (Gumroad...).

## Ajouter un module

Chaque module suit le même contrat, dans `src/modules/<nom>.py` :

1. Un `SYSTEM_PROMPT` qui impose une réponse JSON stricte (liste des
   champs attendus).
2. `REQUIRED_KEYS` + une fonction `_parse_response(raw_text)` qui délègue
   le parsing générique (JSON valide, objet, champs requis présents) à
   `parse_json_object(raw_text, REQUIRED_KEYS, <Nom>Error)` dans
   `src/modules/_client.py`, puis ajoute la validation spécifique au
   module (types, valeurs autorisées...) et lève `<Nom>Error` sinon.
3. Une fonction publique `<nom>(text, client=None)` qui appelle l'API et
   passe la réponse à `_parse_response`.
4. Un fichier `test/test_<nom>.py` qui teste `_parse_response` sur des
   cas fixes (valide, champ manquant, type invalide, JSON cassé) — pas
   d'appel réseau réel.
5. Un enregistrement dans `app.py` (import + sous-parser argparse +
   entrée dans le dict `handlers`) et un cas ajouté dans
   `test/test_app.py`.

Optionnel : si le module doit aussi générer un vrai fichier (Excel, Word...),
reprendre le pattern `<nom>_export_<format>(data, output_path, client=None)`
utilisé par `facturation`/`crm`/`resume` (voir "Génération de fichiers
réels" plus haut), qui délègue à `generate_file_with_skill()` dans
`src/modules/_skills.py` — pas besoin de redériver la logique d'appel aux
Agent Skills.

## Licence

Voir [LICENSE.md](LICENSE.md) — usage personnel et commercial autorisé,
revente ou redistribution du template lui-même interdite.

# Premiers pas avec Ops Agent

Merci pour ton achat. Ce guide t'accompagne du zip téléchargé à ta
première commande qui fonctionne, en une dizaine de minutes. Pour la
référence technique complète (tous les modules, toutes les options),
voir `README.md` — ce guide-ci ne couvre que le strict nécessaire pour
démarrer.

## 1. Vérifier Python

Il faut Python 3.12 ou plus récent :

```bash
python --version
```

Si ce n'est pas le cas, installe-le depuis [python.org](https://python.org).

## 2. Dézipper et installer

```bash
unzip ops-agent-*.zip -d ops-agent
cd ops-agent
python -m venv .venv
.venv/Scripts/activate      # Windows
# ou : source .venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
```

## 3. Créer ta clé API Anthropic

C'est le seul coût récurrent, et il est faible : un usage quotidien
léger (quelques appels par jour) coûte quelques centimes. Un petit
crédit de quelques euros suffit largement pour commencer.

1. Va sur [console.anthropic.com](https://console.anthropic.com)
2. **Settings → API Keys → Create Key**
3. Copie la clé générée (elle commence par `sk-ant-`)

## 4. Configurer

```bash
cp .env.example .env
```

Ouvre `.env` dans un éditeur de texte et remplace la ligne
`ANTHROPIC_API_KEY=sk-ant-...` par ta vraie clé.

## 5. Vérifier que tout est prêt

```bash
python app.py doctor
```

Cette commande te dit précisément, module par module, ce qui est
configuré et ce qu'il manque encore — sans faire aucun appel réseau ni
rien te coûter. Relance-la à chaque fois que tu ajoutes une
configuration pour confirmer que c'est pris en compte.

## 6. Ta première commande

```bash
python app.py triage "Le client X demande un geste commercial avant vendredi"
```

Tu devrais voir un JSON avec une action suggérée, un niveau d'urgence et
un brouillon de réponse. Si tu vois plutôt une erreur `ANTHROPIC_API_KEY`,
relis l'étape 4 — la clé n'a probablement pas été remplacée.

## Aller plus loin

Cinq autres modules d'analyse fonctionnent avec la seule clé Anthropic
déjà configurée : `veille`, `planification`, `resume`, `crm`, `agenda`,
`facturation`. Essaie-les avec `python app.py <module> "<ton texte>"`.

Astuce : `facturation --export-xlsx`, `crm --export-xlsx` et `resume
--export-docx` génèrent en plus un vrai fichier (Excel ou Word) à partir
du résultat (fonctionnalité beta, détails dans `README.md`, section
"Génération de fichiers réels").

Trois intégrations demandent une configuration en plus (détails dans
`README.md`) :

- **email** (lecture/envoi réels) — un compte mail avec mot de passe
  d'application
- **whatsapp** — un compte développeur Meta / WhatsApp Cloud API
- **recherche** — une clé API Perplexity

`python app.py doctor` te dira exactement quelles variables il manque
pour chacun quand tu voudras les activer.

## Problèmes fréquents

- **"ANTHROPIC_API_KEY manquante" ou erreur 401** — la clé dans `.env`
  est encore la valeur d'exemple `sk-ant-...`, ou le fichier `.env`
  n'existe pas (as-tu fait `cp .env.example .env` ?).
- **Module email : la connexion échoue** — utilise un *mot de passe
  d'application*, jamais ton mot de passe de messagerie normal (Gmail,
  Outlook...). La procédure exacte est dans `README.md`, section Email.
- **`python` introuvable** — essaie `python3` à la place, selon ton
  système.

## Une fois que tout tourne

`README.md` documente en détail : chaque module et son format de
sortie, l'automatisation par cron (GitHub Actions), les notifications
WhatsApp proactives, et comment ajouter ton propre module en suivant le
même contrat que les modules existants.

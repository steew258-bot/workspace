# Getting started with Ops Agent

Thanks for your purchase. This guide takes you from the downloaded zip
to your first working command in about ten minutes. For the full
technical reference (every module, every option), see `README.en.md` —
this guide only covers the strict essentials to get started.

Ce guide existe aussi en français : voir
[GETTING_STARTED.md](GETTING_STARTED.md).

## 1. Check Python

You need Python 3.12 or newer:

```bash
python --version
```

If not, install it from [python.org](https://python.org).

## 2. Unzip and install

```bash
unzip ops-agent-*.zip -d ops-agent
cd ops-agent
python -m venv .venv
.venv/Scripts/activate      # Windows
# or: source .venv/bin/activate   # Mac/Linux
pip install -r requirements.txt
```

## 3. Create your Anthropic API key

This is the only recurring cost, and it's low: light daily use (a few
calls a day) costs a few cents. A small credit of a few dollars is
plenty to get started.

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. **Settings → API Keys → Create Key**
3. Copy the generated key (it starts with `sk-ant-`)

## 4. Configure

```bash
cp .env.example .env
```

Open `.env` in a text editor and replace the
`ANTHROPIC_API_KEY=sk-ant-...` line with your real key.

Optional: to get English output (system prompts, JSON field names, CLI
help, `doctor` messages), also set `OPS_AGENT_LANG=en` in `.env` — see
`README.en.md`, section "Bilingual (fr/en)". By default everything is
in French.

## 5. Check that everything is ready

```bash
python app.py doctor
```

This command tells you precisely, module by module, what's configured
and what's still missing — without making any network call or costing
you anything. Rerun it every time you add a configuration to confirm
it's picked up.

## 6. Your first command

```bash
python app.py triage "Client X is asking for a goodwill gesture before Friday"
```

You should see JSON with a suggested action, an urgency level and a
draft reply. If you instead see an `ANTHROPIC_API_KEY` error, re-check
step 4 — the key probably wasn't replaced.

## Going further

Five other analysis modules work with just the Anthropic key already
configured: `veille`, `planification`, `resume`, `crm`, `agenda`,
`facturation`. Try them with `python app.py <module> "<your text>"`.

Tip: `facturation --export-xlsx`, `crm --export-xlsx` and `resume
--export-docx` additionally generate a real file (Excel or Word) from
the result (beta feature, details in `README.en.md`, section "Real
file generation").

Four integrations require extra configuration (details in
`README.en.md`):

- **email** (real read/send) — a mail account with an app password
- **whatsapp** — a Meta developer account / WhatsApp Cloud API
- **recherche** (search) — a Perplexity API key
- **agenda-check** — OAuth connection to Google Calendar (free, about
  ten minutes the first time; see README, Calendar section, "Common
  pitfalls" if you get stuck on the Client ID/Secret)

`python app.py doctor` will tell you exactly which variables are
missing for each one when you want to enable them.

## Common issues

- **"ANTHROPIC_API_KEY missing" or a 401 error** — the key in `.env` is
  still the example value `sk-ant-...`, or the `.env` file doesn't
  exist (did you run `cp .env.example .env`?).
- **Email module: connection fails** — use an *app password*, never
  your normal mailbox password (Gmail, Outlook...). The exact procedure
  is in `README.en.md`, Email section.
- **`python` not found** — try `python3` instead, depending on your
  system.
- **Google Calendar: "OAuth client not found" or "Error 403:
  access_denied"** — a common pitfall when configuring `agenda-check`
  (Client ID/Secret confused with a service account's, or the account
  not yet added as a tester). Details in `README.en.md`, Calendar
  section → "Common pitfalls".

## Once everything is running

`README.en.md` documents in detail: each module and its output format,
cron automation (GitHub Actions), proactive WhatsApp notifications, the
`OPS_AGENT_LANG` bilingual switch, and how to add your own module
following the same contract as the existing ones.

# Ops Agent

A modular personal AI assistant: every everyday task (triage, monitoring,
planning) is a module with a strict input/output contract (structured
JSON) and a test that verifies its reliability, like real software.

First time here? See [GETTING_STARTED.en.md](GETTING_STARTED.en.md) for
a guided setup in about ten minutes. This document is the full technical
reference.

Ce document existe aussi en français : voir [README.md](README.md) et
[GETTING_STARTED.md](GETTING_STARTED.md).

## Modules

- **triage** — free-form text (email, task, notification) → action to
  take, urgency level, draft reply
- **veille** (monitoring) — raw list of information/alerts → priority
  items to review + archive
- **planification** (planning) — today's tasks and constraints →
  optimized order and highest-leverage task
- **resume** (summary) — long text (report, doc, email thread) → short
  summary + key points. With `--export-docx`, also generates a real
  Word document (see "Real file generation" below)
- **email** — email (sender/subject/body) → urgency, action, draft
  reply; connected for real to a mailbox (IMAP read of unread messages,
  SMTP send)
- **recherche** (search) — natural-language question → synthesized
  answer with sources, via real-time web search (Perplexity API)
- **crm** — exchange notes with a client/prospect → case status,
  follow-up needed, next action, churn risk. With `--export-xlsx`, also
  generates a real Excel sheet (see "Real file generation" below)
- **agenda** (calendar) — today's events and constraints → detected
  conflicts, free slots, rescheduling suggestions; `agenda-check`
  connects this for real to Google Calendar (OAuth)
- **facturation** (billing) — service description → structured draft
  quote (line items, quantities, prices); never invents a price not
  specified in the text. With `--export-xlsx`, also generates a real
  Excel file (see "Real file generation" below)

## Bilingual (fr/en)

Every steerable output (system prompts sent to Claude, JSON field
names, CLI `--help`, `doctor` messages, WhatsApp notifications) switches
to English with a single environment variable:

```bash
export OPS_AGENT_LANG=en   # or in .env: OPS_AGENT_LANG=en
python app.py triage "Client X is asking for a goodwill gesture before Friday"
```

By default (`OPS_AGENT_LANG` unset or `fr`), everything stays in
French — identical behavior to before this variable existed. In `en`
mode, JSON field names change too (e.g. `urgence` → `urgency`,
`brouillon_reponse` → `reply_draft`) — see the exact format of each
module in the sections below, or run `python scripts/demo.py` with
`OPS_AGENT_LANG=en` for a full preview.

## Prerequisites

- Python 3.12+
- An Anthropic API key (console.anthropic.com) — light daily use (a few
  calls a day) costs a few cents; a small credit of a few dollars is
  plenty to get started.

## Installation

```bash
python -m venv .venv
.venv/Scripts/activate   # Windows
pip install -r requirements.txt
```

Set the Anthropic API key — copy `.env.example` to `.env` and fill in
the key (loaded automatically at startup), or export it directly:

```bash
cp .env.example .env   # then edit .env
# or
export ANTHROPIC_API_KEY=sk-...   # or set on Windows
export OPS_AGENT_LANG=en          # optional, switches all output to English
```

## Usage

```bash
python app.py triage "Client X is asking for a goodwill gesture before Friday"
python app.py veille "$(cat docs/veille-sources.txt)"          # manual list
python app.py veille-feeds docs/veille-feeds.txt               # real RSS scraping
python app.py planification "Reply to 3 clients, prepare a quote, chase an unpaid invoice"
python app.py resume "$(cat report.txt)"
python app.py resume "..." --export-docx report.docx           # real Word document
python app.py email "From: client@example.com\nSubject: Urgent\n\nPlease call back before 6pm."
python app.py email-check
python app.py email-send client@example.com "Re: Urgent" "Noted, I'll call you back."
python app.py whatsapp +12025550123 "Message to send"
python app.py recherche "What are Anthropic's latest announcements?"
python app.py crm "Call on 07/12: interested but budget not yet approved, will get back to us."
python app.py crm "..." --export-xlsx sheets/smith.xlsx        # real Excel sheet
python app.py agenda "Client meeting 2-3pm ; supplier call 2:30pm ; dentist 5pm"
python app.py agenda-check                                     # real Google Calendar events
python app.py facturation "2 days of dev at $500/day for client Smith"
python app.py facturation "..." --export-xlsx invoices/smith.xlsx  # real Excel file
python app.py doctor                                           # config diagnostic
```

Each command prints structured JSON on stdout. Run any of these with
`OPS_AGENT_LANG=en` set to get English field names in the output.

## Diagnostic (`doctor`)

```bash
python app.py doctor
```

Checks `.env` and reports, module by module, what's missing, what's
still at the `.env.example` placeholder value (so not really
configured), or what has a visibly invalid format (`EMAIL_ADDRESS`
without `@`, `WHATSAPP_API_URL` without `http(s)://`, non-numeric port,
`WHATSAPP_NOTIFY_TO` not in E.164 format) — without making any network
call. Also returns security warnings (e.g. `WHATSAPP_APP_SECRET` still
at its public example value, `WHATSAPP_NOTIFY_TO` missing or malformed).
Exit code `0` if all modules are usable, `1` otherwise — usable in a
script or before launching an automation.

## Local web dashboard

```bash
python app.py dashboard              # http://127.0.0.1:8001
python app.py dashboard --port 8080  # different port
```

A small local web interface: the same configuration status as
`doctor`, rendered as HTML, plus a form to run any of the 9
text-in/JSON-out modules (`triage`, `veille`, `planification`,
`resume`, `email`, `crm`, `agenda`, `recherche`, `facturation`) and see
the result directly in the browser — handy for a demo or occasional
use without the command line. Proactive WhatsApp notifications fire
normally (same rules as the WhatsApp section below).

`email-check`, `agenda-check` and `veille-feeds` aren't in this form:
they don't take free-form text as input (they read a real mailbox,
Google Calendar, or an RSS feed file).

⚠️ Listens on `127.0.0.1` only (never `0.0.0.0` like the WhatsApp
webhook, which does need to be reachable from the internet) — no
authentication, local use only. Stores nothing between requests (no
history): every form submission really runs the module, including any
API cost involved.

## Real file generation (Agent Skills)

Three modules can, in addition to their usual JSON, generate a real
file via Anthropic's **Agent Skills** (beta feature) — no more retyping
the result into a spreadsheet or word processor:

| Module        | Flag            | File generated                     |
| ------------- | --------------- | ----------------------------------- |
| `facturation` | `--export-xlsx` | Excel quote (line items, prices, total) |
| `crm`         | `--export-xlsx` | Excel customer follow-up sheet     |
| `resume`      | `--export-docx` | Word report (summary + key points) |

```bash
python app.py facturation "2 days of dev at $500/day for client Smith" \
  --export-xlsx invoices/smith.xlsx
python app.py crm "Call on 07/12: interested but budget not yet approved" \
  --export-xlsx sheets/smith.xlsx
python app.py resume "$(cat report.txt)" --export-docx report.docx
```

The JSON output then contains a `xlsx_file` or `docx_file` key (in `fr`
mode: `fichier_xlsx`/`fichier_docx`) with the path of the generated
file. The destination folder is created automatically if it doesn't
exist; the usual export folders (`factures/`, `fiches/`) are ignored by
git (`.gitignore`) since their content is specific to each user of the
template.

**Cost**: this feature consumes code execution container time on the
Anthropic API — free up to a monthly quota, then billed. `python app.py
doctor` reminds you of this on every run.

## Search

Real-time web search via the Perplexity API (`sonar` model) — useful
for anything beyond the RSS feeds configured in `veille`. Unlike the
other modules, the output structure (`response`, `sources`) is built
directly from the API response rather than requested from the model: no
LLM-generated JSON to parse, less risk of a format error.

```bash
python app.py recherche "What are Anthropic's latest announcements?"
```

Returns `{"response": "...", "sources": ["<url>", ...]}` (in `fr` mode:
`{"reponse": "...", "sources": [...]}`).

Requires in `.env`:

- `PERPLEXITY_API_KEY` (perplexity.ai/settings/api)

## Calendar (`agenda`)

`agenda` (manual analysis) works with just the Anthropic key — paste a
free-text list of events, get back conflicts/free slots/suggestions.
`agenda-check` goes further: it reads your real events for the day from
**Google Calendar** before running the same analysis. This second part
requires an OAuth 2.0 setup, heavier than the other integrations (an
app password or a simple API key) — expect about ten minutes the first
time.

```bash
python app.py agenda "Client meeting 2-3pm ; supplier call 2:30pm ; dentist 5pm"
python app.py agenda-check                    # today
python app.py agenda-check --date 2026-08-06   # a specific date
```

### Configuring `agenda-check`

1. On [console.cloud.google.com](https://console.cloud.google.com),
   create a project (or reuse an existing one).
2. **APIs & Services → Library**: enable **Google Calendar API**.
3. **APIs & Services → OAuth consent screen**: configure a consent
   screen in "External" mode (or "Internal" if you have a Google
   Workspace); in test mode, add your own Google account as a test
   user.
4. **APIs & Services → Credentials → Create Credentials → OAuth client
   ID**, type **Desktop app**. Note the Client ID and Client Secret.
5. Edit the created credentials and add exactly this authorized
   redirect URI: `http://localhost:8765/oauth2callback`
6. Fill in `.env`:

   ```
   GOOGLE_CLIENT_ID=...
   GOOGLE_CLIENT_SECRET=...
   ```

7. Run the one-time authorization:

   ```bash
   python scripts/google_oauth_setup.py
   ```

   A Google page opens in your browser; after accepting, the script
   prints a `GOOGLE_REFRESH_TOKEN` to copy into `.env`. This token
   doesn't change afterward (unless access is manually revoked at
   [myaccount.google.com/permissions](https://myaccount.google.com/permissions)).

`python app.py doctor` confirms when everything is in place.

#### Common pitfalls

- **Client ID vs Client Secret vs Service Account.** Google Cloud has
  several credential types under "APIs & Services → Credentials": only
  an **"OAuth client ID"** (step 4) has both a Client ID *and* a Client
  Secret. A **"Service Account"** (often already present in the project
  for other uses, e.g. a Gemini API key) has a numeric ID but **no**
  "Client secret" — if you can't find that field, check that you're on
  an OAuth client page, not a service account. The Client ID always
  ends with `.apps.googleusercontent.com`; the Client Secret always
  starts with `GOCSPX-`. `python app.py doctor` checks this format and
  flags it if you swapped the two or pasted the wrong value (e.g. the
  redirect URI instead of the Client ID).
- **"Test users" has moved.** In the current Google Cloud interface
  ("Google Auth Platform"), the list of authorized testers is no longer
  under "Clients" but under the **"Audience"** tab in the left menu. If
  authorization fails with `Error 403: access_denied` ("the app is
  currently being tested"), your Google account isn't in that list yet
  — add it there.

## Email

Real integration with a mailbox (IMAP read, SMTP send), with no
external dependency (Python standard library only).

### Manual analysis

```bash
python app.py email "From: ...\nSubject: ...\n\n<body>"
```

Returns `urgency`, `requires_reply`, `action` and `reply_draft` (in
`fr` mode: `urgence`, `necessite_reponse`, `action`,
`brouillon_reponse`).

### Automatic reading (`email-check`)

```bash
python app.py email-check [--mailbox INBOX] [--max 10]
```

Fetches unread emails via IMAP, passes them one by one to the analysis
module, then marks as read only the ones successfully processed (a
failed analysis on one message doesn't lose the others, and the failed
message stays unread for a future pass). This is the email counterpart
of `veille-feeds`: automated every 30 minutes via
`.github/workflows/email-check.yml` (see the Automation section).

### Sending (`email-send`)

```bash
python app.py email-send <recipient> "<subject>" "<body>"
```

Requires in `.env`:

- `EMAIL_IMAP_HOST`, `EMAIL_IMAP_PORT` (default `993`) — for `email-check`
- `EMAIL_SMTP_HOST`, `EMAIL_SMTP_PORT` (default `587`) — for `email-send`
- `EMAIL_ADDRESS`, `EMAIL_PASSWORD`
- `EMAIL_MAILBOX` (default `INBOX`)

⚠️ Use an **app password** (Gmail, Outlook...), never your main account
password, and enable IMAP access on the provider side. The IMAP
connection uses SSL and SMTP sending uses STARTTLS.

### Proactive notifications

Like `triage`/`veille`, the `email` command (urgency `"high"`) and
`email-check` (at least one processed message with `"high"` urgency)
trigger a proactive WhatsApp notification if `WHATSAPP_NOTIFY_TO` is
set (see the WhatsApp section below).

## WhatsApp

Integration with Meta's WhatsApp Cloud API, in both directions.

### Sending (outbound)

```bash
python app.py whatsapp <E.164_number> "message"
```

Requires in `.env`:

- `WHATSAPP_API_URL` (e.g. `https://graph.facebook.com/v20.0`)
- `WHATSAPP_PHONE_NUMBER_ID`
- `WHATSAPP_ACCESS_TOKEN`

### Receiving (incoming webhook)

```bash
python app.py webhook --port 8000
```

Starts a server (production WSGI, `waitress`) that receives incoming
WhatsApp messages, passes them to the `triage` module, and sends the
result (action, urgency, draft reply) back to the sender via WhatsApp.

Additionally requires in `.env`:

- `WHATSAPP_VERIFY_TOKEN` — a value you choose, also entered on the
  webhook config side in the Meta dashboard (verification handshake).
- `WHATSAPP_APP_SECRET` — used to verify the signature of incoming
  requests (`X-Hub-Signature-256`). Optional but strongly recommended:
  without it, anyone who knows the URL can post fake messages to the
  webhook.

To test locally, the server must be reachable from the internet (Meta
calls your webhook) — use a tunnel like `ngrok http 8000` and enter the
public URL + verify token in the Meta dashboard (WhatsApp >
Configuration > Webhook).

### Proactive notifications (automatic outbound)

If `WHATSAPP_NOTIFY_TO` is set in `.env`, the `triage`, `veille`,
`veille-feeds`, `email`, `email-check`, `crm` and `agenda` commands
automatically send a WhatsApp message to that number when the result is
deemed important:

- `triage` / `email`: urgency `"high"`
- `veille` / `veille-feeds`: at least one item in `to_review`
- `email-check`: at least one processed message with `"high"` urgency
- `crm`: churn risk `"high"`
- `agenda`: at least one detected conflict

Without `WHATSAPP_NOTIFY_TO`, this behavior is inactive (nothing
changes). A notification send failure never interrupts the command — it
is just reported on stderr.

⚠️ WhatsApp forbids sending free text to someone who hasn't messaged you
in the last 24 hours (the "customer service window"). For reliable
proactive notifications beyond that window, create a
[message template](https://business.facebook.com/wa/manage/message-templates/)
approved by Meta (a single text variable in the body) and set:

- `WHATSAPP_NOTIFY_TEMPLATE` — the template name
- `WHATSAPP_NOTIFY_TEMPLATE_LANG` — its language code (default `fr`)

The notification content is then sent as the template variable instead
of a free-text message.

## Automation

`.github/workflows/veille.yml` runs `veille-feeds` every day at 7am UTC
on the RSS feeds listed in `docs/veille-feeds.txt` (real scraping, no
manual watchlist to maintain) and opens a GitHub issue with the
results. Requires the repo secret `ANTHROPIC_API_KEY`.

`.github/workflows/email-check.yml` runs `email-check` every 30 minutes
(near-permanent email monitoring) and opens a GitHub issue only if
there are processed emails (no issue if the mailbox is empty, to avoid
noise). If `WHATSAPP_NOTIFY_TO` is also configured as a secret, urgent
emails additionally trigger an immediate WhatsApp notification (see
"Proactive notifications" in the Email section). Requires the repo
secrets:

- `ANTHROPIC_API_KEY`
- `EMAIL_IMAP_HOST`, `EMAIL_IMAP_PORT`, `EMAIL_ADDRESS`,
  `EMAIL_PASSWORD`, `EMAIL_MAILBOX` (same values as in `.env`, see the
  Email section)
- optional: `WHATSAPP_API_URL`, `WHATSAPP_PHONE_NUMBER_ID`,
  `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_NOTIFY_TO` (and
  `WHATSAPP_NOTIFY_TEMPLATE`/`_LANG` if beyond the 24h window) for the
  proactive notification

Repo secrets (Settings > Secrets and variables > Actions) are
independent of the local `.env` — they need to be set separately for
the workflows to work.

## Development

```bash
ruff check .
ruff format --check .           # checks style (ruff format . to fix)
mypy app.py src scripts
pytest
pytest --cov=src --cov=app --cov-report=term-missing   # test coverage
pip-audit -r requirements.txt   # scans dependencies for known CVEs
```

CI (`.github/workflows/ci.yml`) runs these commands on every push/PR to
`master`. `test/` is deliberately not passed to mypy (heavy mocking,
little value in strictly typing it).

## Offline demo

```bash
python scripts/demo.py
OPS_AGENT_LANG=en python scripts/demo.py   # English sample outputs
```

Replays each module with a realistic example and its expected JSON
output, without calling the Anthropic API or requiring any
configuration — useful for getting a feel for the result before even
having an API key. The examples are checked in tests against each
module's real contract (`test/test_demo.py`), so they're never
misleading.

## Packaging for distribution

```bash
python scripts/package_for_sale.py
```

Generates `dist/ops-agent-<date>.zip`: a clean copy of the repo,
without `.env` (never real secrets in the archive), `.git`, `.venv` or
caches. Includes `.env.example`. This is the zip meant to be uploaded
as-is to a sales platform (Gumroad...).

## Adding a module

Every module follows the same bilingual contract, in
`src/modules/<name>.py`:

1. `SYSTEM_PROMPTS: dict[str, str]` — one system prompt per language
   (`"fr"`/`"en"`) that forces a strict JSON reply, with field names in
   the matching language.
2. `REQUIRED_KEYS: dict[str, set[str]]` (+ any enums like
   `VALID_URGENCY: dict[str, set[str]]`) — a set of valid fields/values
   per language.
3. `FIELDS: dict[str, dict[str, str]]` — **only if another file reads
   the module's output by field name** (e.g. `notifications.py`,
   `app.py`). Key = canonical logical name in English, value = `{"fr":
   "...", "en": "..."}`. Written by hand, not derived from
   `REQUIRED_KEYS[lang]` by zipping two sets (sets aren't ordered —
   that would be a latent bug).
4. `_parse_response(raw_text: str, lang: str | None = None) -> dict`:
   resolves `lang = get_lang(lang)` (imported from
   `src/modules/_client.py`), delegates the generic part (valid JSON,
   object, required fields present) to `parse_json_object(raw_text,
   REQUIRED_KEYS[lang], <Name>Error, lang=lang)`, then adds
   module-specific validation using the right language's literals and
   raises `<Name>Error` otherwise.
5. Public function `<name>(text, client=None, lang: str | None = None)`
   that resolves `lang = get_lang(lang)` first, calls the API with
   `SYSTEM_PROMPTS[lang]`, and passes the response to `_parse_response`.
6. A `test/test_<name>.py` file that tests `_parse_response` on fixed
   cases (valid, missing field, invalid type, broken JSON) — no real
   network call. Full bilingual coverage is recommended for modules
   with non-trivial validation (enums, nested lists); an English
   "happy path" test is enough for shapes already covered elsewhere
   (see `test/test_client.py` for the 3 generic errors tested once).
7. A registration in `app.py` (import + argparse subparser with
   `help=HELP["<name>_cmd"][lang]` + entry in the `handlers` dict) and
   a case added to `test/test_app.py`. **Never pass `lang=` explicitly
   in the module call from `app.py`**: every function already resolves
   the language via `get_lang(None)` from `OPS_AGENT_LANG`, and the
   mocked tests check the exact call
   (`mocked.assert_called_once_with("text")`, no `lang` kwarg).

Optional: if the module should also generate a real file (Excel,
Word...), reuse the `<name>_export_<format>(data, output_path,
client=None, lang: str | None = None)` pattern used by
`facturation`/`crm`/`resume` (see "Real file generation" above), which
reads fields from `data` via `FIELDS[lang]` (never hardcoded, or you'll
get a `KeyError` in `en` mode) and delegates to
`generate_file_with_skill()` in `src/modules/_skills.py` — no need to
reimplement the Agent Skills call logic.

## License

See [LICENSE.md](LICENSE.md) — personal and commercial use allowed,
reselling or redistributing the template itself is prohibited.

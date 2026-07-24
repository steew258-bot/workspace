"""Mini dashboard web local pour Ops Agent : statut de configuration
(doctor) et formulaire pour lancer un module directement depuis le
navigateur, sans ligne de commande.

Usage:
    python app.py dashboard
    python app.py dashboard --port 8001

Ecoute sur 127.0.0.1 par defaut (contrairement au webhook WhatsApp, qui
doit etre joignable depuis internet) : usage local uniquement, pas
d'authentification. Ne jamais exposer ce serveur publiquement.
"""

import html
import json
from collections.abc import Callable

from flask import Flask, request
from flask.typing import ResponseReturnValue

from src.diagnostics import FIELDS as DIAGNOSTICS_FIELDS
from src.diagnostics import check as check_environment
from src.modules._client import get_lang
from src.modules.agenda import agenda
from src.modules.crm import crm
from src.modules.email import email as email_triage
from src.modules.facturation import facturation
from src.modules.planification import planification
from src.modules.recherche import recherche
from src.modules.resume import resume
from src.modules.triage import triage
from src.modules.veille import veille
from src.notifications import notify_if_urgent

app = Flask(__name__)

# Ordre d'affichage dans le formulaire. Les fonctions elles-memes sont
# resolues dynamiquement dans run_module() (pas de dict fige au niveau
# module) pour que patch("src.dashboard.triage", ...) fonctionne dans les
# tests, comme le dict `handlers` construit a chaque appel dans app.py.
MODULE_NAMES = (
    "triage",
    "veille",
    "planification",
    "resume",
    "email",
    "crm",
    "agenda",
    "recherche",
    "facturation",
)

UI_TEXT = {
    "title": {"fr": "Ops Agent — Dashboard", "en": "Ops Agent — Dashboard"},
    "config_heading": {"fr": "Configuration", "en": "Configuration"},
    "warnings_heading": {"fr": "Avertissements", "en": "Warnings"},
    "run_heading": {"fr": "Lancer un module", "en": "Run a module"},
    "module_label": {"fr": "Module", "en": "Module"},
    "text_label": {"fr": "Texte", "en": "Text"},
    "submit_label": {"fr": "Lancer", "en": "Run"},
    "result_heading": {"fr": "Resultat", "en": "Result"},
    "error_heading": {"fr": "Erreur", "en": "Error"},
    "footer_note": {
        "fr": "Dashboard local uniquement, ecoute sur 127.0.0.1 — rien n'est "
        "stocke entre deux requetes.",
        "en": "Local dashboard only, listens on 127.0.0.1 — nothing is stored between requests.",
    },
}
_MISSING_TEXT_ERROR = {
    "fr": "Le champ texte est requis.",
    "en": "The text field is required.",
}
_UNKNOWN_MODULE_ERROR = {
    "fr": "Module inconnu : {module}",
    "en": "Unknown module: {module}",
}

_STYLE = """
  * { box-sizing: border-box; }
  :root {
    --bg: #F5F3EA; --panel: #ECE9E1; --border: rgba(25,29,31,0.15);
    --text: #191D1F; --muted: #5B6266; --accent: #146F63;
    --ok: #3C7350; --bad: #A93A26;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #14171A; --panel: #1B2023; --border: rgba(231,228,218,0.14);
      --text: #E7E4DA; --muted: #99A0A3; --accent: #5FC1B4;
      --ok: #86C29C; --bad: #E08669;
    }
  }
  body {
    margin: 0; padding: 2rem 1.25rem 3rem; background: var(--bg); color: var(--text);
    font-family: system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; line-height: 1.5;
  }
  main { max-width: 44rem; margin: 0 auto; display: flex; flex-direction: column; gap: 2rem; }
  h1 { font-size: 1.35rem; margin: 0; }
  h2 { font-size: 1.02rem; margin: 0 0 0.9rem; }
  section {
    background: var(--panel); border: 1px solid var(--border); border-radius: 8px;
    padding: 1.25rem 1.4rem;
  }
  table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
  td { padding: 0.4rem 0.3rem; border-top: 1px solid var(--border); vertical-align: top; }
  tr:first-child td { border-top: none; }
  .pill {
    display: inline-block; padding: 0.1em 0.6em; border-radius: 999px;
    font-size: 0.76rem; font-weight: 600;
  }
  .pill.ok { color: var(--ok); background: color-mix(in srgb, var(--ok) 16%, transparent); }
  .pill.bad { color: var(--bad); background: color-mix(in srgb, var(--bad) 16%, transparent); }
  .issues { color: var(--muted); font-size: 0.82rem; margin-top: 0.2rem; }
  ul.warnings { margin: 0; padding-left: 1.2rem; color: var(--muted); font-size: 0.86rem; }
  form { display: flex; flex-direction: column; gap: 0.8rem; }
  label { font-size: 0.86rem; color: var(--muted); }
  select, textarea, button {
    font: inherit; padding: 0.55rem 0.7rem; border-radius: 5px;
    border: 1px solid var(--border); background: var(--bg); color: var(--text);
  }
  textarea { min-height: 6rem; resize: vertical; }
  button {
    align-self: flex-start; background: var(--accent); color: #fff; border: none;
    padding: 0.6rem 1.3rem; cursor: pointer; font-weight: 600;
  }
  pre {
    background: var(--bg); border: 1px solid var(--border); border-radius: 6px;
    padding: 0.9rem 1rem; overflow-x: auto; font-size: 0.84rem;
    font-family: ui-monospace, "Cascadia Code", Consolas, monospace;
  }
  pre.error { color: var(--bad); }
  footer { color: var(--muted); font-size: 0.78rem; text-align: center; }
"""


def _render_doctor_section(lang: str) -> str:
    result = check_environment()
    modules_key = DIAGNOSTICS_FIELDS["modules"][lang]
    status_key = DIAGNOSTICS_FIELDS["status"][lang]
    issues_key = DIAGNOSTICS_FIELDS["issues"][lang]
    warnings_key = DIAGNOSTICS_FIELDS["warnings"][lang]

    rows = []
    for name, module in result[modules_key].items():
        issues = module[issues_key]
        ok = not issues
        pill_class = "ok" if ok else "bad"
        pill_text = "OK" if ok else module[status_key]
        issues_html = ""
        if issues:
            details = ", ".join(f"{html.escape(k)}: {html.escape(v)}" for k, v in issues.items())
            issues_html = f'<div class="issues">{details}</div>'
        rows.append(
            f"<tr><td>{html.escape(name)}</td>"
            f'<td><span class="pill {pill_class}">{html.escape(pill_text)}</span>'
            f"{issues_html}</td></tr>"
        )

    warnings = result[warnings_key]
    warnings_html = ""
    if warnings:
        items = "".join(f"<li>{html.escape(w)}</li>" for w in warnings)
        warnings_html = (
            f'<h2 style="margin-top:1.4rem">{UI_TEXT["warnings_heading"][lang]}</h2>'
            f'<ul class="warnings">{items}</ul>'
        )

    return (
        f"<section><h2>{UI_TEXT['config_heading'][lang]}</h2>"
        f"<table>{''.join(rows)}</table>{warnings_html}</section>"
    )


def _render_run_section(
    lang: str, selected: str = "triage", text: str = "", result_html: str = ""
) -> str:
    options = "".join(
        f'<option value="{html.escape(name)}"'
        f"{' selected' if name == selected else ''}>{html.escape(name)}</option>"
        for name in MODULE_NAMES
    )
    return f"""<section>
  <h2>{UI_TEXT["run_heading"][lang]}</h2>
  <form method="post" action="/run">
    <div>
      <label for="module">{UI_TEXT["module_label"][lang]}</label><br>
      <select name="module" id="module">{options}</select>
    </div>
    <div>
      <label for="text">{UI_TEXT["text_label"][lang]}</label><br>
      <textarea name="text" id="text">{html.escape(text)}</textarea>
    </div>
    <button type="submit">{UI_TEXT["submit_label"][lang]}</button>
  </form>
  {result_html}
</section>"""


def _render_page(lang: str, run_section: str) -> str:
    return f"""<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{UI_TEXT["title"][lang]}</title>
<style>{_STYLE}</style>
</head>
<body>
<main>
  <h1>{UI_TEXT["title"][lang]}</h1>
  {_render_doctor_section(lang)}
  {run_section}
  <footer>{UI_TEXT["footer_note"][lang]}</footer>
</main>
</body>
</html>"""


@app.get("/")
def index() -> ResponseReturnValue:
    lang = get_lang()
    return _render_page(lang, _render_run_section(lang))


@app.post("/run")
def run_module() -> ResponseReturnValue:
    lang = get_lang()
    module = request.form.get("module", "")
    text = request.form.get("text", "")

    handlers: dict[str, Callable[[str], dict]] = {
        "triage": triage,
        "veille": veille,
        "planification": planification,
        "resume": resume,
        "email": email_triage,
        "crm": crm,
        "agenda": agenda,
        "recherche": recherche,
        "facturation": facturation,
    }

    if module not in handlers:
        error_html = (
            f'<pre class="error">{html.escape(_UNKNOWN_MODULE_ERROR[lang].format(module=module))}'
            "</pre>"
        )
        run_section = _render_run_section(
            lang, selected="triage", text=text, result_html=error_html
        )
        return _render_page(lang, run_section), 400

    if not text.strip():
        error_html = f'<pre class="error">{html.escape(_MISSING_TEXT_ERROR[lang])}</pre>'
        run_section = _render_run_section(lang, selected=module, text=text, result_html=error_html)
        return _render_page(lang, run_section), 400

    try:
        result = handlers[module](text)
    except Exception as exc:
        error_message = f"{UI_TEXT['error_heading'][lang]}: {exc}"
        error_html = f'<pre class="error">{html.escape(error_message)}</pre>'
        run_section = _render_run_section(lang, selected=module, text=text, result_html=error_html)
        return _render_page(lang, run_section), 200

    notify_if_urgent(module, result)
    result_json = json.dumps(result, ensure_ascii=False, indent=2)
    result_html = (
        f'<h2 style="margin-top:1.4rem">{UI_TEXT["result_heading"][lang]}</h2>'
        f"<pre>{html.escape(result_json)}</pre>"
    )
    run_section = _render_run_section(lang, selected=module, text=text, result_html=result_html)
    return _render_page(lang, run_section)


def run(host: str = "127.0.0.1", port: int = 8001) -> None:
    from waitress import serve

    serve(app, host=host, port=port)

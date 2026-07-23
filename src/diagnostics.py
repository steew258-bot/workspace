import os

from dotenv import load_dotenv

from src.modules.email_client import REQUIRED_IMAP_VARS, REQUIRED_SMTP_VARS
from src.modules.recherche import REQUIRED_ENV_VARS as RECHERCHE_REQUIRED_VARS
from src.modules.whatsapp import REQUIRED_ENV_VARS as WHATSAPP_REQUIRED_VARS

load_dotenv()

ENV_EXAMPLE_PATH = ".env.example"

# Variables dont la valeur dans .env.example est un vrai defaut utilisable (URL/host
# standard), pas un placeholder a remplacer : on verifie juste qu'elles sont non vides,
# on ne les compare pas a l'exemple.
VARS_WITH_USABLE_DEFAULTS = {
    "WHATSAPP_API_URL",
    "EMAIL_IMAP_HOST",
    "EMAIL_IMAP_PORT",
    "EMAIL_SMTP_HOST",
    "EMAIL_SMTP_PORT",
    "EMAIL_MAILBOX",
}

MODULE_REQUIREMENTS = {
    "triage": ("ANTHROPIC_API_KEY",),
    "veille": ("ANTHROPIC_API_KEY",),
    "veille-feeds": ("ANTHROPIC_API_KEY",),
    "planification": ("ANTHROPIC_API_KEY",),
    "resume": ("ANTHROPIC_API_KEY",),
    "email": ("ANTHROPIC_API_KEY",),
    "crm": ("ANTHROPIC_API_KEY",),
    "email-check": ("ANTHROPIC_API_KEY", *REQUIRED_IMAP_VARS),
    "email-send": REQUIRED_SMTP_VARS,
    "recherche": RECHERCHE_REQUIRED_VARS,
    "whatsapp": WHATSAPP_REQUIRED_VARS,
    "webhook": ("WHATSAPP_VERIFY_TOKEN", *WHATSAPP_REQUIRED_VARS),
}


def _load_example_values(path: str = ENV_EXAMPLE_PATH) -> dict[str, str]:
    values = {}
    if not os.path.exists(path):
        return values

    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            values[key.strip()] = value.strip()
    return values


def _check_var(name: str, example_values: dict[str, str]) -> str | None:
    value = os.environ.get(name, "").strip()
    if not value:
        return "manquante"

    if name in VARS_WITH_USABLE_DEFAULTS:
        return None

    example = example_values.get(name, "").strip()
    if example and value == example:
        return "valeur d'exemple non remplacee"

    return None


def check() -> dict:
    example_values = _load_example_values()

    modules = {}
    for module_name, required_vars in MODULE_REQUIREMENTS.items():
        problemes = {}
        for var in required_vars:
            issue = _check_var(var, example_values)
            if issue:
                problemes[var] = issue
        modules[module_name] = {
            "statut": "ok" if not problemes else "incomplet",
            "problemes": problemes,
        }

    avertissements = []
    if _check_var("WHATSAPP_APP_SECRET", example_values) is not None:
        avertissements.append(
            "WHATSAPP_APP_SECRET non definie (ou encore a la valeur d'exemple, publique sur "
            "le repo) : la signature des webhooks entrants n'est pas verifiee, n'importe qui "
            "connaissant l'URL peut poster de faux messages."
        )
    if not os.environ.get("WHATSAPP_NOTIFY_TO", "").strip():
        avertissements.append(
            "WHATSAPP_NOTIFY_TO non definie : les notifications proactives sont desactivees."
        )

    return {"modules": modules, "avertissements": avertissements}

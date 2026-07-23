import os
from collections.abc import Callable

from dotenv import load_dotenv

from src.modules.calendar_client import REQUIRED_ENV_VARS as GOOGLE_REQUIRED_VARS
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


def _is_valid_email(value: str) -> bool:
    local, _, domain = value.partition("@")
    return bool(local) and "." in domain and not domain.startswith(".") and not domain.endswith(".")


def _is_valid_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def _is_valid_port(value: str) -> bool:
    return value.isdigit() and 0 < int(value) <= 65535


def _is_valid_e164_phone(value: str) -> bool:
    return value.startswith("+") and value[1:].isdigit() and len(value) >= 8


# Validateurs de format optionnels, appliques en plus des verifications
# "non vide" / "placeholder non remplace" : detecte une valeur non vide mais
# manifestement mal saisie (email sans @, port non numerique...).
FORMAT_VALIDATORS: dict[str, tuple[Callable[[str], bool], str]] = {
    "EMAIL_ADDRESS": (_is_valid_email, "doit ressembler a une adresse email (ex: toi@exemple.com)"),
    "WHATSAPP_API_URL": (_is_valid_url, "doit commencer par http:// ou https://"),
    "EMAIL_IMAP_PORT": (_is_valid_port, "doit etre un numero de port valide (1-65535)"),
    "EMAIL_SMTP_PORT": (_is_valid_port, "doit etre un numero de port valide (1-65535)"),
    "WHATSAPP_NOTIFY_TO": (_is_valid_e164_phone, "doit etre au format E.164 (ex: +33600000000)"),
}

MODULE_REQUIREMENTS = {
    "triage": ("ANTHROPIC_API_KEY",),
    "veille": ("ANTHROPIC_API_KEY",),
    "veille-feeds": ("ANTHROPIC_API_KEY",),
    "planification": ("ANTHROPIC_API_KEY",),
    "resume": ("ANTHROPIC_API_KEY",),
    "email": ("ANTHROPIC_API_KEY",),
    "crm": ("ANTHROPIC_API_KEY",),
    "agenda": ("ANTHROPIC_API_KEY",),
    "facturation": ("ANTHROPIC_API_KEY",),
    "agenda-check": ("ANTHROPIC_API_KEY", *GOOGLE_REQUIRED_VARS),
    "email-check": ("ANTHROPIC_API_KEY", *REQUIRED_IMAP_VARS),
    "email-send": REQUIRED_SMTP_VARS,
    "recherche": RECHERCHE_REQUIRED_VARS,
    "whatsapp": WHATSAPP_REQUIRED_VARS,
    "webhook": ("WHATSAPP_VERIFY_TOKEN", *WHATSAPP_REQUIRED_VARS),
}


def _load_example_values(path: str = ENV_EXAMPLE_PATH) -> dict[str, str]:
    values: dict[str, str] = {}
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

    if name not in VARS_WITH_USABLE_DEFAULTS:
        example = example_values.get(name, "").strip()
        if example and value == example:
            return "valeur d'exemple non remplacee"

    validator = FORMAT_VALIDATORS.get(name)
    if validator is not None and not validator[0](value):
        return f"format invalide : {validator[1]}"

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
    notify_to_issue = _check_var("WHATSAPP_NOTIFY_TO", example_values)
    if notify_to_issue == "manquante":
        avertissements.append(
            "WHATSAPP_NOTIFY_TO non definie : les notifications proactives sont desactivees."
        )
    elif notify_to_issue is not None:
        avertissements.append(f"WHATSAPP_NOTIFY_TO : {notify_to_issue}")

    avertissements.append(
        "facturation --export-xlsx, crm --export-xlsx et resume --export-docx utilisent les "
        "Agent Skills Anthropic (fonctionnalite beta) : chaque generation de fichier consomme "
        "du temps de conteneur d'execution de code, gratuit jusqu'a un quota mensuel puis "
        "facture par l'API Anthropic."
    )

    return {"modules": modules, "avertissements": avertissements}

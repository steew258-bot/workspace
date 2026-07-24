import os
from collections.abc import Callable

from dotenv import load_dotenv

from src.modules._client import get_lang
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

# Nom logique canonique -> nom de champ localise, pour les fichiers qui lisent
# la sortie de check() par nom de champ (app.py).
FIELDS = {
    "modules": {"fr": "modules", "en": "modules"},
    "status": {"fr": "statut", "en": "status"},
    "issues": {"fr": "problemes", "en": "issues"},
    "warnings": {"fr": "avertissements", "en": "warnings"},
}
STATUS_OK = {"fr": "ok", "en": "ok"}
STATUS_INCOMPLETE = {"fr": "incomplet", "en": "incomplete"}


def _is_valid_email(value: str) -> bool:
    local, _, domain = value.partition("@")
    return bool(local) and "." in domain and not domain.startswith(".") and not domain.endswith(".")


def _is_valid_url(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def _is_valid_port(value: str) -> bool:
    return value.isdigit() and 0 < int(value) <= 65535


def _is_valid_e164_phone(value: str) -> bool:
    return value.startswith("+") and value[1:].isdigit() and len(value) >= 8


def _is_valid_google_client_id(value: str) -> bool:
    suffix = ".apps.googleusercontent.com"
    if not value.endswith(suffix):
        return False
    project_number, _, rest = value[: -len(suffix)].partition("-")
    return bool(project_number) and project_number.isdigit() and bool(rest)


def _is_valid_google_client_secret(value: str) -> bool:
    prefix = "GOCSPX-"
    return value.startswith(prefix) and len(value) > len(prefix)


# Validateurs de format optionnels, appliques en plus des verifications
# "non vide" / "placeholder non remplace" : detecte une valeur non vide mais
# manifestement mal saisie (email sans @, port non numerique...).
FORMAT_VALIDATORS: dict[str, tuple[Callable[[str], bool], dict[str, str]]] = {
    "EMAIL_ADDRESS": (
        _is_valid_email,
        {
            "fr": "doit ressembler a une adresse email (ex: toi@exemple.com)",
            "en": "must look like an email address (e.g. you@example.com)",
        },
    ),
    "WHATSAPP_API_URL": (
        _is_valid_url,
        {
            "fr": "doit commencer par http:// ou https://",
            "en": "must start with http:// or https://",
        },
    ),
    "EMAIL_IMAP_PORT": (
        _is_valid_port,
        {
            "fr": "doit etre un numero de port valide (1-65535)",
            "en": "must be a valid port number (1-65535)",
        },
    ),
    "EMAIL_SMTP_PORT": (
        _is_valid_port,
        {
            "fr": "doit etre un numero de port valide (1-65535)",
            "en": "must be a valid port number (1-65535)",
        },
    ),
    "WHATSAPP_NOTIFY_TO": (
        _is_valid_e164_phone,
        {
            "fr": "doit etre au format E.164 (ex: +33600000000)",
            "en": "must be in E.164 format (e.g. +12025550123)",
        },
    ),
    "GOOGLE_CLIENT_ID": (
        _is_valid_google_client_id,
        {
            "fr": (
                "doit finir par .apps.googleusercontent.com avec un numero de projet devant "
                "(ex: 123456789-abc.apps.googleusercontent.com) - pas l'URI de redirection, "
                "pas l'ID d'un compte de service"
            ),
            "en": (
                "must end with .apps.googleusercontent.com with a project number in front "
                "(e.g. 123456789-abc.apps.googleusercontent.com) - not the redirect URI, "
                "not a service account ID"
            ),
        },
    ),
    "GOOGLE_CLIENT_SECRET": (
        _is_valid_google_client_secret,
        {
            "fr": (
                "doit commencer par GOCSPX- (le Client secret d'un vrai client OAuth, "
                "pas un ID de compte de service ni une URL)"
            ),
            "en": (
                "must start with GOCSPX- (the Client secret of a real OAuth client, "
                "not a service account ID or a URL)"
            ),
        },
    ),
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

_MISSING_MESSAGES = {"fr": "manquante", "en": "missing"}
_PLACEHOLDER_MESSAGES = {
    "fr": "valeur d'exemple non remplacee",
    "en": "example value not replaced",
}
_INVALID_FORMAT_MESSAGES = {
    "fr": "format invalide : {detail}",
    "en": "invalid format: {detail}",
}
_APP_SECRET_WARNING = {
    "fr": (
        "WHATSAPP_APP_SECRET non definie (ou encore a la valeur d'exemple, publique sur "
        "le repo) : la signature des webhooks entrants n'est pas verifiee, n'importe qui "
        "connaissant l'URL peut poster de faux messages."
    ),
    "en": (
        "WHATSAPP_APP_SECRET not set (or still at the example value, public on the "
        "repo): incoming webhook signatures aren't verified, anyone who knows the URL "
        "can post fake messages."
    ),
}
_NOTIFY_TO_MISSING_WARNING = {
    "fr": "WHATSAPP_NOTIFY_TO non definie : les notifications proactives sont desactivees.",
    "en": "WHATSAPP_NOTIFY_TO not set: proactive notifications are disabled.",
}
_NOTIFY_TO_ISSUE_WARNING = {
    "fr": "WHATSAPP_NOTIFY_TO : {issue}",
    "en": "WHATSAPP_NOTIFY_TO: {issue}",
}
_SKILLS_COST_WARNING = {
    "fr": (
        "facturation --export-xlsx, crm --export-xlsx et resume --export-docx utilisent les "
        "Agent Skills Anthropic (fonctionnalite beta) : chaque generation de fichier consomme "
        "du temps de conteneur d'execution de code, gratuit jusqu'a un quota mensuel puis "
        "facture par l'API Anthropic."
    ),
    "en": (
        "facturation --export-xlsx, crm --export-xlsx and resume --export-docx use "
        "Anthropic Agent Skills (beta feature): each file generation consumes code "
        "execution container time, free up to a monthly quota then billed by the "
        "Anthropic API."
    ),
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


def _check_var(name: str, example_values: dict[str, str], lang: str | None = None) -> str | None:
    lang = get_lang(lang)
    value = os.environ.get(name, "").strip()
    if not value:
        return _MISSING_MESSAGES[lang]

    if name not in VARS_WITH_USABLE_DEFAULTS:
        example = example_values.get(name, "").strip()
        if example and value == example:
            return _PLACEHOLDER_MESSAGES[lang]

    validator = FORMAT_VALIDATORS.get(name)
    if validator is not None and not validator[0](value):
        return _INVALID_FORMAT_MESSAGES[lang].format(detail=validator[1][lang])

    return None


def check(lang: str | None = None) -> dict:
    lang = get_lang(lang)
    example_values = _load_example_values()

    status_key = FIELDS["status"][lang]
    issues_key = FIELDS["issues"][lang]

    modules = {}
    for module_name, required_vars in MODULE_REQUIREMENTS.items():
        problemes = {}
        for var in required_vars:
            issue = _check_var(var, example_values, lang=lang)
            if issue:
                problemes[var] = issue
        modules[module_name] = {
            status_key: STATUS_OK[lang] if not problemes else STATUS_INCOMPLETE[lang],
            issues_key: problemes,
        }

    avertissements = []
    if _check_var("WHATSAPP_APP_SECRET", example_values, lang=lang) is not None:
        avertissements.append(_APP_SECRET_WARNING[lang])
    notify_to_issue = _check_var("WHATSAPP_NOTIFY_TO", example_values, lang=lang)
    if notify_to_issue == _MISSING_MESSAGES[lang]:
        avertissements.append(_NOTIFY_TO_MISSING_WARNING[lang])
    elif notify_to_issue is not None:
        avertissements.append(_NOTIFY_TO_ISSUE_WARNING[lang].format(issue=notify_to_issue))

    avertissements.append(_SKILLS_COST_WARNING[lang])

    return {FIELDS["modules"][lang]: modules, FIELDS["warnings"][lang]: avertissements}

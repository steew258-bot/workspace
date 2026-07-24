import anthropic

from src.modules._client import extract_text, get_client, get_lang, parse_json_object
from src.modules._skills import generate_file_with_skill

SYSTEM_PROMPTS = {
    "fr": """Tu es un assistant de suivi client (CRM). Analyse les notes d'echanges \
fournies (emails, appels, reunions...) avec un client ou prospect et reponds UNIQUEMENT avec \
un JSON valide, sans aucun texte autour, au format :
{
  "statut": "<statut court du dossier, ex: actif, a relancer, gagne, perdu>",
  "relance_a_faire": true|false,
  "action": "<prochaine action concrete a mener>",
  "risque_churn": "eleve|moyen|faible"
}""",
    "en": """You are a customer follow-up (CRM) assistant. Analyze the provided exchange \
notes (emails, calls, meetings...) with a client or prospect and reply ONLY with valid \
JSON, no surrounding text, in this format:
{
  "status": "<short status of the case, e.g. active, needs follow-up, won, lost>",
  "follow_up_needed": true|false,
  "action": "<next concrete action to take>",
  "churn_risk": "high|medium|low"
}""",
}

REQUIRED_KEYS = {
    "fr": {"statut", "relance_a_faire", "action", "risque_churn"},
    "en": {"status", "follow_up_needed", "action", "churn_risk"},
}
VALID_CHURN_RISK = {
    "fr": {"eleve", "moyen", "faible"},
    "en": {"high", "medium", "low"},
}

FIELDS = {
    "status": {"fr": "statut", "en": "status"},
    "follow_up_needed": {"fr": "relance_a_faire", "en": "follow_up_needed"},
    "action": {"fr": "action", "en": "action"},
    "churn_risk": {"fr": "risque_churn", "en": "churn_risk"},
}

MODEL = "claude-sonnet-5"

_INVALID_CHURN_RISK_MESSAGES = {
    "fr": "risque_churn invalide: {value!r}",
    "en": "Invalid churn_risk: {value!r}",
}
_INVALID_FOLLOW_UP_NEEDED_MESSAGES = {
    "fr": "relance_a_faire invalide: {value!r}",
    "en": "Invalid follow_up_needed: {value!r}",
}


class CrmError(ValueError):
    pass


def _parse_response(raw_text: str, lang: str | None = None) -> dict:
    lang = get_lang(lang)
    data = parse_json_object(raw_text, REQUIRED_KEYS[lang], CrmError, lang=lang)

    churn_risk_key = FIELDS["churn_risk"][lang]
    if data[churn_risk_key] not in VALID_CHURN_RISK[lang]:
        raise CrmError(_INVALID_CHURN_RISK_MESSAGES[lang].format(value=data[churn_risk_key]))

    follow_up_key = FIELDS["follow_up_needed"][lang]
    if not isinstance(data[follow_up_key], bool):
        raise CrmError(_INVALID_FOLLOW_UP_NEEDED_MESSAGES[lang].format(value=data[follow_up_key]))

    return data


def crm(text: str, client: anthropic.Anthropic | None = None, lang: str | None = None) -> dict:
    lang = get_lang(lang)
    client = client or get_client(lang=lang)
    response = client.messages.create(
        model=MODEL,
        max_tokens=500,
        system=SYSTEM_PROMPTS[lang],
        messages=[{"role": "user", "content": text}],
    )
    return _parse_response(extract_text(response, lang=lang), lang=lang)


_EXPORT_PROMPTS = {
    "fr": (
        "Cree une fiche de suivi client au format Excel (.xlsx), avec une ligne "
        "par champ (Statut, Relance a faire, Action, Risque de churn).\n"
        "Statut : {status}\n"
        "Relance a faire : {follow_up}\n"
        "Action : {action}\n"
        "Risque de churn : {churn_risk}"
    ),
    "en": (
        "Create a customer follow-up sheet in Excel format (.xlsx), with one row "
        "per field (Status, Follow-up needed, Action, Churn risk).\n"
        "Status: {status}\n"
        "Follow-up needed: {follow_up}\n"
        "Action: {action}\n"
        "Churn risk: {churn_risk}"
    ),
}
_YES_NO = {
    "fr": {True: "oui", False: "non"},
    "en": {True: "yes", False: "no"},
}


def crm_export_xlsx(
    data: dict,
    output_path: str,
    client: anthropic.Anthropic | None = None,
    lang: str | None = None,
) -> str:
    """Genere une vraie fiche de suivi client .xlsx a partir d'une analyse deja
    structuree par crm(). Fonctionnalite beta (Agent Skills), consomme du temps
    de conteneur d'execution de code : voir `python app.py doctor`."""
    lang = get_lang(lang)
    status_key = FIELDS["status"][lang]
    follow_up_key = FIELDS["follow_up_needed"][lang]
    action_key = FIELDS["action"][lang]
    churn_risk_key = FIELDS["churn_risk"][lang]

    prompt = _EXPORT_PROMPTS[lang].format(
        status=data[status_key],
        follow_up=_YES_NO[lang][data[follow_up_key]],
        action=data[action_key],
        churn_risk=data[churn_risk_key],
    )
    return generate_file_with_skill(prompt, "xlsx", output_path, client=client)

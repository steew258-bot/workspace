import anthropic

from src.modules._client import extract_text, get_client, get_lang, parse_json_object

SYSTEM_PROMPTS = {
    "fr": """Tu es un assistant de triage d'emails. Analyse l'email fourni (expediteur, \
objet et corps) et reponds UNIQUEMENT avec un JSON valide, sans aucun texte autour, au format :
{
  "urgence": "haute|moyenne|basse",
  "necessite_reponse": true|false,
  "action": "<action a entreprendre, courte>",
  "brouillon_reponse": "<brouillon de reponse, ou chaine vide si aucune reponse n'est requise>"
}""",
    "en": """You are an email triage assistant. Analyze the provided email (sender, \
subject and body) and reply ONLY with valid JSON, no surrounding text, in this format:
{
  "urgency": "high|medium|low",
  "requires_reply": true|false,
  "action": "<short action to take>",
  "reply_draft": "<draft reply, or an empty string if no reply is required>"
}""",
}

REQUIRED_KEYS = {
    "fr": {"urgence", "necessite_reponse", "action", "brouillon_reponse"},
    "en": {"urgency", "requires_reply", "action", "reply_draft"},
}
VALID_URGENCY = {
    "fr": {"haute", "moyenne", "basse"},
    "en": {"high", "medium", "low"},
}

FIELDS = {
    "action": {"fr": "action", "en": "action"},
    "urgency": {"fr": "urgence", "en": "urgency"},
    "requires_reply": {"fr": "necessite_reponse", "en": "requires_reply"},
    "reply_draft": {"fr": "brouillon_reponse", "en": "reply_draft"},
}

MODEL = "claude-sonnet-5"

_INVALID_URGENCY_MESSAGES = {
    "fr": "Urgence invalide: {value!r}",
    "en": "Invalid urgency: {value!r}",
}
_INVALID_REQUIRES_REPLY_MESSAGES = {
    "fr": "necessite_reponse invalide: {value!r}",
    "en": "Invalid requires_reply: {value!r}",
}


class EmailError(ValueError):
    pass


def _parse_response(raw_text: str, lang: str | None = None) -> dict:
    lang = get_lang(lang)
    data = parse_json_object(raw_text, REQUIRED_KEYS[lang], EmailError, lang=lang)

    urgency_key = FIELDS["urgency"][lang]
    if data[urgency_key] not in VALID_URGENCY[lang]:
        raise EmailError(_INVALID_URGENCY_MESSAGES[lang].format(value=data[urgency_key]))

    requires_reply_key = FIELDS["requires_reply"][lang]
    if not isinstance(data[requires_reply_key], bool):
        raise EmailError(
            _INVALID_REQUIRES_REPLY_MESSAGES[lang].format(value=data[requires_reply_key])
        )

    return data


def email(text: str, client: anthropic.Anthropic | None = None, lang: str | None = None) -> dict:
    lang = get_lang(lang)
    client = client or get_client(lang=lang)
    response = client.messages.create(
        model=MODEL,
        max_tokens=500,
        system=SYSTEM_PROMPTS[lang],
        messages=[{"role": "user", "content": text}],
    )
    return _parse_response(extract_text(response, lang=lang), lang=lang)

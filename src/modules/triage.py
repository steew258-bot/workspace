import anthropic

from src.modules._client import extract_text, get_client, get_lang, parse_json_object

SYSTEM_PROMPTS = {
    "fr": """Tu es un assistant de triage. Analyse le texte fourni (email, tache, \
notification...) et reponds UNIQUEMENT avec un JSON valide, sans aucun texte autour, au format :
{
  "action": "<action a entreprendre, courte>",
  "urgence": "haute|moyenne|basse",
  "brouillon_reponse": "<brouillon de reponse ou de suite a donner>"
}""",
    "en": """You are a triage assistant. Analyze the provided text (email, task, \
notification...) and reply ONLY with valid JSON, no surrounding text, in this format:
{
  "action": "<short action to take>",
  "urgency": "high|medium|low",
  "reply_draft": "<draft reply or next step>"
}""",
}

REQUIRED_KEYS = {
    "fr": {"action", "urgence", "brouillon_reponse"},
    "en": {"action", "urgency", "reply_draft"},
}
VALID_URGENCY = {
    "fr": {"haute", "moyenne", "basse"},
    "en": {"high", "medium", "low"},
}

# Nom logique canonique -> nom de champ localise, pour les fichiers qui lisent
# la sortie de ce module par nom de champ (notifications.py).
FIELDS = {
    "action": {"fr": "action", "en": "action"},
    "urgency": {"fr": "urgence", "en": "urgency"},
    "reply_draft": {"fr": "brouillon_reponse", "en": "reply_draft"},
}

MODEL = "claude-sonnet-5"

_INVALID_URGENCY_MESSAGES = {
    "fr": "Urgence invalide: {value!r}",
    "en": "Invalid urgency: {value!r}",
}


class TriageError(ValueError):
    pass


def _parse_response(raw_text: str, lang: str | None = None) -> dict:
    lang = get_lang(lang)
    data = parse_json_object(raw_text, REQUIRED_KEYS[lang], TriageError, lang=lang)

    urgency_key = FIELDS["urgency"][lang]
    if data[urgency_key] not in VALID_URGENCY[lang]:
        raise TriageError(_INVALID_URGENCY_MESSAGES[lang].format(value=data[urgency_key]))

    return data


def triage(text: str, client: anthropic.Anthropic | None = None, lang: str | None = None) -> dict:
    lang = get_lang(lang)
    client = client or get_client(lang=lang)
    response = client.messages.create(
        model=MODEL,
        max_tokens=500,
        system=SYSTEM_PROMPTS[lang],
        messages=[{"role": "user", "content": text}],
    )
    return _parse_response(extract_text(response, lang=lang), lang=lang)

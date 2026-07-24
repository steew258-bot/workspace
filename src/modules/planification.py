import anthropic

from src.modules._client import extract_text, get_client, get_lang, parse_json_object

SYSTEM_PROMPTS = {
    "fr": """Tu es un assistant de planification. Analyse la liste de taches et \
contraintes du jour fournie et reponds UNIQUEMENT avec un JSON valide, sans aucun texte \
autour, au format :
{
  "ordre": ["<tache 1>", "<tache 2>", ...],
  "tache_prioritaire": "<la tache a plus fort levier>",
  "justification": "<pourquoi>"
}""",
    "en": """You are a planning assistant. Analyze the provided list of today's tasks \
and constraints and reply ONLY with valid JSON, no surrounding text, in this format:
{
  "order": ["<task 1>", "<task 2>", ...],
  "priority_task": "<the highest-leverage task>",
  "justification": "<why>"
}""",
}

REQUIRED_KEYS = {
    "fr": {"ordre", "tache_prioritaire", "justification"},
    "en": {"order", "priority_task", "justification"},
}

FIELDS = {
    "order": {"fr": "ordre", "en": "order"},
}

MODEL = "claude-sonnet-5"

_INVALID_ORDER_MESSAGES = {
    "fr": "'ordre' doit etre une liste non vide",
    "en": "'order' must be a non-empty list",
}


class PlanificationError(ValueError):
    pass


def _parse_response(raw_text: str, lang: str | None = None) -> dict:
    lang = get_lang(lang)
    data = parse_json_object(raw_text, REQUIRED_KEYS[lang], PlanificationError, lang=lang)

    order_key = FIELDS["order"][lang]
    if not isinstance(data[order_key], list) or not data[order_key]:
        raise PlanificationError(_INVALID_ORDER_MESSAGES[lang])

    return data


def planification(
    text: str, client: anthropic.Anthropic | None = None, lang: str | None = None
) -> dict:
    lang = get_lang(lang)
    client = client or get_client(lang=lang)
    response = client.messages.create(
        model=MODEL,
        max_tokens=600,
        system=SYSTEM_PROMPTS[lang],
        messages=[{"role": "user", "content": text}],
    )
    return _parse_response(extract_text(response, lang=lang), lang=lang)

import anthropic

from src.modules._client import extract_text, get_client, get_lang, parse_json_object

SYSTEM_PROMPTS = {
    "fr": """Tu es un assistant d'agenda. Analyse la liste d'evenements et de \
contraintes du jour fournie et reponds UNIQUEMENT avec un JSON valide, sans aucun texte \
autour, au format :
{
  "conflits": [{"evenements": ["<evenement 1>", "<evenement 2>"], "raison": "<pourquoi ca \
coince>"}],
  "creneaux_libres": ["<creneau libre, ex: 14h-15h30>"],
  "suggestions": ["<suggestion de replanification>"]
}
Si aucun conflit, "conflits" est une liste vide.""",
    "en": """You are a calendar assistant. Analyze the provided list of today's events \
and constraints and reply ONLY with valid JSON, no surrounding text, in this format:
{
  "conflicts": [{"events": ["<event 1>", "<event 2>"], "reason": "<why it clashes>"}],
  "free_slots": ["<free slot, e.g. 2pm-3:30pm>"],
  "suggestions": ["<rescheduling suggestion>"]
}
If there is no conflict, "conflicts" is an empty list.""",
}

REQUIRED_KEYS = {
    "fr": {"conflits", "creneaux_libres", "suggestions"},
    "en": {"conflicts", "free_slots", "suggestions"},
}

FIELDS = {
    "conflicts": {"fr": "conflits", "en": "conflicts"},
    "free_slots": {"fr": "creneaux_libres", "en": "free_slots"},
    "suggestions": {"fr": "suggestions", "en": "suggestions"},
    "events": {"fr": "evenements", "en": "events"},
    "reason": {"fr": "raison", "en": "reason"},
}

MODEL = "claude-sonnet-5"

_INVALID_CONFLICTS_LIST_MESSAGES = {
    "fr": "'conflits' doit etre une liste",
    "en": "'conflicts' must be a list",
}
_INVALID_CONFLICT_ITEM_MESSAGES = {
    "fr": "Element 'conflits' invalide: {item!r}",
    "en": "Invalid 'conflicts' element: {item!r}",
}
_INVALID_FREE_SLOTS_MESSAGES = {
    "fr": "'creneaux_libres' doit etre une liste",
    "en": "'free_slots' must be a list",
}
_INVALID_SUGGESTIONS_MESSAGES = {
    "fr": "'suggestions' doit etre une liste",
    "en": "'suggestions' must be a list",
}


class AgendaError(ValueError):
    pass


def _parse_response(raw_text: str, lang: str | None = None) -> dict:
    lang = get_lang(lang)
    data = parse_json_object(raw_text, REQUIRED_KEYS[lang], AgendaError, lang=lang)

    conflicts_key = FIELDS["conflicts"][lang]
    if not isinstance(data[conflicts_key], list):
        raise AgendaError(_INVALID_CONFLICTS_LIST_MESSAGES[lang])

    events_key = FIELDS["events"][lang]
    reason_key = FIELDS["reason"][lang]
    for conflict in data[conflicts_key]:
        if not isinstance(conflict, dict) or {events_key, reason_key} - conflict.keys():
            raise AgendaError(_INVALID_CONFLICT_ITEM_MESSAGES[lang].format(item=conflict))

    free_slots_key = FIELDS["free_slots"][lang]
    if not isinstance(data[free_slots_key], list):
        raise AgendaError(_INVALID_FREE_SLOTS_MESSAGES[lang])

    suggestions_key = FIELDS["suggestions"][lang]
    if not isinstance(data[suggestions_key], list):
        raise AgendaError(_INVALID_SUGGESTIONS_MESSAGES[lang])

    return data


def agenda(text: str, client: anthropic.Anthropic | None = None, lang: str | None = None) -> dict:
    lang = get_lang(lang)
    client = client or get_client(lang=lang)
    response = client.messages.create(
        model=MODEL,
        max_tokens=700,
        system=SYSTEM_PROMPTS[lang],
        messages=[{"role": "user", "content": text}],
    )
    return _parse_response(extract_text(response, lang=lang), lang=lang)

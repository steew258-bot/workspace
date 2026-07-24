import anthropic

from src.modules._client import extract_text, get_client, get_lang, parse_json_object

SYSTEM_PROMPTS = {
    "fr": """Tu es un assistant de veille. Analyse la liste d'informations fournie \
(titres d'articles, alertes, annonces...) et reponds UNIQUEMENT avec un JSON valide, sans \
aucun texte autour, au format :
{
  "a_traiter": [{"titre": "<titre>", "raison": "<pourquoi c'est important>"}],
  "archive": ["<titre>", ...]
}
Ne mets dans "a_traiter" que les 1 a 3 elements les plus importants, le reste va dans "archive".""",
    "en": """You are a monitoring assistant. Analyze the provided list of information \
(article titles, alerts, announcements...) and reply ONLY with valid JSON, no surrounding \
text, in this format:
{
  "to_review": [{"title": "<title>", "reason": "<why it matters>"}],
  "archived": ["<title>", ...]
}
Only put the 1 to 3 most important items in "to_review", everything else goes in "archived".""",
}

REQUIRED_KEYS = {
    "fr": {"a_traiter", "archive"},
    "en": {"to_review", "archived"},
}

FIELDS = {
    "to_review": {"fr": "a_traiter", "en": "to_review"},
    "archived": {"fr": "archive", "en": "archived"},
    "title": {"fr": "titre", "en": "title"},
    "reason": {"fr": "raison", "en": "reason"},
}

MODEL = "claude-sonnet-5"

_INVALID_LISTS_MESSAGES = {
    "fr": "'a_traiter' et 'archive' doivent etre des listes",
    "en": "'to_review' and 'archived' must be lists",
}
_INVALID_ITEM_MESSAGES = {
    "fr": "Element 'a_traiter' invalide: {item!r}",
    "en": "Invalid 'to_review' element: {item!r}",
}


class VeilleError(ValueError):
    pass


def _parse_response(raw_text: str, lang: str | None = None) -> dict:
    lang = get_lang(lang)
    data = parse_json_object(raw_text, REQUIRED_KEYS[lang], VeilleError, lang=lang)

    to_review_key = FIELDS["to_review"][lang]
    archived_key = FIELDS["archived"][lang]
    if not isinstance(data[to_review_key], list) or not isinstance(data[archived_key], list):
        raise VeilleError(_INVALID_LISTS_MESSAGES[lang])

    title_key = FIELDS["title"][lang]
    reason_key = FIELDS["reason"][lang]
    for item in data[to_review_key]:
        if not isinstance(item, dict) or {title_key, reason_key} - item.keys():
            raise VeilleError(_INVALID_ITEM_MESSAGES[lang].format(item=item))

    return data


def veille(
    items_text: str, client: anthropic.Anthropic | None = None, lang: str | None = None
) -> dict:
    lang = get_lang(lang)
    client = client or get_client(lang=lang)
    response = client.messages.create(
        model=MODEL,
        max_tokens=800,
        system=SYSTEM_PROMPTS[lang],
        messages=[{"role": "user", "content": items_text}],
    )
    return _parse_response(extract_text(response, lang=lang), lang=lang)

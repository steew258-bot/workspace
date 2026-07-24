import anthropic

from src.modules._client import extract_text, get_client, get_lang, parse_json_object
from src.modules._skills import generate_file_with_skill

SYSTEM_PROMPTS = {
    "fr": """Tu es un assistant de facturation. Analyse la description de prestation \
fournie et reponds UNIQUEMENT avec un JSON valide, sans aucun texte autour, au format :
{
  "client": "<nom du client si mentionne, sinon chaine vide>",
  "lignes": [{"designation": "<description precise de la prestation ou du produit>", \
"quantite": <nombre>, "prix_unitaire": <nombre ou null si non precise dans le texte>}],
  "total_estime": <nombre ou null si au moins un prix_unitaire est null>,
  "notes": "<hypotheses faites, informations manquantes a completer avant envoi>"
}
N'invente jamais de prix : si un prix n'est pas donne dans le texte, mets prix_unitaire (et \
donc total_estime) a null et signale-le dans "notes".""",
    "en": """You are a billing assistant. Analyze the provided service description and \
reply ONLY with valid JSON, no surrounding text, in this format:
{
  "client": "<client name if mentioned, otherwise an empty string>",
  "line_items": [{"description": "<precise description of the service or product>", \
"quantity": <number>, "unit_price": <number or null if not specified in the text>}],
  "estimated_total": <number or null if at least one unit_price is null>,
  "notes": "<assumptions made, missing information to fill in before sending>"
}
Never invent a price: if a price isn't given in the text, set unit_price (and therefore \
estimated_total) to null and flag it in "notes".""",
}

REQUIRED_KEYS = {
    "fr": {"client", "lignes", "total_estime", "notes"},
    "en": {"client", "line_items", "estimated_total", "notes"},
}
REQUIRED_LINE_ITEM_KEYS = {
    "fr": {"designation", "quantite", "prix_unitaire"},
    "en": {"description", "quantity", "unit_price"},
}

FIELDS = {
    "client": {"fr": "client", "en": "client"},
    "line_items": {"fr": "lignes", "en": "line_items"},
    "estimated_total": {"fr": "total_estime", "en": "estimated_total"},
    "notes": {"fr": "notes", "en": "notes"},
    "description": {"fr": "designation", "en": "description"},
    "quantity": {"fr": "quantite", "en": "quantity"},
    "unit_price": {"fr": "prix_unitaire", "en": "unit_price"},
}

MODEL = "claude-sonnet-5"

_INVALID_LINE_ITEMS_MESSAGES = {
    "fr": "'lignes' doit etre une liste non vide",
    "en": "'line_items' must be a non-empty list",
}
_INVALID_LINE_ITEM_MESSAGES = {
    "fr": "Element 'lignes' invalide: {item!r}",
    "en": "Invalid 'line_items' element: {item!r}",
}
_INVALID_QUANTITY_MESSAGES = {
    "fr": "'quantite' invalide: {value!r}",
    "en": "Invalid 'quantity': {value!r}",
}
_INVALID_UNIT_PRICE_MESSAGES = {
    "fr": "'prix_unitaire' invalide: {value!r}",
    "en": "Invalid 'unit_price': {value!r}",
}
_INVALID_ESTIMATED_TOTAL_MESSAGES = {
    "fr": "'total_estime' invalide: {value!r}",
    "en": "Invalid 'estimated_total': {value!r}",
}


class FacturationError(ValueError):
    pass


def _is_number_or_none(value) -> bool:
    return value is None or (isinstance(value, (int, float)) and not isinstance(value, bool))


def _parse_response(raw_text: str, lang: str | None = None) -> dict:
    lang = get_lang(lang)
    data = parse_json_object(raw_text, REQUIRED_KEYS[lang], FacturationError, lang=lang)

    line_items_key = FIELDS["line_items"][lang]
    if not isinstance(data[line_items_key], list) or not data[line_items_key]:
        raise FacturationError(_INVALID_LINE_ITEMS_MESSAGES[lang])

    quantity_key = FIELDS["quantity"][lang]
    unit_price_key = FIELDS["unit_price"][lang]
    for item in data[line_items_key]:
        if not isinstance(item, dict) or REQUIRED_LINE_ITEM_KEYS[lang] - item.keys():
            raise FacturationError(_INVALID_LINE_ITEM_MESSAGES[lang].format(item=item))
        if not _is_number_or_none(item[quantity_key]):
            raise FacturationError(
                _INVALID_QUANTITY_MESSAGES[lang].format(value=item[quantity_key])
            )
        if not _is_number_or_none(item[unit_price_key]):
            raise FacturationError(
                _INVALID_UNIT_PRICE_MESSAGES[lang].format(value=item[unit_price_key])
            )

    estimated_total_key = FIELDS["estimated_total"][lang]
    if not _is_number_or_none(data[estimated_total_key]):
        raise FacturationError(
            _INVALID_ESTIMATED_TOTAL_MESSAGES[lang].format(value=data[estimated_total_key])
        )

    return data


def facturation(
    text: str, client: anthropic.Anthropic | None = None, lang: str | None = None
) -> dict:
    lang = get_lang(lang)
    client = client or get_client(lang=lang)
    response = client.messages.create(
        model=MODEL,
        max_tokens=700,
        system=SYSTEM_PROMPTS[lang],
        messages=[{"role": "user", "content": text}],
    )
    return _parse_response(extract_text(response, lang=lang), lang=lang)


_EXPORT_PROMPTS = {
    "fr": (
        "Cree un devis au format Excel (.xlsx), avec un tableau (designation, quantite, "
        "prix unitaire, total par ligne) et un total general en bas.\n"
        "Client : {client}\n"
        "Lignes :\n{lines_text}\n"
        "Notes : {notes}"
    ),
    "en": (
        "Create a quote in Excel format (.xlsx), with a table (description, quantity, "
        "unit price, line total) and a grand total at the bottom.\n"
        "Client: {client}\n"
        "Line items:\n{lines_text}\n"
        "Notes: {notes}"
    ),
}
_UNSPECIFIED_CLIENT = {"fr": "non precise", "en": "unspecified"}
_NO_NOTES = {"fr": "aucune", "en": "none"}
_PRICE_TO_DEFINE = {"fr": " (prix a definir)", "en": " (price to be defined)"}
_UNIT_PRICE_SUFFIX = {"fr": " a {price} EUR l'unite", "en": " at {price} EUR per unit"}


def facturation_export_xlsx(
    data: dict,
    output_path: str,
    client: anthropic.Anthropic | None = None,
    lang: str | None = None,
) -> str:
    """Genere un vrai fichier .xlsx pour un devis deja structure par facturation().
    Fonctionnalite beta (Agent Skills), consomme du temps de conteneur d'execution
    de code : voir `python app.py doctor`."""
    lang = get_lang(lang)
    client_key = FIELDS["client"][lang]
    line_items_key = FIELDS["line_items"][lang]
    notes_key = FIELDS["notes"][lang]
    description_key = FIELDS["description"][lang]
    quantity_key = FIELDS["quantity"][lang]
    unit_price_key = FIELDS["unit_price"][lang]

    lines_text = "\n".join(
        f"- {item[description_key]} x{item[quantity_key]}"
        + (
            _UNIT_PRICE_SUFFIX[lang].format(price=item[unit_price_key])
            if item[unit_price_key] is not None
            else _PRICE_TO_DEFINE[lang]
        )
        for item in data[line_items_key]
    )
    prompt = _EXPORT_PROMPTS[lang].format(
        client=data[client_key] or _UNSPECIFIED_CLIENT[lang],
        lines_text=lines_text,
        notes=data[notes_key] or _NO_NOTES[lang],
    )
    return generate_file_with_skill(prompt, "xlsx", output_path, client=client)

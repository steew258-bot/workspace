import json
import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

DEFAULT_LANG = "fr"


def get_lang(lang: str | None = None) -> str:
    """Resout la langue effective : l'argument explicite si fourni, sinon
    OPS_AGENT_LANG, sinon DEFAULT_LANG. Lu a chaque appel (jamais mis en cache
    a l'import) pour que les tests puissent monkeypatcher la variable d'env."""
    return lang or os.environ.get("OPS_AGENT_LANG", DEFAULT_LANG)


class MissingApiKeyError(RuntimeError):
    pass


_MISSING_API_KEY_MESSAGES = {
    "fr": (
        "ANTHROPIC_API_KEY manquante. Copie .env.example en .env et renseigne ta cle, "
        "ou exporte la variable d'environnement directement."
    ),
    "en": (
        "ANTHROPIC_API_KEY is missing. Copy .env.example to .env and fill in your key, "
        "or export the environment variable directly."
    ),
}


def get_client(lang: str | None = None) -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise MissingApiKeyError(_MISSING_API_KEY_MESSAGES[get_lang(lang)])
    return anthropic.Anthropic(api_key=api_key)


_UNEXPECTED_RESPONSE_MESSAGES = {
    "fr": "Reponse Anthropic inattendue (pas de bloc texte): {block!r}",
    "en": "Unexpected Anthropic response (no text block): {block!r}",
}


def extract_text(response: anthropic.types.Message, lang: str | None = None) -> str:
    block = response.content[0]
    if not isinstance(block, anthropic.types.TextBlock):
        raise TypeError(_UNEXPECTED_RESPONSE_MESSAGES[get_lang(lang)].format(block=block))
    return block.text


_GENERIC_PARSE_MESSAGES = {
    "fr": {
        "not_json": "Reponse non JSON: {raw!r}",
        "not_object": "Reponse JSON invalide, objet attendu: {raw!r}",
        "missing_keys": "Champs manquants dans la reponse: {missing}",
    },
    "en": {
        "not_json": "Response is not JSON: {raw!r}",
        "not_object": "Invalid JSON response, expected an object: {raw!r}",
        "missing_keys": "Missing fields in response: {missing}",
    },
}


def parse_json_object(
    raw_text: str,
    required_keys: set[str],
    error_cls: type[Exception],
    lang: str | None = None,
) -> dict:
    """Parse le JSON strict attendu de chaque module : un objet contenant au moins
    required_keys. Leve error_cls (le <Nom>Error propre au module appelant) sur
    JSON invalide, non-objet, ou champ manquant. La validation specifique a chaque
    module continue apres cet appel."""
    messages = _GENERIC_PARSE_MESSAGES[get_lang(lang)]
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise error_cls(messages["not_json"].format(raw=raw_text)) from exc

    if not isinstance(data, dict):
        raise error_cls(messages["not_object"].format(raw=raw_text))

    missing = required_keys - data.keys()
    if missing:
        raise error_cls(messages["missing_keys"].format(missing=missing))

    return data

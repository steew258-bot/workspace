import json
import os
import urllib.error
import urllib.request

from dotenv import load_dotenv

from src.modules._client import get_lang

load_dotenv()

API_URL = "https://api.perplexity.ai/chat/completions"
MODEL = "sonar"
REQUEST_TIMEOUT_SECONDS = 30

REQUIRED_ENV_VARS = ("PERPLEXITY_API_KEY",)

FIELDS = {
    "response": {"fr": "reponse", "en": "response"},
    "sources": {"fr": "sources", "en": "sources"},
}

_MISSING_API_KEY_MESSAGES = {
    "fr": (
        "PERPLEXITY_API_KEY manquante. Copie .env.example en .env et renseigne ta cle "
        "(perplexity.ai/settings/api)."
    ),
    "en": (
        "PERPLEXITY_API_KEY missing. Copy .env.example to .env and set your key "
        "(perplexity.ai/settings/api)."
    ),
}
_INVALID_RESPONSE_OBJECT_MESSAGES = {
    "fr": "Reponse Perplexity invalide, objet attendu: {data!r}",
    "en": "Invalid Perplexity response, expected an object: {data!r}",
}
_MISSING_CHOICES_MESSAGES = {
    "fr": "Reponse Perplexity sans 'choices': {data!r}",
    "en": "Perplexity response missing 'choices': {data!r}",
}
_NO_USABLE_CONTENT_MESSAGES = {
    "fr": "Reponse Perplexity sans contenu exploitable: {data!r}",
    "en": "Perplexity response has no usable content: {data!r}",
}
_HTTP_ERROR_MESSAGES = {
    "fr": "Echec de la recherche Perplexity ({code}): {detail}",
    "en": "Perplexity search failed ({code}): {detail}",
}
_URL_ERROR_MESSAGES = {
    "fr": "Echec de la recherche Perplexity: {reason}",
    "en": "Perplexity search failed: {reason}",
}
_NON_JSON_RESPONSE_MESSAGES = {
    "fr": "Reponse Perplexity non JSON: {body!r}",
    "en": "Non-JSON Perplexity response: {body!r}",
}


class RechercheError(RuntimeError):
    pass


def _get_api_key(lang: str | None = None) -> str:
    lang = get_lang(lang)
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        raise RechercheError(_MISSING_API_KEY_MESSAGES[lang])
    return api_key


def _parse_response(data: dict, lang: str | None = None) -> dict:
    lang = get_lang(lang)
    if not isinstance(data, dict):
        raise RechercheError(_INVALID_RESPONSE_OBJECT_MESSAGES[lang].format(data=data))

    choices = data.get("choices")
    if not choices or not isinstance(choices, list) or not isinstance(choices[0], dict):
        raise RechercheError(_MISSING_CHOICES_MESSAGES[lang].format(data=data))

    message = choices[0].get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if not content or not isinstance(content, str):
        raise RechercheError(_NO_USABLE_CONTENT_MESSAGES[lang].format(data=data))

    sources = data.get("citations", [])
    if not isinstance(sources, list):
        sources = []

    return {FIELDS["response"][lang]: content.strip(), FIELDS["sources"][lang]: sources}


def recherche(question: str, lang: str | None = None) -> dict:
    lang = get_lang(lang)
    api_key = _get_api_key(lang=lang)

    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": question}],
    }
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RechercheError(
            _HTTP_ERROR_MESSAGES[lang].format(code=exc.code, detail=detail)
        ) from exc
    except urllib.error.URLError as exc:
        raise RechercheError(_URL_ERROR_MESSAGES[lang].format(reason=exc.reason)) from exc

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RechercheError(_NON_JSON_RESPONSE_MESSAGES[lang].format(body=body)) from exc

    return _parse_response(data, lang=lang)

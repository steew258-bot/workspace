import json
import os
import urllib.error
import urllib.request

from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.perplexity.ai/chat/completions"
MODEL = "sonar"
REQUEST_TIMEOUT_SECONDS = 30

REQUIRED_ENV_VARS = ("PERPLEXITY_API_KEY",)


class RechercheError(RuntimeError):
    pass


def _get_api_key() -> str:
    api_key = os.environ.get("PERPLEXITY_API_KEY")
    if not api_key:
        raise RechercheError(
            "PERPLEXITY_API_KEY manquante. Copie .env.example en .env et renseigne ta cle "
            "(perplexity.ai/settings/api)."
        )
    return api_key


def _parse_response(data: dict) -> dict:
    if not isinstance(data, dict):
        raise RechercheError(f"Reponse Perplexity invalide, objet attendu: {data!r}")

    choices = data.get("choices")
    if not choices or not isinstance(choices, list) or not isinstance(choices[0], dict):
        raise RechercheError(f"Reponse Perplexity sans 'choices': {data!r}")

    message = choices[0].get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if not content or not isinstance(content, str):
        raise RechercheError(f"Reponse Perplexity sans contenu exploitable: {data!r}")

    sources = data.get("citations", [])
    if not isinstance(sources, list):
        sources = []

    return {"reponse": content.strip(), "sources": sources}


def recherche(question: str) -> dict:
    api_key = _get_api_key()

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
        raise RechercheError(f"Echec de la recherche Perplexity ({exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise RechercheError(f"Echec de la recherche Perplexity: {exc.reason}") from exc

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RechercheError(f"Reponse Perplexity non JSON: {body!r}") from exc

    return _parse_response(data)

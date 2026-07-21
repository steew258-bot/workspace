import json

import anthropic

from src.modules._client import get_client

SYSTEM_PROMPT = """Tu es un assistant de synthese. Analyse le texte long fourni (compte-rendu, \
document, fil d'emails...) et reponds UNIQUEMENT avec un JSON valide, sans aucun texte autour, \
au format :
{
  "resume": "<resume en 2 a 4 phrases>",
  "points_cles": ["<point cle 1>", "<point cle 2>", ...]
}"""

REQUIRED_KEYS = {"resume", "points_cles"}

MODEL = "claude-sonnet-5"


class ResumeError(ValueError):
    pass


def _parse_response(raw_text: str) -> dict:
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ResumeError(f"Reponse non JSON: {raw_text!r}") from exc

    missing = REQUIRED_KEYS - data.keys()
    if missing:
        raise ResumeError(f"Champs manquants dans la reponse: {missing}")

    if not isinstance(data["resume"], str) or not data["resume"].strip():
        raise ResumeError("'resume' doit etre une chaine non vide")

    if not isinstance(data["points_cles"], list) or not data["points_cles"]:
        raise ResumeError("'points_cles' doit etre une liste non vide")

    return data


def resume(text: str, client: anthropic.Anthropic | None = None) -> dict:
    client = client or get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
    )
    return _parse_response(response.content[0].text)

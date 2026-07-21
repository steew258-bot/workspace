import json

import anthropic

from src.modules._client import get_client

SYSTEM_PROMPT = """Tu es un assistant de triage. Analyse le texte fourni (email, tache, \
notification...) et reponds UNIQUEMENT avec un JSON valide, sans aucun texte autour, au format :
{
  "action": "<action a entreprendre, courte>",
  "urgence": "haute|moyenne|basse",
  "brouillon_reponse": "<brouillon de reponse ou de suite a donner>"
}"""

REQUIRED_KEYS = {"action", "urgence", "brouillon_reponse"}
VALID_URGENCE = {"haute", "moyenne", "basse"}

MODEL = "claude-sonnet-5"


class TriageError(ValueError):
    pass


def _parse_response(raw_text: str) -> dict:
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise TriageError(f"Reponse non JSON: {raw_text!r}") from exc

    missing = REQUIRED_KEYS - data.keys()
    if missing:
        raise TriageError(f"Champs manquants dans la reponse: {missing}")

    if data["urgence"] not in VALID_URGENCE:
        raise TriageError(f"Urgence invalide: {data['urgence']!r}")

    return data


def triage(text: str, client: anthropic.Anthropic | None = None) -> dict:
    client = client or get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
    )
    return _parse_response(response.content[0].text)

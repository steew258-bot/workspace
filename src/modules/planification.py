import json

import anthropic

from src.modules._client import get_client

SYSTEM_PROMPT = """Tu es un assistant de planification. Analyse la liste de taches et \
contraintes du jour fournie et reponds UNIQUEMENT avec un JSON valide, sans aucun texte \
autour, au format :
{
  "ordre": ["<tache 1>", "<tache 2>", ...],
  "tache_prioritaire": "<la tache a plus fort levier>",
  "justification": "<pourquoi>"
}"""

REQUIRED_KEYS = {"ordre", "tache_prioritaire", "justification"}

MODEL = "claude-sonnet-5"


class PlanificationError(ValueError):
    pass


def _parse_response(raw_text: str) -> dict:
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise PlanificationError(f"Reponse non JSON: {raw_text!r}") from exc

    if not isinstance(data, dict):
        raise PlanificationError(f"Reponse JSON invalide, objet attendu: {raw_text!r}")

    missing = REQUIRED_KEYS - data.keys()
    if missing:
        raise PlanificationError(f"Champs manquants dans la reponse: {missing}")

    if not isinstance(data["ordre"], list) or not data["ordre"]:
        raise PlanificationError("'ordre' doit etre une liste non vide")

    return data


def planification(text: str, client: anthropic.Anthropic | None = None) -> dict:
    client = client or get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=600,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
    )
    return _parse_response(response.content[0].text)

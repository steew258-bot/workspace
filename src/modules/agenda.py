import json

import anthropic

from src.modules._client import get_client

SYSTEM_PROMPT = """Tu es un assistant d'agenda. Analyse la liste d'evenements et de \
contraintes du jour fournie et reponds UNIQUEMENT avec un JSON valide, sans aucun texte \
autour, au format :
{
  "conflits": [{"evenements": ["<evenement 1>", "<evenement 2>"], "raison": "<pourquoi ca \
coince>"}],
  "creneaux_libres": ["<creneau libre, ex: 14h-15h30>"],
  "suggestions": ["<suggestion de replanification>"]
}
Si aucun conflit, "conflits" est une liste vide."""

REQUIRED_KEYS = {"conflits", "creneaux_libres", "suggestions"}

MODEL = "claude-sonnet-5"


class AgendaError(ValueError):
    pass


def _parse_response(raw_text: str) -> dict:
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise AgendaError(f"Reponse non JSON: {raw_text!r}") from exc

    if not isinstance(data, dict):
        raise AgendaError(f"Reponse JSON invalide, objet attendu: {raw_text!r}")

    missing = REQUIRED_KEYS - data.keys()
    if missing:
        raise AgendaError(f"Champs manquants dans la reponse: {missing}")

    if not isinstance(data["conflits"], list):
        raise AgendaError("'conflits' doit etre une liste")

    for conflit in data["conflits"]:
        if not isinstance(conflit, dict) or {"evenements", "raison"} - conflit.keys():
            raise AgendaError(f"Element 'conflits' invalide: {conflit!r}")

    if not isinstance(data["creneaux_libres"], list):
        raise AgendaError("'creneaux_libres' doit etre une liste")

    if not isinstance(data["suggestions"], list):
        raise AgendaError("'suggestions' doit etre une liste")

    return data


def agenda(text: str, client: anthropic.Anthropic | None = None) -> dict:
    client = client or get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=700,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
    )
    return _parse_response(response.content[0].text)

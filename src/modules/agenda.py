import anthropic

from src.modules._client import extract_text, get_client, parse_json_object

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
    data = parse_json_object(raw_text, REQUIRED_KEYS, AgendaError)

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
    return _parse_response(extract_text(response))

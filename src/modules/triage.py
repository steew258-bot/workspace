import anthropic

from src.modules._client import extract_text, get_client, parse_json_object

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
    data = parse_json_object(raw_text, REQUIRED_KEYS, TriageError)

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
    return _parse_response(extract_text(response))

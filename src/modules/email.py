import anthropic

from src.modules._client import extract_text, get_client, parse_json_object

SYSTEM_PROMPT = """Tu es un assistant de triage d'emails. Analyse l'email fourni (expediteur, \
objet et corps) et reponds UNIQUEMENT avec un JSON valide, sans aucun texte autour, au format :
{
  "urgence": "haute|moyenne|basse",
  "necessite_reponse": true|false,
  "action": "<action a entreprendre, courte>",
  "brouillon_reponse": "<brouillon de reponse, ou chaine vide si aucune reponse n'est requise>"
}"""

REQUIRED_KEYS = {"urgence", "necessite_reponse", "action", "brouillon_reponse"}
VALID_URGENCE = {"haute", "moyenne", "basse"}

MODEL = "claude-sonnet-5"


class EmailError(ValueError):
    pass


def _parse_response(raw_text: str) -> dict:
    data = parse_json_object(raw_text, REQUIRED_KEYS, EmailError)

    if data["urgence"] not in VALID_URGENCE:
        raise EmailError(f"Urgence invalide: {data['urgence']!r}")

    if not isinstance(data["necessite_reponse"], bool):
        raise EmailError(f"necessite_reponse invalide: {data['necessite_reponse']!r}")

    return data


def email(text: str, client: anthropic.Anthropic | None = None) -> dict:
    client = client or get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
    )
    return _parse_response(extract_text(response))

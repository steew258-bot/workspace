import json

import anthropic

from src.modules._client import extract_text, get_client

SYSTEM_PROMPT = """Tu es un assistant de veille. Analyse la liste d'informations fournie \
(titres d'articles, alertes, annonces...) et reponds UNIQUEMENT avec un JSON valide, sans \
aucun texte autour, au format :
{
  "a_traiter": [{"titre": "<titre>", "raison": "<pourquoi c'est important>"}],
  "archive": ["<titre>", ...]
}
Ne mets dans "a_traiter" que les 1 a 3 elements les plus importants, le reste va dans "archive"."""

REQUIRED_KEYS = {"a_traiter", "archive"}

MODEL = "claude-sonnet-5"


class VeilleError(ValueError):
    pass


def _parse_response(raw_text: str) -> dict:
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise VeilleError(f"Reponse non JSON: {raw_text!r}") from exc

    if not isinstance(data, dict):
        raise VeilleError(f"Reponse JSON invalide, objet attendu: {raw_text!r}")

    missing = REQUIRED_KEYS - data.keys()
    if missing:
        raise VeilleError(f"Champs manquants dans la reponse: {missing}")

    if not isinstance(data["a_traiter"], list) or not isinstance(data["archive"], list):
        raise VeilleError("'a_traiter' et 'archive' doivent etre des listes")

    for item in data["a_traiter"]:
        if not isinstance(item, dict) or {"titre", "raison"} - item.keys():
            raise VeilleError(f"Element 'a_traiter' invalide: {item!r}")

    return data


def veille(items_text: str, client: anthropic.Anthropic | None = None) -> dict:
    client = client or get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=800,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": items_text}],
    )
    return _parse_response(extract_text(response))

import json

import anthropic

from src.modules._client import get_client

SYSTEM_PROMPT = """Tu es un assistant de suivi client (CRM). Analyse les notes d'echanges \
fournies (emails, appels, reunions...) avec un client ou prospect et reponds UNIQUEMENT avec \
un JSON valide, sans aucun texte autour, au format :
{
  "statut": "<statut court du dossier, ex: actif, a relancer, gagne, perdu>",
  "relance_a_faire": true|false,
  "action": "<prochaine action concrete a mener>",
  "risque_churn": "eleve|moyen|faible"
}"""

REQUIRED_KEYS = {"statut", "relance_a_faire", "action", "risque_churn"}
VALID_RISQUE_CHURN = {"eleve", "moyen", "faible"}

MODEL = "claude-sonnet-5"


class CrmError(ValueError):
    pass


def _parse_response(raw_text: str) -> dict:
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise CrmError(f"Reponse non JSON: {raw_text!r}") from exc

    if not isinstance(data, dict):
        raise CrmError(f"Reponse JSON invalide, objet attendu: {raw_text!r}")

    missing = REQUIRED_KEYS - data.keys()
    if missing:
        raise CrmError(f"Champs manquants dans la reponse: {missing}")

    if data["risque_churn"] not in VALID_RISQUE_CHURN:
        raise CrmError(f"risque_churn invalide: {data['risque_churn']!r}")

    if not isinstance(data["relance_a_faire"], bool):
        raise CrmError(f"relance_a_faire invalide: {data['relance_a_faire']!r}")

    return data


def crm(text: str, client: anthropic.Anthropic | None = None) -> dict:
    client = client or get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=500,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
    )
    return _parse_response(response.content[0].text)

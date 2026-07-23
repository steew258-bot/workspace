import anthropic

from src.modules._client import extract_text, get_client, parse_json_object
from src.modules._skills import generate_file_with_skill

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
    data = parse_json_object(raw_text, REQUIRED_KEYS, CrmError)

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
    return _parse_response(extract_text(response))


def crm_export_xlsx(
    data: dict, output_path: str, client: anthropic.Anthropic | None = None
) -> str:
    """Genere une vraie fiche de suivi client .xlsx a partir d'une analyse deja
    structuree par crm(). Fonctionnalite beta (Agent Skills), consomme du temps
    de conteneur d'execution de code : voir `python app.py doctor`."""
    prompt = (
        "Cree une fiche de suivi client au format Excel (.xlsx), avec une ligne "
        "par champ (Statut, Relance a faire, Action, Risque de churn).\n"
        f"Statut : {data['statut']}\n"
        f"Relance a faire : {'oui' if data['relance_a_faire'] else 'non'}\n"
        f"Action : {data['action']}\n"
        f"Risque de churn : {data['risque_churn']}"
    )
    return generate_file_with_skill(prompt, "xlsx", output_path, client=client)

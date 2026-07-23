import json

import anthropic

from src.modules._client import extract_text, get_client
from src.modules._skills import generate_file_with_skill

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

    if not isinstance(data, dict):
        raise ResumeError(f"Reponse JSON invalide, objet attendu: {raw_text!r}")

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
    return _parse_response(extract_text(response))


def resume_export_docx(
    data: dict, output_path: str, client: anthropic.Anthropic | None = None
) -> str:
    """Genere un vrai rapport .docx a partir d'un resume deja structure par
    resume(). Fonctionnalite beta (Agent Skills), consomme du temps de
    conteneur d'execution de code : voir `python app.py doctor`."""
    points_text = "\n".join(f"- {point}" for point in data["points_cles"])
    prompt = (
        "Cree un document Word (.docx) avec un titre, un paragraphe de resume, "
        "puis une liste a puces des points cles.\n"
        f"Resume : {data['resume']}\n"
        f"Points cles :\n{points_text}"
    )
    return generate_file_with_skill(prompt, "docx", output_path, client=client)

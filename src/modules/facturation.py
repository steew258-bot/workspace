import anthropic

from src.modules._client import extract_text, get_client, parse_json_object
from src.modules._skills import generate_file_with_skill

SYSTEM_PROMPT = """Tu es un assistant de facturation. Analyse la description de prestation \
fournie et reponds UNIQUEMENT avec un JSON valide, sans aucun texte autour, au format :
{
  "client": "<nom du client si mentionne, sinon chaine vide>",
  "lignes": [{"designation": "<description precise de la prestation ou du produit>", \
"quantite": <nombre>, "prix_unitaire": <nombre ou null si non precise dans le texte>}],
  "total_estime": <nombre ou null si au moins un prix_unitaire est null>,
  "notes": "<hypotheses faites, informations manquantes a completer avant envoi>"
}
N'invente jamais de prix : si un prix n'est pas donne dans le texte, mets prix_unitaire (et \
donc total_estime) a null et signale-le dans "notes"."""

REQUIRED_KEYS = {"client", "lignes", "total_estime", "notes"}
REQUIRED_LIGNE_KEYS = {"designation", "quantite", "prix_unitaire"}

MODEL = "claude-sonnet-5"


class FacturationError(ValueError):
    pass


def _is_number_or_none(value) -> bool:
    return value is None or (isinstance(value, (int, float)) and not isinstance(value, bool))


def _parse_response(raw_text: str) -> dict:
    data = parse_json_object(raw_text, REQUIRED_KEYS, FacturationError)

    if not isinstance(data["lignes"], list) or not data["lignes"]:
        raise FacturationError("'lignes' doit etre une liste non vide")

    for ligne in data["lignes"]:
        if not isinstance(ligne, dict) or REQUIRED_LIGNE_KEYS - ligne.keys():
            raise FacturationError(f"Element 'lignes' invalide: {ligne!r}")
        if not _is_number_or_none(ligne["quantite"]):
            raise FacturationError(f"'quantite' invalide: {ligne['quantite']!r}")
        if not _is_number_or_none(ligne["prix_unitaire"]):
            raise FacturationError(f"'prix_unitaire' invalide: {ligne['prix_unitaire']!r}")

    if not _is_number_or_none(data["total_estime"]):
        raise FacturationError(f"'total_estime' invalide: {data['total_estime']!r}")

    return data


def facturation(text: str, client: anthropic.Anthropic | None = None) -> dict:
    client = client or get_client()
    response = client.messages.create(
        model=MODEL,
        max_tokens=700,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}],
    )
    return _parse_response(extract_text(response))


def facturation_export_xlsx(
    data: dict, output_path: str, client: anthropic.Anthropic | None = None
) -> str:
    """Genere un vrai fichier .xlsx pour un devis deja structure par facturation().
    Fonctionnalite beta (Agent Skills), consomme du temps de conteneur d'execution
    de code : voir `python app.py doctor`."""
    lignes_text = "\n".join(
        f"- {ligne['designation']} x{ligne['quantite']}"
        + (
            f" a {ligne['prix_unitaire']} EUR l'unite"
            if ligne["prix_unitaire"] is not None
            else " (prix a definir)"
        )
        for ligne in data["lignes"]
    )
    prompt = (
        "Cree un devis au format Excel (.xlsx), avec un tableau (designation, quantite, "
        "prix unitaire, total par ligne) et un total general en bas.\n"
        f"Client : {data['client'] or 'non precise'}\n"
        f"Lignes :\n{lignes_text}\n"
        f"Notes : {data['notes'] or 'aucune'}"
    )
    return generate_file_with_skill(prompt, "xlsx", output_path, client=client)

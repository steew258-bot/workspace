import json
import os

import anthropic
from dotenv import load_dotenv

load_dotenv()


class MissingApiKeyError(RuntimeError):
    pass


def get_client() -> anthropic.Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise MissingApiKeyError(
            "ANTHROPIC_API_KEY manquante. Copie .env.example en .env et renseigne ta cle, "
            "ou exporte la variable d'environnement directement."
        )
    return anthropic.Anthropic(api_key=api_key)


def extract_text(response: anthropic.types.Message) -> str:
    block = response.content[0]
    if not isinstance(block, anthropic.types.TextBlock):
        raise TypeError(f"Reponse Anthropic inattendue (pas de bloc texte): {block!r}")
    return block.text


def parse_json_object(
    raw_text: str, required_keys: set[str], error_cls: type[Exception]
) -> dict:
    """Parse le JSON strict attendu de chaque module : un objet contenant au moins
    required_keys. Leve error_cls (le <Nom>Error propre au module appelant) sur
    JSON invalide, non-objet, ou champ manquant. La validation specifique a chaque
    module continue apres cet appel."""
    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise error_cls(f"Reponse non JSON: {raw_text!r}") from exc

    if not isinstance(data, dict):
        raise error_cls(f"Reponse JSON invalide, objet attendu: {raw_text!r}")

    missing = required_keys - data.keys()
    if missing:
        raise error_cls(f"Champs manquants dans la reponse: {missing}")

    return data

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

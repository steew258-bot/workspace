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

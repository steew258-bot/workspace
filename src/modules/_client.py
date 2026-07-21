import os

import anthropic
from dotenv import load_dotenv

load_dotenv()


def get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

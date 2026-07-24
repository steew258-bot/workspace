import anthropic

from src.modules._client import extract_text, get_client, get_lang, parse_json_object
from src.modules._skills import generate_file_with_skill

SYSTEM_PROMPTS = {
    "fr": """Tu es un assistant de synthese. Analyse le texte long fourni (compte-rendu, \
document, fil d'emails...) et reponds UNIQUEMENT avec un JSON valide, sans aucun texte autour, \
au format :
{
  "resume": "<resume en 2 a 4 phrases>",
  "points_cles": ["<point cle 1>", "<point cle 2>", ...]
}""",
    "en": """You are a summarization assistant. Analyze the provided long text (report, \
document, email thread...) and reply ONLY with valid JSON, no surrounding text, in this \
format:
{
  "summary": "<summary in 2 to 4 sentences>",
  "key_points": ["<key point 1>", "<key point 2>", ...]
}""",
}

REQUIRED_KEYS = {
    "fr": {"resume", "points_cles"},
    "en": {"summary", "key_points"},
}

FIELDS = {
    "summary": {"fr": "resume", "en": "summary"},
    "key_points": {"fr": "points_cles", "en": "key_points"},
}

MODEL = "claude-sonnet-5"

_INVALID_SUMMARY_MESSAGES = {
    "fr": "'resume' doit etre une chaine non vide",
    "en": "'summary' must be a non-empty string",
}
_INVALID_KEY_POINTS_MESSAGES = {
    "fr": "'points_cles' doit etre une liste non vide",
    "en": "'key_points' must be a non-empty list",
}


class ResumeError(ValueError):
    pass


def _parse_response(raw_text: str, lang: str | None = None) -> dict:
    lang = get_lang(lang)
    data = parse_json_object(raw_text, REQUIRED_KEYS[lang], ResumeError, lang=lang)

    summary_key = FIELDS["summary"][lang]
    if not isinstance(data[summary_key], str) or not data[summary_key].strip():
        raise ResumeError(_INVALID_SUMMARY_MESSAGES[lang])

    key_points_key = FIELDS["key_points"][lang]
    if not isinstance(data[key_points_key], list) or not data[key_points_key]:
        raise ResumeError(_INVALID_KEY_POINTS_MESSAGES[lang])

    return data


def resume(text: str, client: anthropic.Anthropic | None = None, lang: str | None = None) -> dict:
    lang = get_lang(lang)
    client = client or get_client(lang=lang)
    response = client.messages.create(
        model=MODEL,
        max_tokens=600,
        system=SYSTEM_PROMPTS[lang],
        messages=[{"role": "user", "content": text}],
    )
    return _parse_response(extract_text(response, lang=lang), lang=lang)


_EXPORT_PROMPTS = {
    "fr": (
        "Cree un document Word (.docx) avec un titre, un paragraphe de resume, "
        "puis une liste a puces des points cles.\n"
        "Resume : {summary}\n"
        "Points cles :\n{points_text}"
    ),
    "en": (
        "Create a Word document (.docx) with a title, a summary paragraph, "
        "then a bulleted list of the key points.\n"
        "Summary: {summary}\n"
        "Key points:\n{points_text}"
    ),
}


def resume_export_docx(
    data: dict,
    output_path: str,
    client: anthropic.Anthropic | None = None,
    lang: str | None = None,
) -> str:
    """Genere un vrai rapport .docx a partir d'un resume deja structure par
    resume(). Fonctionnalite beta (Agent Skills), consomme du temps de
    conteneur d'execution de code : voir `python app.py doctor`."""
    lang = get_lang(lang)
    summary_key = FIELDS["summary"][lang]
    key_points_key = FIELDS["key_points"][lang]
    points_text = "\n".join(f"- {point}" for point in data[key_points_key])
    prompt = _EXPORT_PROMPTS[lang].format(summary=data[summary_key], points_text=points_text)
    return generate_file_with_skill(prompt, "docx", output_path, client=client)

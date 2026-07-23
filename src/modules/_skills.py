import os

import anthropic

from src.modules._client import get_client

BETAS: list[str] = ["code-execution-2025-08-25", "skills-2025-10-02"]
MODEL = "claude-sonnet-5"


class SkillsError(RuntimeError):
    pass


def _extract_file_id(response: anthropic.types.beta.BetaMessage) -> str | None:
    for block in response.content:
        if block.type != "bash_code_execution_tool_result":
            continue
        result = block.content
        if result.type != "bash_code_execution_result":
            continue
        for output in result.content:
            if output.type == "bash_code_execution_output":
                return output.file_id
    return None


def generate_file_with_skill(
    prompt: str,
    skill_id: str,
    output_path: str,
    client: anthropic.Anthropic | None = None,
) -> str:
    """Genere un fichier reel (xlsx, docx, ...) via une Agent Skill Anthropic et
    l'ecrit sur disque a output_path. Fonctionnalite beta : consomme du temps de
    conteneur d'execution de code (voir `python app.py doctor`)."""
    client = client or get_client()
    response = client.beta.messages.create(
        model=MODEL,
        max_tokens=4096,
        betas=BETAS,
        container={"skills": [{"type": "anthropic", "skill_id": skill_id, "version": "latest"}]},
        tools=[{"type": "code_execution_20260521", "name": "code_execution"}],
        messages=[{"role": "user", "content": prompt}],
    )

    file_id = _extract_file_id(response)
    if file_id is None:
        raise SkillsError(f"Aucun fichier genere par la skill '{skill_id}'.")

    directory = os.path.dirname(output_path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    client.beta.files.download(file_id).write_to_file(output_path)
    return output_path

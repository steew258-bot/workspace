from unittest.mock import MagicMock

import pytest

from src.modules._skills import SkillsError, generate_file_with_skill


def _fake_response(file_id: str | None) -> MagicMock:
    block = MagicMock()
    block.type = "bash_code_execution_tool_result"
    block.content.type = "bash_code_execution_result"
    if file_id is not None:
        output = MagicMock()
        output.type = "bash_code_execution_output"
        output.file_id = file_id
        block.content.content = [output]
    else:
        block.content.content = []

    response = MagicMock()
    response.content = [block]
    return response


def test_generate_file_with_skill_success(tmp_path):
    client = MagicMock()
    client.beta.messages.create.return_value = _fake_response("file_abc123")
    output_path = str(tmp_path / "devis.xlsx")

    result = generate_file_with_skill("Genere un devis", "xlsx", output_path, client=client)

    assert result == output_path
    kwargs = client.beta.messages.create.call_args.kwargs
    assert kwargs["betas"] == ["code-execution-2025-08-25", "skills-2025-10-02"]
    assert kwargs["container"] == {
        "skills": [{"type": "anthropic", "skill_id": "xlsx", "version": "latest"}]
    }
    assert kwargs["tools"] == [{"type": "code_execution_20260521", "name": "code_execution"}]
    client.beta.files.download.assert_called_once_with("file_abc123")
    client.beta.files.download.return_value.write_to_file.assert_called_once_with(output_path)


def test_generate_file_with_skill_creates_output_directory(tmp_path):
    client = MagicMock()
    client.beta.messages.create.return_value = _fake_response("file_xyz")
    output_path = str(tmp_path / "sous_dossier" / "devis.xlsx")

    generate_file_with_skill("Genere un devis", "xlsx", output_path, client=client)

    assert (tmp_path / "sous_dossier").is_dir()


def test_generate_file_with_skill_no_file_raises():
    client = MagicMock()
    client.beta.messages.create.return_value = _fake_response(None)

    with pytest.raises(SkillsError):
        generate_file_with_skill("Genere un devis", "xlsx", "devis.xlsx", client=client)

import json
from unittest.mock import patch

import pytest

from app import main


@pytest.mark.parametrize(
    ("command", "target", "fake_result"),
    [
        ("triage", "app.triage", {"action": "a", "urgence": "basse", "brouillon_reponse": "b"}),
        ("veille", "app.veille", {"a_traiter": [], "archive": ["x"]}),
        (
            "planification",
            "app.planification",
            {"ordre": ["a"], "tache_prioritaire": "a", "justification": "j"},
        ),
    ],
)
def test_command_prints_json(capsys, command, target, fake_result):
    with patch(target, return_value=fake_result) as mocked:
        main([command, "un texte quelconque"])

    mocked.assert_called_once_with("un texte quelconque")
    captured = capsys.readouterr()
    assert json.loads(captured.out) == fake_result

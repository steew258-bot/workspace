from unittest.mock import patch

from app import main


def test_triage_command_prints_json(capsys):
    fake_result = {"action": "a", "urgence": "basse", "brouillon_reponse": "b"}
    with patch("app.triage", return_value=fake_result) as mocked:
        main(["triage", "un texte quelconque"])

    mocked.assert_called_once_with("un texte quelconque")
    captured = capsys.readouterr()
    assert '"urgence": "basse"' in captured.out

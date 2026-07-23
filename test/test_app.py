import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from app import main


def test_main_forces_utf8_stdout_and_stderr():
    fake_out = MagicMock()
    fake_err = MagicMock()
    fake_result = {"action": "a", "urgence": "basse", "brouillon_reponse": "b"}

    with (
        patch.object(sys, "stdout", fake_out),
        patch.object(sys, "stderr", fake_err),
        patch("app.triage", return_value=fake_result),
    ):
        main(["triage", "texte"])

    fake_out.reconfigure.assert_called_once_with(encoding="utf-8")
    fake_err.reconfigure.assert_called_once_with(encoding="utf-8")


@pytest.mark.parametrize(
    ("command", "target", "fake_result"),
    [
        ("triage", "app.triage", {"action": "a", "urgence": "basse", "brouillon_reponse": "b"}),
        (
            "email",
            "app.email_triage",
            {
                "urgence": "basse",
                "necessite_reponse": False,
                "action": "a",
                "brouillon_reponse": "b",
            },
        ),
        ("veille", "app.veille", {"a_traiter": [], "archive": ["x"]}),
        (
            "planification",
            "app.planification",
            {"ordre": ["a"], "tache_prioritaire": "a", "justification": "j"},
        ),
        ("resume", "app.resume", {"resume": "r", "points_cles": ["a"]}),
        ("recherche", "app.recherche", {"reponse": "r", "sources": ["https://exemple.com"]}),
        (
            "crm",
            "app.crm",
            {
                "statut": "actif",
                "relance_a_faire": False,
                "action": "a",
                "risque_churn": "faible",
            },
        ),
        (
            "agenda",
            "app.agenda",
            {"conflits": [], "creneaux_libres": ["9h-10h"], "suggestions": []},
        ),
    ],
)
def test_command_prints_json(capsys, command, target, fake_result):
    with patch(target, return_value=fake_result) as mocked:
        main([command, "un texte quelconque"])

    mocked.assert_called_once_with("un texte quelconque")
    captured = capsys.readouterr()
    assert json.loads(captured.out) == fake_result


def test_email_check_processes_and_marks_read(capsys):
    messages = [
        {"uid": "1", "de": "a@exemple.com", "objet": "Sujet 1", "corps": "Corps 1"},
        {"uid": "2", "de": "b@exemple.com", "objet": "Sujet 2", "corps": "Corps 2"},
    ]
    analyse = {
        "urgence": "basse",
        "necessite_reponse": False,
        "action": "a",
        "brouillon_reponse": "b",
    }

    with (
        patch("app.fetch_unread", return_value=messages) as mocked_fetch,
        patch("app.email_triage", return_value=analyse) as mocked_triage,
        patch("app.mark_as_read") as mocked_mark,
        patch("app.notify_if_urgent") as mocked_notify,
    ):
        main(["email-check"])

    mocked_fetch.assert_called_once_with(mailbox="INBOX", max_messages=10)
    assert mocked_triage.call_count == 2
    mocked_mark.assert_called_once_with(["1", "2"], mailbox="INBOX")
    mocked_notify.assert_called_once()
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert len(result["traites"]) == 2
    assert result["traites"][0]["objet"] == "Sujet 1"


def test_email_check_skips_failed_analysis(capsys):
    from src.modules.email import EmailError

    messages = [{"uid": "1", "de": "a@exemple.com", "objet": "Sujet 1", "corps": "Corps 1"}]

    with (
        patch("app.fetch_unread", return_value=messages),
        patch("app.email_triage", side_effect=EmailError("reponse invalide")),
        patch("app.mark_as_read") as mocked_mark,
        patch("app.notify_if_urgent"),
    ):
        main(["email-check"])

    mocked_mark.assert_not_called()
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {"traites": []}


def test_email_check_skips_non_email_error_and_continues(capsys):
    messages = [
        {"uid": "1", "de": "a@exemple.com", "objet": "Sujet 1", "corps": "Corps 1"},
        {"uid": "2", "de": "b@exemple.com", "objet": "Sujet 2", "corps": "Corps 2"},
    ]
    analyse = {
        "urgence": "basse",
        "necessite_reponse": False,
        "action": "a",
        "brouillon_reponse": "b",
    }

    with (
        patch("app.fetch_unread", return_value=messages),
        patch("app.email_triage", side_effect=[RuntimeError("cle API invalide"), analyse]),
        patch("app.mark_as_read") as mocked_mark,
        patch("app.notify_if_urgent") as mocked_notify,
    ):
        main(["email-check"])

    mocked_mark.assert_called_once_with(["2"], mailbox="INBOX")
    mocked_notify.assert_called_once()
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert len(result["traites"]) == 1
    assert result["traites"][0]["objet"] == "Sujet 2"
    assert "cle API invalide" in captured.err


def test_email_check_mark_as_read_failure_still_reports_and_notifies(capsys):
    from src.modules.email_client import EmailClientError

    messages = [{"uid": "1", "de": "a@exemple.com", "objet": "Sujet urgent", "corps": "Corps"}]
    analyse = {
        "urgence": "haute",
        "necessite_reponse": True,
        "action": "a",
        "brouillon_reponse": "b",
    }

    with (
        patch("app.fetch_unread", return_value=messages),
        patch("app.email_triage", return_value=analyse),
        patch("app.mark_as_read", side_effect=EmailClientError("IMAP deconnecte")) as mocked_mark,
        patch("app.notify_if_urgent") as mocked_notify,
    ):
        main(["email-check"])

    mocked_mark.assert_called_once()
    mocked_notify.assert_called_once()
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert len(result["traites"]) == 1
    assert "IMAP deconnecte" in captured.err


def test_doctor_exits_zero_when_all_ok(capsys):
    fake_result = {"modules": {"triage": {"statut": "ok", "problemes": {}}}, "avertissements": []}

    with patch("app.check_environment", return_value=fake_result):
        with pytest.raises(SystemExit) as exc_info:
            main(["doctor"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert json.loads(captured.out) == fake_result


def test_doctor_exits_one_when_incomplete(capsys):
    fake_result = {
        "modules": {
            "triage": {"statut": "incomplet", "problemes": {"ANTHROPIC_API_KEY": "manquante"}}
        },
        "avertissements": [],
    }

    with patch("app.check_environment", return_value=fake_result):
        with pytest.raises(SystemExit) as exc_info:
            main(["doctor"])

    assert exc_info.value.code == 1


def test_email_send_calls_smtp(capsys):
    with patch("app.send_email") as mocked_send:
        main(["email-send", "a@exemple.com", "Sujet", "Corps"])

    mocked_send.assert_called_once_with("a@exemple.com", "Sujet", "Corps")
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result == {"statut": "envoye", "to": "a@exemple.com", "objet": "Sujet"}

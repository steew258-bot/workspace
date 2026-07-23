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
        (
            "facturation",
            "app.facturation",
            {
                "client": "X",
                "lignes": [{"designation": "A", "quantite": 1, "prix_unitaire": 10}],
                "total_estime": 10,
                "notes": "",
            },
        ),
    ],
)
def test_command_prints_json(capsys, command, target, fake_result):
    with patch(target, return_value=fake_result) as mocked:
        main([command, "un texte quelconque"])

    mocked.assert_called_once_with("un texte quelconque")
    captured = capsys.readouterr()
    assert json.loads(captured.out) == fake_result


def test_facturation_export_xlsx_flag_adds_file_path(capsys):
    devis = {
        "client": "X",
        "lignes": [{"designation": "A", "quantite": 1, "prix_unitaire": 10}],
        "total_estime": 10,
        "notes": "",
    }

    with (
        patch("app.facturation", return_value=devis) as mocked_facturation,
        patch("app.facturation_export_xlsx", return_value="devis.xlsx") as mocked_export,
        patch("app.notify_if_urgent") as mocked_notify,
    ):
        main(["facturation", "un texte quelconque", "--export-xlsx", "devis.xlsx"])

    mocked_facturation.assert_called_once_with("un texte quelconque")
    mocked_export.assert_called_once_with(devis, "devis.xlsx")
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result == {**devis, "fichier_xlsx": "devis.xlsx"}
    mocked_notify.assert_called_once_with("facturation", result)


def test_facturation_without_export_flag_skips_export(capsys):
    devis = {
        "client": "X",
        "lignes": [{"designation": "A", "quantite": 1, "prix_unitaire": 10}],
        "total_estime": 10,
        "notes": "",
    }

    with (
        patch("app.facturation", return_value=devis),
        patch("app.facturation_export_xlsx") as mocked_export,
        patch("app.notify_if_urgent"),
    ):
        main(["facturation", "un texte quelconque"])

    mocked_export.assert_not_called()
    captured = capsys.readouterr()
    assert json.loads(captured.out) == devis


def test_crm_export_xlsx_flag_adds_file_path(capsys):
    fiche = {
        "statut": "actif",
        "relance_a_faire": False,
        "action": "a",
        "risque_churn": "faible",
    }

    with (
        patch("app.crm", return_value=fiche) as mocked_crm,
        patch("app.crm_export_xlsx", return_value="fiche.xlsx") as mocked_export,
        patch("app.notify_if_urgent") as mocked_notify,
    ):
        main(["crm", "un texte quelconque", "--export-xlsx", "fiche.xlsx"])

    mocked_crm.assert_called_once_with("un texte quelconque")
    mocked_export.assert_called_once_with(fiche, "fiche.xlsx")
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result == {**fiche, "fichier_xlsx": "fiche.xlsx"}
    mocked_notify.assert_called_once_with("crm", result)


def test_crm_without_export_flag_skips_export(capsys):
    fiche = {
        "statut": "actif",
        "relance_a_faire": False,
        "action": "a",
        "risque_churn": "faible",
    }

    with (
        patch("app.crm", return_value=fiche),
        patch("app.crm_export_xlsx") as mocked_export,
        patch("app.notify_if_urgent"),
    ):
        main(["crm", "un texte quelconque"])

    mocked_export.assert_not_called()
    captured = capsys.readouterr()
    assert json.loads(captured.out) == fiche


def test_resume_export_docx_flag_adds_file_path(capsys):
    synthese = {"resume": "r", "points_cles": ["a"]}

    with (
        patch("app.resume", return_value=synthese) as mocked_resume,
        patch("app.resume_export_docx", return_value="rapport.docx") as mocked_export,
        patch("app.notify_if_urgent") as mocked_notify,
    ):
        main(["resume", "un texte quelconque", "--export-docx", "rapport.docx"])

    mocked_resume.assert_called_once_with("un texte quelconque")
    mocked_export.assert_called_once_with(synthese, "rapport.docx")
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result == {**synthese, "fichier_docx": "rapport.docx"}
    mocked_notify.assert_called_once_with("resume", result)


def test_resume_without_export_flag_skips_export(capsys):
    synthese = {"resume": "r", "points_cles": ["a"]}

    with (
        patch("app.resume", return_value=synthese),
        patch("app.resume_export_docx") as mocked_export,
        patch("app.notify_if_urgent"),
    ):
        main(["resume", "un texte quelconque"])

    mocked_export.assert_not_called()
    captured = capsys.readouterr()
    assert json.loads(captured.out) == synthese


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

    with (
        patch("app.check_environment", return_value=fake_result),
        pytest.raises(SystemExit) as exc_info,
    ):
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

    with (
        patch("app.check_environment", return_value=fake_result),
        pytest.raises(SystemExit) as exc_info,
    ):
        main(["doctor"])

    assert exc_info.value.code == 1


def test_email_send_calls_smtp(capsys):
    with patch("app.send_email") as mocked_send:
        main(["email-send", "a@exemple.com", "Sujet", "Corps"])

    mocked_send.assert_called_once_with("a@exemple.com", "Sujet", "Corps")
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result == {"statut": "envoye", "to": "a@exemple.com", "objet": "Sujet"}


def test_email_send_dry_run_does_not_send(capsys):
    with patch("app.send_email") as mocked_send:
        main(["email-send", "a@exemple.com", "Sujet", "Corps", "--dry-run"])

    mocked_send.assert_not_called()
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result == {
        "statut": "apercu",
        "to": "a@exemple.com",
        "objet": "Sujet",
        "corps": "Corps",
    }


def test_whatsapp_sends_message(capsys):
    fake_result = {"messages": [{"id": "wamid.1"}]}
    with patch("app.send_whatsapp_message", return_value=fake_result) as mocked:
        main(["whatsapp", "+33600000000", "Bonjour"])

    mocked.assert_called_once_with("+33600000000", "Bonjour")
    captured = capsys.readouterr()
    assert json.loads(captured.out) == {"messages": [{"id": "wamid.1"}]}


def test_whatsapp_dry_run_does_not_send(capsys):
    with patch("app.send_whatsapp_message") as mocked:
        main(["whatsapp", "+33600000000", "Bonjour", "--dry-run"])

    mocked.assert_not_called()
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result == {"statut": "apercu", "to": "+33600000000", "message": "Bonjour"}


def test_agenda_check_with_events_runs_analysis(capsys):
    events = [{"titre": "RDV client", "debut": "14h", "fin": "15h"}]
    analyse = {
        "conflits": [{"evenements": ["RDV client", "Appel"], "raison": "meme creneau"}],
        "creneaux_libres": [],
        "suggestions": [],
    }

    with (
        patch("app.fetch_events", return_value=events) as mocked_fetch,
        patch("app.agenda", return_value=analyse) as mocked_agenda,
        patch("app.notify_if_urgent") as mocked_notify,
    ):
        main(["agenda-check"])

    mocked_fetch.assert_called_once_with(day=None)
    mocked_agenda.assert_called_once()
    assert "RDV client" in mocked_agenda.call_args[0][0]
    mocked_notify.assert_called_once_with("agenda", analyse)
    captured = capsys.readouterr()
    assert json.loads(captured.out) == analyse


def test_agenda_check_without_events_skips_analysis(capsys):
    with (
        patch("app.fetch_events", return_value=[]),
        patch("app.agenda") as mocked_agenda,
        patch("app.notify_if_urgent") as mocked_notify,
    ):
        main(["agenda-check"])

    mocked_agenda.assert_not_called()
    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result == {"conflits": [], "creneaux_libres": [], "suggestions": []}
    mocked_notify.assert_called_once_with("agenda", result)


def test_agenda_check_with_date_argument(capsys):
    from datetime import date

    with (
        patch("app.fetch_events", return_value=[]) as mocked_fetch,
        patch("app.notify_if_urgent"),
    ):
        main(["agenda-check", "--date", "2026-08-06"])

    mocked_fetch.assert_called_once_with(day=date(2026, 8, 6))

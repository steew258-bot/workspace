from unittest.mock import patch

import pytest

from src.dashboard import app


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    return app.test_client()


def _fake_doctor_result(lang="fr"):
    if lang == "en":
        return {
            "modules": {"triage": {"status": "ok", "issues": {}}},
            "warnings": [],
        }
    return {
        "modules": {"triage": {"statut": "ok", "problemes": {}}},
        "avertissements": [],
    }


def test_index_shows_doctor_status(client):
    with patch("src.dashboard.check_environment", return_value=_fake_doctor_result()):
        response = client.get("/")

    assert response.status_code == 200
    body = response.text
    assert "triage" in body
    assert "OK" in body
    assert "Configuration" in body


def test_index_shows_warnings(client):
    result = {
        "modules": {"triage": {"statut": "ok", "problemes": {}}},
        "avertissements": ["WHATSAPP_NOTIFY_TO non definie"],
    }
    with patch("src.dashboard.check_environment", return_value=result):
        response = client.get("/")

    assert "WHATSAPP_NOTIFY_TO non definie" in response.text


def test_index_shows_module_issues(client):
    result = {
        "modules": {
            "triage": {"statut": "incomplet", "problemes": {"ANTHROPIC_API_KEY": "manquante"}}
        },
        "avertissements": [],
    }
    with patch("src.dashboard.check_environment", return_value=result):
        response = client.get("/")

    assert "incomplet" in response.text
    assert "ANTHROPIC_API_KEY" in response.text
    assert "manquante" in response.text


def test_run_triage_success(client):
    fake_result = {"action": "Rappeler", "urgence": "haute", "brouillon_reponse": "Bonjour"}

    with (
        patch("src.dashboard.check_environment", return_value=_fake_doctor_result()),
        patch("src.dashboard.triage", return_value=fake_result) as mocked_triage,
        patch("src.dashboard.notify_if_urgent") as mocked_notify,
    ):
        response = client.post("/run", data={"module": "triage", "text": "Un texte"})

    assert response.status_code == 200
    mocked_triage.assert_called_once_with("Un texte")
    mocked_notify.assert_called_once_with("triage", fake_result)
    body = response.text
    assert "Rappeler" in body
    assert "haute" in body


def test_run_crm_success(client):
    fake_result = {
        "statut": "actif",
        "relance_a_faire": False,
        "action": "Rien",
        "risque_churn": "faible",
    }

    with (
        patch("src.dashboard.check_environment", return_value=_fake_doctor_result()),
        patch("src.dashboard.crm", return_value=fake_result) as mocked_crm,
        patch("src.dashboard.notify_if_urgent"),
    ):
        response = client.post("/run", data={"module": "crm", "text": "Notes client"})

    assert response.status_code == 200
    mocked_crm.assert_called_once_with("Notes client")
    assert "actif" in response.text


def test_run_unknown_module_returns_400(client):
    with patch("src.dashboard.check_environment", return_value=_fake_doctor_result()):
        response = client.post("/run", data={"module": "not-a-module", "text": "x"})

    assert response.status_code == 400
    assert "not-a-module" in response.text


def test_run_missing_text_returns_400(client):
    with patch("src.dashboard.check_environment", return_value=_fake_doctor_result()):
        response = client.post("/run", data={"module": "triage", "text": ""})

    assert response.status_code == 400


def test_run_handler_exception_is_shown_not_raised(client):
    with (
        patch("src.dashboard.check_environment", return_value=_fake_doctor_result()),
        patch("src.dashboard.triage", side_effect=RuntimeError("cle API invalide")),
    ):
        response = client.post("/run", data={"module": "triage", "text": "Un texte"})

    assert response.status_code == 200
    assert "cle API invalide" in response.text


def test_run_does_not_notify_on_exception(client):
    with (
        patch("src.dashboard.check_environment", return_value=_fake_doctor_result()),
        patch("src.dashboard.triage", side_effect=RuntimeError("boom")),
        patch("src.dashboard.notify_if_urgent") as mocked_notify,
    ):
        client.post("/run", data={"module": "triage", "text": "Un texte"})

    mocked_notify.assert_not_called()


def test_index_lists_all_modules_in_select(client):
    with patch("src.dashboard.check_environment", return_value=_fake_doctor_result()):
        response = client.get("/")

    for module in (
        "triage",
        "veille",
        "planification",
        "resume",
        "email",
        "crm",
        "agenda",
        "recherche",
        "facturation",
    ):
        assert f'value="{module}"' in response.text


def test_index_english(monkeypatch, client):
    monkeypatch.setenv("OPS_AGENT_LANG", "en")

    with patch("src.dashboard.check_environment", return_value=_fake_doctor_result("en")):
        response = client.get("/")

    assert "Run a module" in response.text
    assert "Configuration" in response.text


def test_run_english(monkeypatch, client):
    monkeypatch.setenv("OPS_AGENT_LANG", "en")
    fake_result = {"action": "Call back", "urgency": "high", "reply_draft": "Hello"}

    with (
        patch("src.dashboard.check_environment", return_value=_fake_doctor_result("en")),
        patch("src.dashboard.triage", return_value=fake_result),
        patch("src.dashboard.notify_if_urgent"),
    ):
        response = client.post("/run", data={"module": "triage", "text": "Some text"})

    assert "Call back" in response.text
    assert "Result" in response.text

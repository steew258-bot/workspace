from unittest.mock import patch

from src.notifications import notify_if_urgent


def test_no_notify_target_does_nothing(monkeypatch):
    monkeypatch.delenv("WHATSAPP_NOTIFY_TO", raising=False)

    with patch("src.notifications.send_whatsapp_message") as mocked_send:
        notify_if_urgent("triage", {"urgence": "haute", "action": "a", "brouillon_reponse": "b"})

    mocked_send.assert_not_called()


def test_triage_haute_urgence_notifies(monkeypatch):
    monkeypatch.setenv("WHATSAPP_NOTIFY_TO", "+33600000000")

    result = {"action": "Repondre", "urgence": "haute", "brouillon_reponse": "Bonjour"}
    with patch("src.notifications.send_whatsapp_message") as mocked_send:
        notify_if_urgent("triage", result)

    mocked_send.assert_called_once()
    args, _ = mocked_send.call_args
    assert args[0] == "+33600000000"
    assert "Repondre" in args[1]


def test_triage_basse_urgence_does_not_notify(monkeypatch):
    monkeypatch.setenv("WHATSAPP_NOTIFY_TO", "+33600000000")

    result = {"action": "Repondre", "urgence": "basse", "brouillon_reponse": "Bonjour"}
    with patch("src.notifications.send_whatsapp_message") as mocked_send:
        notify_if_urgent("triage", result)

    mocked_send.assert_not_called()


def test_veille_with_items_notifies(monkeypatch):
    monkeypatch.setenv("WHATSAPP_NOTIFY_TO", "+33600000000")

    result = {
        "a_traiter": [{"titre": "Incident X", "raison": "Impact client"}],
        "archive": [],
    }
    with patch("src.notifications.send_whatsapp_message") as mocked_send:
        notify_if_urgent("veille", result)

    mocked_send.assert_called_once()
    args, _ = mocked_send.call_args
    assert "Incident X" in args[1]


def test_veille_feeds_treated_like_veille(monkeypatch):
    monkeypatch.setenv("WHATSAPP_NOTIFY_TO", "+33600000000")

    result = {"a_traiter": [{"titre": "T", "raison": "R"}], "archive": []}
    with patch("src.notifications.send_whatsapp_message") as mocked_send:
        notify_if_urgent("veille-feeds", result)

    mocked_send.assert_called_once()


def test_veille_without_items_does_not_notify(monkeypatch):
    monkeypatch.setenv("WHATSAPP_NOTIFY_TO", "+33600000000")

    result = {"a_traiter": [], "archive": ["x"]}
    with patch("src.notifications.send_whatsapp_message") as mocked_send:
        notify_if_urgent("veille", result)

    mocked_send.assert_not_called()


def test_send_failure_is_swallowed(monkeypatch):
    from src.modules.whatsapp import WhatsAppError

    monkeypatch.setenv("WHATSAPP_NOTIFY_TO", "+33600000000")

    with patch("src.notifications.send_whatsapp_message", side_effect=WhatsAppError("boom")):
        notify_if_urgent("triage", {"urgence": "haute", "action": "a", "brouillon_reponse": "b"})

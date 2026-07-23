from unittest.mock import patch

from src.notifications import notify_if_urgent


def test_no_notify_target_does_nothing(monkeypatch):
    monkeypatch.delenv("WHATSAPP_NOTIFY_TO", raising=False)

    with patch("src.notifications.send_whatsapp_message") as mocked_send:
        notify_if_urgent("triage", {"urgence": "haute", "action": "a", "brouillon_reponse": "b"})

    mocked_send.assert_not_called()


def test_triage_haute_urgence_notifies(monkeypatch):
    monkeypatch.setenv("WHATSAPP_NOTIFY_TO", "+33600000000")
    monkeypatch.delenv("WHATSAPP_NOTIFY_TEMPLATE", raising=False)

    result = {"action": "Repondre", "urgence": "haute", "brouillon_reponse": "Bonjour"}
    with patch("src.notifications.send_whatsapp_message") as mocked_send:
        notify_if_urgent("triage", result)

    mocked_send.assert_called_once()
    args, _ = mocked_send.call_args
    assert args[0] == "+33600000000"
    assert "Repondre" in args[1]


def test_triage_basse_urgence_does_not_notify(monkeypatch):
    monkeypatch.setenv("WHATSAPP_NOTIFY_TO", "+33600000000")
    monkeypatch.delenv("WHATSAPP_NOTIFY_TEMPLATE", raising=False)

    result = {"action": "Repondre", "urgence": "basse", "brouillon_reponse": "Bonjour"}
    with patch("src.notifications.send_whatsapp_message") as mocked_send:
        notify_if_urgent("triage", result)

    mocked_send.assert_not_called()


def test_veille_with_items_notifies(monkeypatch):
    monkeypatch.setenv("WHATSAPP_NOTIFY_TO", "+33600000000")
    monkeypatch.delenv("WHATSAPP_NOTIFY_TEMPLATE", raising=False)

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
    monkeypatch.delenv("WHATSAPP_NOTIFY_TEMPLATE", raising=False)

    result = {"a_traiter": [{"titre": "T", "raison": "R"}], "archive": []}
    with patch("src.notifications.send_whatsapp_message") as mocked_send:
        notify_if_urgent("veille-feeds", result)

    mocked_send.assert_called_once()


def test_veille_without_items_does_not_notify(monkeypatch):
    monkeypatch.setenv("WHATSAPP_NOTIFY_TO", "+33600000000")
    monkeypatch.delenv("WHATSAPP_NOTIFY_TEMPLATE", raising=False)

    result = {"a_traiter": [], "archive": ["x"]}
    with patch("src.notifications.send_whatsapp_message") as mocked_send:
        notify_if_urgent("veille", result)

    mocked_send.assert_not_called()


def test_email_haute_urgence_notifies(monkeypatch):
    monkeypatch.setenv("WHATSAPP_NOTIFY_TO", "+33600000000")
    monkeypatch.delenv("WHATSAPP_NOTIFY_TEMPLATE", raising=False)

    result = {
        "urgence": "haute",
        "necessite_reponse": True,
        "action": "Rappeler",
        "brouillon_reponse": "Bonjour",
    }
    with patch("src.notifications.send_whatsapp_message") as mocked_send:
        notify_if_urgent("email", result)

    mocked_send.assert_called_once()
    args, _ = mocked_send.call_args
    assert args[0] == "+33600000000"
    assert "Rappeler" in args[1]


def test_email_basse_urgence_does_not_notify(monkeypatch):
    monkeypatch.setenv("WHATSAPP_NOTIFY_TO", "+33600000000")
    monkeypatch.delenv("WHATSAPP_NOTIFY_TEMPLATE", raising=False)

    result = {
        "urgence": "basse",
        "necessite_reponse": False,
        "action": "Archiver",
        "brouillon_reponse": "",
    }
    with patch("src.notifications.send_whatsapp_message") as mocked_send:
        notify_if_urgent("email", result)

    mocked_send.assert_not_called()


def test_crm_risque_eleve_notifies(monkeypatch):
    monkeypatch.setenv("WHATSAPP_NOTIFY_TO", "+33600000000")
    monkeypatch.delenv("WHATSAPP_NOTIFY_TEMPLATE", raising=False)

    result = {
        "statut": "a relancer",
        "relance_a_faire": True,
        "action": "Rappeler avant vendredi",
        "risque_churn": "eleve",
    }
    with patch("src.notifications.send_whatsapp_message") as mocked_send:
        notify_if_urgent("crm", result)

    mocked_send.assert_called_once()
    args, _ = mocked_send.call_args
    assert "Rappeler avant vendredi" in args[1]


def test_crm_risque_faible_does_not_notify(monkeypatch):
    monkeypatch.setenv("WHATSAPP_NOTIFY_TO", "+33600000000")
    monkeypatch.delenv("WHATSAPP_NOTIFY_TEMPLATE", raising=False)

    result = {
        "statut": "actif",
        "relance_a_faire": False,
        "action": "Rien a faire",
        "risque_churn": "faible",
    }
    with patch("src.notifications.send_whatsapp_message") as mocked_send:
        notify_if_urgent("crm", result)

    mocked_send.assert_not_called()


def test_agenda_with_conflicts_notifies(monkeypatch):
    monkeypatch.setenv("WHATSAPP_NOTIFY_TO", "+33600000000")
    monkeypatch.delenv("WHATSAPP_NOTIFY_TEMPLATE", raising=False)

    result = {
        "conflits": [{"evenements": ["RDV client 14h", "Appel 14h"], "raison": "meme creneau"}],
        "creneaux_libres": [],
        "suggestions": [],
    }
    with patch("src.notifications.send_whatsapp_message") as mocked_send:
        notify_if_urgent("agenda", result)

    mocked_send.assert_called_once()
    args, _ = mocked_send.call_args
    assert "RDV client 14h" in args[1]


def test_agenda_without_conflicts_does_not_notify(monkeypatch):
    monkeypatch.setenv("WHATSAPP_NOTIFY_TO", "+33600000000")
    monkeypatch.delenv("WHATSAPP_NOTIFY_TEMPLATE", raising=False)

    result = {"conflits": [], "creneaux_libres": ["9h-10h"], "suggestions": []}
    with patch("src.notifications.send_whatsapp_message") as mocked_send:
        notify_if_urgent("agenda", result)

    mocked_send.assert_not_called()


def test_email_check_with_urgent_item_notifies(monkeypatch):
    monkeypatch.setenv("WHATSAPP_NOTIFY_TO", "+33600000000")
    monkeypatch.delenv("WHATSAPP_NOTIFY_TEMPLATE", raising=False)

    result = {
        "traites": [
            {"de": "client@exemple.com", "objet": "Urgent", "urgence": "haute"},
            {"de": "autre@exemple.com", "objet": "Info", "urgence": "basse"},
        ]
    }
    with patch("src.notifications.send_whatsapp_message") as mocked_send:
        notify_if_urgent("email-check", result)

    mocked_send.assert_called_once()
    args, _ = mocked_send.call_args
    assert "Urgent" in args[1]
    assert "client@exemple.com" in args[1]


def test_email_check_without_urgent_item_does_not_notify(monkeypatch):
    monkeypatch.setenv("WHATSAPP_NOTIFY_TO", "+33600000000")
    monkeypatch.delenv("WHATSAPP_NOTIFY_TEMPLATE", raising=False)

    result = {"traites": [{"de": "autre@exemple.com", "objet": "Info", "urgence": "basse"}]}
    with patch("src.notifications.send_whatsapp_message") as mocked_send:
        notify_if_urgent("email-check", result)

    mocked_send.assert_not_called()


def test_send_failure_is_swallowed(monkeypatch):
    from src.modules.whatsapp import WhatsAppError

    monkeypatch.setenv("WHATSAPP_NOTIFY_TO", "+33600000000")
    monkeypatch.delenv("WHATSAPP_NOTIFY_TEMPLATE", raising=False)

    with patch("src.notifications.send_whatsapp_message", side_effect=WhatsAppError("boom")):
        notify_if_urgent("triage", {"urgence": "haute", "action": "a", "brouillon_reponse": "b"})


def test_uses_template_when_configured(monkeypatch):
    monkeypatch.setenv("WHATSAPP_NOTIFY_TO", "+33600000000")
    monkeypatch.setenv("WHATSAPP_NOTIFY_TEMPLATE", "notification_urgente")
    monkeypatch.setenv("WHATSAPP_NOTIFY_TEMPLATE_LANG", "en_US")

    result = {"action": "Repondre", "urgence": "haute", "brouillon_reponse": "Bonjour"}
    with (
        patch("src.notifications.send_whatsapp_template") as mocked_template,
        patch("src.notifications.send_whatsapp_message") as mocked_message,
    ):
        notify_if_urgent("triage", result)

    mocked_message.assert_not_called()
    mocked_template.assert_called_once()
    args, kwargs = mocked_template.call_args
    assert args[0] == "+33600000000"
    assert args[1] == "notification_urgente"
    assert args[2] == "en_US"
    assert "Repondre" in kwargs["body_params"][0]


def test_template_default_language_is_fr(monkeypatch):
    monkeypatch.setenv("WHATSAPP_NOTIFY_TO", "+33600000000")
    monkeypatch.setenv("WHATSAPP_NOTIFY_TEMPLATE", "notification_urgente")
    monkeypatch.delenv("WHATSAPP_NOTIFY_TEMPLATE_LANG", raising=False)

    result = {"a_traiter": [{"titre": "T", "raison": "R"}], "archive": []}
    with patch("src.notifications.send_whatsapp_template") as mocked_template:
        notify_if_urgent("veille", result)

    assert mocked_template.call_args[0][2] == "fr"

import hashlib
import hmac
import json
from unittest.mock import patch

import pytest

from src.webhook import app


@pytest.fixture
def client():
    app.config.update(TESTING=True)
    return app.test_client()


def test_verify_success(monkeypatch, client):
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "my-verify-token")

    response = client.get(
        "/webhook",
        query_string={
            "hub.mode": "subscribe",
            "hub.verify_token": "my-verify-token",
            "hub.challenge": "123456",
        },
    )

    assert response.status_code == 200
    assert response.text == "123456"


def test_verify_wrong_token(monkeypatch, client):
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "my-verify-token")

    response = client.get(
        "/webhook",
        query_string={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong-token",
            "hub.challenge": "123456",
        },
    )

    assert response.status_code == 403


def test_verify_missing_env_var(monkeypatch, client):
    monkeypatch.delenv("WHATSAPP_VERIFY_TOKEN", raising=False)

    with pytest.raises(RuntimeError):
        client.get(
            "/webhook",
            query_string={
                "hub.mode": "subscribe",
                "hub.verify_token": "anything",
                "hub.challenge": "123456",
            },
        )


def _payload_with_message(sender: str, text: str) -> dict:
    return {
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "messages": [
                                {"from": sender, "text": {"body": text}},
                            ]
                        }
                    }
                ]
            }
        ]
    }


def test_receive_rejects_invalid_signature(monkeypatch, client):
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "app-secret")

    response = client.post(
        "/webhook",
        data=json.dumps(_payload_with_message("33600000000", "Bonjour")),
        content_type="application/json",
        headers={"X-Hub-Signature-256": "sha256=deadbeef"},
    )

    assert response.status_code == 403


def test_receive_triages_and_replies(monkeypatch, client):
    monkeypatch.delenv("WHATSAPP_APP_SECRET", raising=False)

    fake_triage_result = {
        "action": "Repondre au client",
        "urgence": "haute",
        "brouillon_reponse": "Bonjour, je reviens vers vous.",
    }

    with (
        patch("src.webhook.triage", return_value=fake_triage_result) as mocked_triage,
        patch("src.webhook.send_whatsapp_message") as mocked_send,
    ):
        response = client.post(
            "/webhook",
            data=json.dumps(_payload_with_message("33600000000", "Le client X est furieux")),
            content_type="application/json",
        )

    assert response.status_code == 200
    mocked_triage.assert_called_once_with("Le client X est furieux")
    mocked_send.assert_called_once()
    args, _ = mocked_send.call_args
    assert args[0] == "33600000000"
    assert "haute" in args[1]


def test_receive_with_valid_signature(monkeypatch, client):
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "app-secret")

    body = json.dumps(_payload_with_message("33600000000", "Bonjour")).encode("utf-8")
    signature = hmac.new(b"app-secret", body, hashlib.sha256).hexdigest()

    with (
        patch("src.webhook.triage", return_value={
            "action": "a", "urgence": "basse", "brouillon_reponse": "b",
        }),
        patch("src.webhook.send_whatsapp_message") as mocked_send,
    ):
        response = client.post(
            "/webhook",
            data=body,
            content_type="application/json",
            headers={"X-Hub-Signature-256": f"sha256={signature}"},
        )

    assert response.status_code == 200
    mocked_send.assert_called_once()

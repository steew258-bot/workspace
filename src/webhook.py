import hashlib
import hmac
import os
import sys

from flask import Flask, request

from src.modules.triage import triage
from src.modules.whatsapp import WhatsAppError, send_whatsapp_message

app = Flask(__name__)


class WebhookError(RuntimeError):
    pass


def _verify_token() -> str:
    token = os.environ.get("WHATSAPP_VERIFY_TOKEN")
    if not token:
        raise WebhookError(
            "WHATSAPP_VERIFY_TOKEN manquant. Choisis une valeur, ajoute-la a ton .env "
            "et renseigne la meme valeur dans la config du webhook Meta."
        )
    return token


def _verify_signature(payload: bytes, signature_header: str | None) -> bool:
    app_secret = os.environ.get("WHATSAPP_APP_SECRET")
    if not app_secret:
        print(
            "[webhook] avertissement: WHATSAPP_APP_SECRET non defini, signature non verifiee",
            file=sys.stderr,
        )
        return True

    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected = hmac.new(app_secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    received = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, received)


def _extract_messages(payload) -> list[dict]:
    if not isinstance(payload, dict):
        return []

    messages = []
    for entry in payload.get("entry", []):
        if not isinstance(entry, dict):
            continue
        for change in entry.get("changes", []):
            if not isinstance(change, dict):
                continue
            value = change.get("value")
            if not isinstance(value, dict):
                continue
            for message in value.get("messages", []):
                if isinstance(message, dict):
                    messages.append(message)
    return messages


def _handle_message(message: dict) -> None:
    sender = message.get("from")
    text_field = message.get("text")
    text = text_field.get("body") if isinstance(text_field, dict) else None
    if not sender or not text:
        return

    try:
        result = triage(text)
        reply = (
            f"Action : {result['action']}\n"
            f"Urgence : {result['urgence']}\n"
            f"Suggestion : {result['brouillon_reponse']}"
        )
    except Exception as exc:
        print(f"[webhook] echec du triage: {exc}", file=sys.stderr)
        reply = "Desole, une erreur est survenue lors de l'analyse de ton message."

    try:
        send_whatsapp_message(sender, reply)
    except WhatsAppError as exc:
        print(f"[webhook] echec de la reponse WhatsApp: {exc}", file=sys.stderr)


@app.get("/webhook")
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode == "subscribe" and token == _verify_token():
        return challenge, 200
    return "Verification token invalide", 403


@app.post("/webhook")
def receive():
    if not _verify_signature(request.get_data(), request.headers.get("X-Hub-Signature-256")):
        return "Signature invalide", 403

    payload = request.get_json(silent=True) or {}
    for message in _extract_messages(payload):
        _handle_message(message)

    return "", 200


def run(host: str = "0.0.0.0", port: int = 8000) -> None:
    _verify_token()
    from waitress import serve

    serve(app, host=host, port=port)

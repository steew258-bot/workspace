import os
import sys

from src.modules.whatsapp import WhatsAppError, send_whatsapp_message


def _notify_target() -> str | None:
    return os.environ.get("WHATSAPP_NOTIFY_TO")


def _send(message: str) -> None:
    to = _notify_target()
    if not to:
        return
    try:
        send_whatsapp_message(to, message)
    except WhatsAppError as exc:
        print(f"[notify] echec de l'envoi de la notification WhatsApp: {exc}", file=sys.stderr)


def notify_if_urgent(command: str, result: dict) -> None:
    if command == "triage" and result.get("urgence") == "haute":
        _send(
            "Triage urgent\n"
            f"Action : {result.get('action', '')}\n"
            f"Suggestion : {result.get('brouillon_reponse', '')}"
        )
    elif command in ("veille", "veille-feeds") and result.get("a_traiter"):
        items = result["a_traiter"]
        lignes = "\n".join(
            f"- {item.get('titre', '')} ({item.get('raison', '')})" for item in items
        )
        _send(f"Veille : {len(items)} element(s) prioritaire(s)\n{lignes}")

import json
import os
import urllib.error
import urllib.request

from dotenv import load_dotenv

load_dotenv()

SEND_TIMEOUT_SECONDS = 10

REQUIRED_ENV_VARS = ("WHATSAPP_API_URL", "WHATSAPP_PHONE_NUMBER_ID", "WHATSAPP_ACCESS_TOKEN")


class WhatsAppError(RuntimeError):
    pass


def _get_config() -> tuple[str, str, str]:
    values = {name: os.environ.get(name) for name in REQUIRED_ENV_VARS}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise WhatsAppError(
            f"Variables d'environnement manquantes: {', '.join(missing)}. "
            "Copie .env.example en .env et renseigne ces valeurs."
        )
    return (
        values["WHATSAPP_API_URL"],
        values["WHATSAPP_PHONE_NUMBER_ID"],
        values["WHATSAPP_ACCESS_TOKEN"],
    )


def send_whatsapp_message(to: str, message: str) -> dict:
    api_url, phone_number_id, access_token = _get_config()

    url = f"{api_url.rstrip('/')}/{phone_number_id}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message},
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=SEND_TIMEOUT_SECONDS) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise WhatsAppError(f"Echec de l'envoi WhatsApp ({exc.code}): {detail}") from exc
    except urllib.error.URLError as exc:
        raise WhatsAppError(f"Echec de l'envoi WhatsApp: {exc.reason}") from exc

    return json.loads(body)

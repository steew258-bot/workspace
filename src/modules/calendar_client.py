import json
import os
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone

from dotenv import load_dotenv

from src.retry import call_with_retry, is_transient_url_error

load_dotenv()

TOKEN_URL = "https://oauth2.googleapis.com/token"
EVENTS_URL_TEMPLATE = "https://www.googleapis.com/calendar/v3/calendars/{calendar_id}/events"
DEFAULT_CALENDAR_ID = "primary"
REQUEST_TIMEOUT_SECONDS = 10

REQUIRED_ENV_VARS = ("GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET", "GOOGLE_REFRESH_TOKEN")


class CalendarClientError(RuntimeError):
    pass


def _get_env() -> dict[str, str]:
    values = {name: os.environ.get(name, "").strip() for name in REQUIRED_ENV_VARS}
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise CalendarClientError(
            f"Variables d'environnement manquantes: {', '.join(missing)}. "
            "Lance scripts/google_oauth_setup.py pour les obtenir (voir README, section Agenda)."
        )
    return values


def _get_access_token() -> str:
    values = _get_env()
    payload = urllib.parse.urlencode(
        {
            "client_id": values["GOOGLE_CLIENT_ID"],
            "client_secret": values["GOOGLE_CLIENT_SECRET"],
            "refresh_token": values["GOOGLE_REFRESH_TOKEN"],
            "grant_type": "refresh_token",
        }
    ).encode("utf-8")

    request = urllib.request.Request(TOKEN_URL, data=payload, method="POST")

    def _do_request() -> bytes:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return response.read()

    try:
        body = call_with_retry(_do_request, is_retryable=is_transient_url_error)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise CalendarClientError(
            f"Echec du rafraichissement du token Google ({exc.code}): {detail}"
        ) from exc
    except urllib.error.URLError as exc:
        raise CalendarClientError(
            f"Echec du rafraichissement du token Google: {exc.reason}"
        ) from exc

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise CalendarClientError(f"Reponse token Google non JSON: {body!r}") from exc

    access_token = data.get("access_token") if isinstance(data, dict) else None
    if not isinstance(access_token, str):
        raise CalendarClientError(f"Reponse token Google sans access_token: {data!r}")

    return access_token


def _parse_event_time(event: dict, key: str) -> str:
    slot = event.get(key)
    if not isinstance(slot, dict):
        return ""
    return slot.get("dateTime") or slot.get("date") or ""


def fetch_events(day: date | None = None, calendar_id: str = DEFAULT_CALENDAR_ID) -> list[dict]:
    day = day or date.today()
    time_min = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
    time_max = time_min + timedelta(days=1)

    access_token = _get_access_token()
    query = urllib.parse.urlencode(
        {
            "timeMin": time_min.isoformat(),
            "timeMax": time_max.isoformat(),
            "singleEvents": "true",
            "orderBy": "startTime",
        }
    )
    url = EVENTS_URL_TEMPLATE.format(calendar_id=urllib.parse.quote(calendar_id)) + "?" + query
    request = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})

    def _do_request() -> bytes:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            return response.read()

    try:
        body = call_with_retry(_do_request, is_retryable=is_transient_url_error)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise CalendarClientError(
            f"Echec de la lecture du calendrier Google ({exc.code}): {detail}"
        ) from exc
    except urllib.error.URLError as exc:
        raise CalendarClientError(
            f"Echec de la lecture du calendrier Google: {exc.reason}"
        ) from exc

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise CalendarClientError(f"Reponse calendrier Google non JSON: {body!r}") from exc

    items = data.get("items") if isinstance(data, dict) else None
    if not isinstance(items, list):
        raise CalendarClientError(f"Reponse calendrier Google sans 'items': {data!r}")

    events = []
    for item in items:
        if not isinstance(item, dict):
            continue
        titre = item.get("summary")
        if not isinstance(titre, str) or not titre:
            continue
        events.append(
            {
                "titre": titre,
                "debut": _parse_event_time(item, "start"),
                "fin": _parse_event_time(item, "end"),
            }
        )

    return events

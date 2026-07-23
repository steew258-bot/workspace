"""Autorisation OAuth 2.0 unique pour connecter Ops Agent a Google Calendar.

Usage:
    python scripts/google_oauth_setup.py

Prerequis (voir README, section Agenda) :
1. Un projet Google Cloud Console avec l'API Google Calendar activee.
2. Des identifiants OAuth "Application de bureau" avec comme URI de
   redirection autorisee exactement : http://localhost:8765/oauth2callback
3. GOOGLE_CLIENT_ID et GOOGLE_CLIENT_SECRET deja renseignes dans .env.

Ce script ouvre une page Google dans ton navigateur, recupere le code
d'autorisation via un petit serveur local temporaire, l'echange contre
un refresh token, et l'affiche pour que tu l'ajoutes a .env
(GOOGLE_REFRESH_TOKEN). Aucune valeur n'est ecrite automatiquement dans
.env - tu gardes le controle.
"""

import http.server
import json
import os
import urllib.error
import urllib.parse
import urllib.request
import webbrowser

from dotenv import load_dotenv

load_dotenv()

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/calendar.readonly"
REDIRECT_PORT = 8765
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/oauth2callback"


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    authorization_code: str | None = None

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        code = params.get("code", [None])[0]

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

        if code:
            _CallbackHandler.authorization_code = code
            self.wfile.write(
                b"<p>Autorisation recue, tu peux revenir au terminal.</p>"
            )
        else:
            error = params.get("error", ["inconnue"])[0]
            self.wfile.write(f"<p>Echec de l'autorisation : {error}</p>".encode())

    def log_message(self, format_str: str, *args: object) -> None:
        pass  # silence les logs HTTP par defaut


def _get_client_credentials() -> tuple[str, str]:
    client_id = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.environ.get("GOOGLE_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        raise SystemExit(
            "GOOGLE_CLIENT_ID et GOOGLE_CLIENT_SECRET doivent etre deja renseignes dans .env "
            "(voir README, section Agenda, pour les obtenir depuis Google Cloud Console)."
        )
    return client_id, client_secret


def _exchange_code_for_tokens(code: str, client_id: str, client_secret: str) -> dict:
    payload = urllib.parse.urlencode(
        {
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": REDIRECT_URI,
            "grant_type": "authorization_code",
        }
    ).encode("utf-8")

    request = urllib.request.Request(TOKEN_URL, data=payload, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Echec de l'echange du code contre un token : {detail}") from exc

    return json.loads(body)


def run() -> None:
    client_id, client_secret = _get_client_credentials()

    params = urllib.parse.urlencode(
        {
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "response_type": "code",
            "scope": SCOPE,
            "access_type": "offline",
            "prompt": "consent",
        }
    )
    auth_url = f"{AUTH_URL}?{params}"

    print("Ouverture de la page d'autorisation Google dans ton navigateur...")
    print(f"Si elle ne s'ouvre pas automatiquement, va sur :\n{auth_url}\n")
    webbrowser.open(auth_url)

    server = http.server.HTTPServer(("localhost", REDIRECT_PORT), _CallbackHandler)
    print(f"En attente de l'autorisation sur {REDIRECT_URI} ...")
    while _CallbackHandler.authorization_code is None:
        server.handle_request()

    tokens = _exchange_code_for_tokens(
        _CallbackHandler.authorization_code, client_id, client_secret
    )
    refresh_token = tokens.get("refresh_token")

    if not refresh_token:
        raise SystemExit(
            "Aucun refresh_token recu. Si tu as deja autorise cette application avant, "
            "revoque l'acces sur https://myaccount.google.com/permissions puis relance ce "
            "script."
        )

    print("\nAutorisation reussie. Ajoute cette ligne a ton .env :\n")
    print(f"GOOGLE_REFRESH_TOKEN={refresh_token}")


if __name__ == "__main__":
    run()

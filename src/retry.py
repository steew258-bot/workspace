"""Retry/backoff pour les appels reseau des clients IMAP/SMTP/HTTP (WhatsApp,
Google Calendar). Ne reessaie que sur des erreurs jugees transitoires (coupure
reseau, timeout) ; jamais sur un echec d'authentification ou une reponse HTTP
d'erreur (401, 400...), qui ne beneficierait pas d'un nouvel essai immediat.
"""

import time
import urllib.error
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")

DEFAULT_ATTEMPTS = 3
DEFAULT_BASE_DELAY_SECONDS = 1.0


def call_with_retry(
    func: Callable[[], T],
    is_retryable: Callable[[Exception], bool],
    attempts: int = DEFAULT_ATTEMPTS,
    base_delay_seconds: float = DEFAULT_BASE_DELAY_SECONDS,
) -> T:
    for attempt in range(attempts):
        try:
            return func()
        except Exception as exc:
            if not is_retryable(exc) or attempt == attempts - 1:
                raise
            time.sleep(base_delay_seconds * (2**attempt))
    raise AssertionError("unreachable: call_with_retry attempts must be >= 1")


def is_transient_url_error(exc: Exception) -> bool:
    """Vrai pour une erreur reseau (DNS, connexion refusee, timeout), faux pour
    une reponse HTTP d'erreur (HTTPError, sous-classe de URLError) qui ne
    beneficierait pas d'un retry immediat."""
    return isinstance(exc, urllib.error.URLError) and not isinstance(
        exc, urllib.error.HTTPError
    )

import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from src.modules.feeds import FeedError, _parse_feeds_file, fetch_items

SAMPLE_RSS = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Flux Test</title>
    <item><title>Premier article</title></item>
    <item><title>Deuxieme article</title></item>
    <item><title>Troisieme article</title></item>
  </channel>
</rss>"""

EMPTY_RSS = """<?xml version="1.0"?>
<rss version="2.0">
  <channel>
    <title>Flux Vide</title>
  </channel>
</rss>"""


def test_fetch_items_from_feed_content():
    items = fetch_items([SAMPLE_RSS])
    assert items == [
        "[Flux Test] Premier article",
        "[Flux Test] Deuxieme article",
        "[Flux Test] Troisieme article",
    ]


def test_fetch_items_respects_max_per_feed():
    items = fetch_items([SAMPLE_RSS], max_per_feed=2)
    assert items == ["[Flux Test] Premier article", "[Flux Test] Deuxieme article"]


def test_fetch_items_empty_feed():
    assert fetch_items([EMPTY_RSS]) == []


def test_fetch_items_invalid_feed_raises():
    with pytest.raises(FeedError):
        fetch_items(["pas un flux du tout, juste du texte"])


def test_fetch_items_skips_broken_feed_but_continues():
    items = fetch_items([SAMPLE_RSS, "pas un flux valide", EMPTY_RSS])
    assert items == [
        "[Flux Test] Premier article",
        "[Flux Test] Deuxieme article",
        "[Flux Test] Troisieme article",
    ]


def test_fetch_items_retries_transient_url_error_then_succeeds(monkeypatch):
    monkeypatch.setattr("src.retry.time.sleep", lambda seconds: None)

    fake_response = MagicMock()
    fake_response.read.return_value = SAMPLE_RSS.encode("utf-8")
    fake_response.__enter__.return_value = fake_response

    with patch(
        "src.modules.feeds.urllib.request.urlopen",
        side_effect=[urllib.error.URLError("connection refused"), fake_response],
    ) as mocked:
        items = fetch_items(["https://exemple.com/feed.xml"])

    assert items == [
        "[Flux Test] Premier article",
        "[Flux Test] Deuxieme article",
        "[Flux Test] Troisieme article",
    ]
    assert mocked.call_count == 2


def test_fetch_items_http_error_not_retried_and_feed_skipped(monkeypatch):
    monkeypatch.setattr("src.retry.time.sleep", lambda seconds: None)

    http_error = urllib.error.HTTPError(
        url="https://exemple.com/feed.xml", code=404, msg="Not Found", hdrs=None, fp=None
    )

    with patch("src.modules.feeds.urllib.request.urlopen", side_effect=http_error) as mocked:
        items = fetch_items(["https://exemple.com/feed.xml", SAMPLE_RSS])

    assert mocked.call_count == 1
    assert items == [
        "[Flux Test] Premier article",
        "[Flux Test] Deuxieme article",
        "[Flux Test] Troisieme article",
    ]


def test_parse_feeds_file_skips_comments_and_blanks(tmp_path):
    feeds_file = tmp_path / "feeds.txt"
    feeds_file.write_text(
        "# commentaire\nhttps://example.com/feed1\n\nhttps://example.com/feed2\n",
        encoding="utf-8",
    )
    assert _parse_feeds_file(str(feeds_file)) == [
        "https://example.com/feed1",
        "https://example.com/feed2",
    ]

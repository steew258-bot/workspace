import sys
import urllib.request

import feedparser

DEFAULT_MAX_ITEMS_PER_FEED = 5
FETCH_TIMEOUT_SECONDS = 10


class FeedError(ValueError):
    pass


def _parse_feeds_file(path: str) -> list[str]:
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def _fetch_feed(url_or_content: str):
    if url_or_content.startswith(("http://", "https://")):
        with urllib.request.urlopen(url_or_content, timeout=FETCH_TIMEOUT_SECONDS) as response:
            content = response.read()
        return feedparser.parse(content)
    return feedparser.parse(url_or_content)


def fetch_items(feed_urls: list[str], max_per_feed: int = DEFAULT_MAX_ITEMS_PER_FEED) -> list[str]:
    items = []
    failures = []
    for url in feed_urls:
        try:
            parsed = _fetch_feed(url)
        except OSError as exc:
            failures.append(f"{url}: {exc}")
            continue

        if parsed.bozo and not parsed.entries:
            failures.append(f"{url}: flux illisible")
            continue

        source = parsed.feed.get("title", url)
        for entry in parsed.entries[:max_per_feed]:
            title = entry.get("title", "").strip()
            if title:
                items.append(f"[{source}] {title}")

    for failure in failures:
        print(f"[veille-feeds] avertissement, flux ignore : {failure}", file=sys.stderr)

    if not items and failures:
        raise FeedError(f"Aucun flux n'a pu etre lu: {'; '.join(failures)}")

    return items


def fetch_items_text(feeds_file: str, max_per_feed: int = DEFAULT_MAX_ITEMS_PER_FEED) -> str:
    feed_urls = _parse_feeds_file(feeds_file)
    items = fetch_items(feed_urls, max_per_feed=max_per_feed)
    return "\n".join(items)

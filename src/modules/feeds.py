import feedparser

DEFAULT_MAX_ITEMS_PER_FEED = 5


class FeedError(ValueError):
    pass


def _parse_feeds_file(path: str) -> list[str]:
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    return [line.strip() for line in lines if line.strip() and not line.strip().startswith("#")]


def fetch_items(feed_urls: list[str], max_per_feed: int = DEFAULT_MAX_ITEMS_PER_FEED) -> list[str]:
    items = []
    for url in feed_urls:
        parsed = feedparser.parse(url)
        if parsed.bozo and not parsed.entries:
            raise FeedError(f"Impossible de lire le flux: {url}")
        source = parsed.feed.get("title", url)
        for entry in parsed.entries[:max_per_feed]:
            title = entry.get("title", "").strip()
            if title:
                items.append(f"[{source}] {title}")
    return items


def fetch_items_text(feeds_file: str, max_per_feed: int = DEFAULT_MAX_ITEMS_PER_FEED) -> str:
    feed_urls = _parse_feeds_file(feeds_file)
    items = fetch_items(feed_urls, max_per_feed=max_per_feed)
    return "\n".join(items)

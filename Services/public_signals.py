import json
import os
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ElementTree
from datetime import datetime


USER_AGENT = "TusalamaRoadSafety/1.0 (public safety signals)"
MAX_POSTS = 8
ALLOWED_RSS_SUFFIXES = (".go.ke", ".kenha.co.ke")


def _get_json(url, headers=None):
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
            **(headers or {}),
        },
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        return json.load(response)


def _get_xml(url):
    parsed = urllib.parse.urlsplit(url)
    host = (parsed.hostname or "").lower()
    if (
        parsed.scheme != "https"
        or not host
        or parsed.username
        or parsed.password
        or not any(host.endswith(suffix) for suffix in ALLOWED_RSS_SUFFIXES)
    ):
        raise ValueError("RSS feeds must use HTTPS on an approved Kenyan government domain.")

    class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, new_url):
            return None

    opener = urllib.request.build_opener(NoRedirectHandler)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/atom+xml, application/xml"},
    )
    with opener.open(request, timeout=8) as response:
        final_url = urllib.parse.urlsplit(response.geturl())
        if final_url.scheme != "https" or final_url.hostname != host:
            raise ValueError("RSS feed redirected outside its approved host.")
        return ElementTree.fromstring(response.read(1_000_000))


def _element_text(element, name):
    for child in element.iter():
        if child.tag.rsplit("}", 1)[-1].lower() == name.lower():
            return " ".join("".join(child.itertext()).split())
    return ""


def _fetch_rss():
    urls = [
        value.strip()
        for value in os.environ.get("TUSALAMA_RSS_FEEDS", "").split(";")
        if value.strip()
    ]
    if not urls:
        return []
    signals = []
    for url in urls[:5]:
        try:
            root = _get_xml(url)
            for item in list(root.iter())[:200]:
                tag = item.tag.rsplit("}", 1)[-1].lower()
                if tag not in {"item", "entry"}:
                    continue
                title = _element_text(item, "title")
                description = _element_text(item, "description") or _element_text(item, "summary")
                published = (
                    _element_text(item, "pubdate")
                    or _element_text(item, "published")
                    or _element_text(item, "updated")
                )
                link = _element_text(item, "link")
                if not link:
                    link_node = next(
                        (
                            child for child in item
                            if child.tag.rsplit("}", 1)[-1].lower() == "link"
                        ),
                        None,
                    )
                    if link_node is not None:
                        link = link_node.attrib.get("href", "")
                signals.append({
                    "source": urllib.parse.urlsplit(url).hostname,
                    "platform": "Official RSS",
                    "text": (title + (" — " + description if description else ""))[:1000],
                    "published": published[:80],
                    "url": link[:500],
                    "verified": False,
                })
                if len(signals) >= MAX_POSTS:
                    return signals
        except (urllib.error.URLError, TimeoutError, ValueError, ElementTree.ParseError) as error:
            signals.append({
                "source": urllib.parse.urlsplit(url).hostname or "Configured RSS",
                "platform": "Official RSS",
                "error": str(error),
                "verified": False,
            })
    return signals[:MAX_POSTS]


def _fetch_bluesky():
    handles = [
        handle.strip().lstrip("@")
        for handle in os.environ.get("TUSALAMA_BSKY_HANDLES", "").split(",")
        if handle.strip()
    ]
    signals = []
    for handle in handles[:5]:
        query = urllib.parse.urlencode({"actor": handle, "limit": str(MAX_POSTS)})
        try:
            payload = _get_json(
                "https://public.api.bsky.app/xrpc/app.bsky.feed.getAuthorFeed?"
                + query
            )
            for post in payload.get("feed", []):
                record = post.get("post", {})
                text = record.get("record", {}).get("text", "")
                if not text:
                    continue
                signals.append({
                    "source": "@" + handle,
                    "platform": "Bluesky",
                    "text": text[:1000],
                    "published": record.get("indexedAt", ""),
                    "url": "",
                    "verified": False,
                })
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as error:
            signals.append({
                "source": "@" + handle,
                "platform": "Bluesky",
                "error": str(error),
                "verified": False,
            })
    return signals[:MAX_POSTS]


def _fetch_x():
    user_ids = [
        value.strip()
        for value in os.environ.get("TUSALAMA_X_USER_IDS", "").split(",")
        if value.strip()
    ]
    token = os.environ.get("TUSALAMA_X_BEARER_TOKEN", "")
    if not user_ids:
        return []
    if not token:
        return [{
            "source": "Configured X accounts",
            "platform": "X",
            "error": "Set TUSALAMA_X_BEARER_TOKEN to use the official X API.",
            "verified": False,
        }]
    signals = []
    for user_id in user_ids[:5]:
        query = urllib.parse.urlencode({
            "max_results": "10",
            "tweet.fields": "created_at",
            "exclude": "retweets,replies",
        })
        try:
            payload = _get_json(
                f"https://api.x.com/2/users/{urllib.parse.quote(user_id, safe='')}/tweets?{query}",
                {"Authorization": f"Bearer {token}"},
            )
            for post in payload.get("data", []):
                signals.append({
                    "source": f"X user {user_id}",
                    "platform": "X",
                    "text": post.get("text", "")[:1000],
                    "published": post.get("created_at", ""),
                    "url": "",
                    "verified": False,
                })
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, ValueError) as error:
            signals.append({
                "source": f"X user {user_id}",
                "platform": "X",
                "error": str(error),
                "verified": False,
            })
    return signals[:MAX_POSTS]


def fetch_public_safety_signals():
    """Fetch only explicitly configured public accounts and official RSS feeds."""
    signals = _fetch_x() + _fetch_bluesky() + _fetch_rss()
    signals.sort(
        key=lambda item: item.get("published", ""),
        reverse=True,
    )
    return {
        "fetched_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "signals": signals[:MAX_POSTS],
        "verified_incidents": 0,
        "notice": (
            "Public posts are unverified leads, not confirmed incidents. "
            "Review and verify with the responsible agency before taking action."
        ),
    }

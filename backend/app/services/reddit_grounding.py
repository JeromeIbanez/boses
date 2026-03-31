"""
reddit_grounding.py
Fetches real Reddit posts from location-relevant subreddits via Reddit's
public JSON API (no credentials required) and formats them as a social
listening context block for injection into persona generation prompts.

Results are cached in-memory with a 6-hour TTL to stay within rate limits.
"""
from __future__ import annotations

import hashlib
import logging
import re
import time

import httpx

from app.services.grounding import get_country_key

logger = logging.getLogger(__name__)

_USER_AGENT = "boses-persona-generator/1.0 (market research tool)"
_REQUEST_TIMEOUT = 8  # seconds

# ---------------------------------------------------------------------------
# Location → subreddits mapping
# ---------------------------------------------------------------------------

_LOCATION_SUBREDDITS: dict[str, list[str]] = {
    "philippines": ["Philippines", "phcareers", "phfinance"],
    "indonesia":   ["indonesia"],
    "singapore":   ["singapore", "singaporefi"],
    "malaysia":    ["malaysia"],
    "vietnam":     ["vietnam"],
    "thailand":    ["thailand"],
    "usa":         ["AskAmerica", "personalfinance"],
    "uk":          ["unitedkingdom", "UKPersonalFinance"],
    "india":       ["india", "IndiaInvestments"],
}

# ---------------------------------------------------------------------------
# In-memory TTL cache: key → (content, fetched_at_timestamp)
# ---------------------------------------------------------------------------

_CACHE: dict[str, tuple[str, float]] = {}
_CACHE_TTL_SECONDS = 6 * 60 * 60  # 6 hours

_STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "is", "are", "was", "be", "by", "as", "it", "its",
    "this", "that", "they", "we", "our", "their", "my", "i", "you", "who",
    "what", "when", "where", "how", "not", "no", "so", "do", "have",
}


def _build_cache_key(country_key: str, topic_context: str) -> str:
    topic_hash = hashlib.md5(topic_context.lower().encode()).hexdigest()[:8]
    return f"{country_key}:{topic_hash}"


def _extract_keywords(text: str, max_keywords: int = 5) -> list[str]:
    words = re.findall(r"[a-zA-Z]+", text.lower())
    keywords = [w for w in words if w not in _STOP_WORDS and len(w) > 3]
    seen: set[str] = set()
    unique = []
    for kw in keywords:
        if kw not in seen:
            seen.add(kw)
            unique.append(kw)
    return unique[:max_keywords]


def _fetch_posts(subreddits: list[str], query: str) -> list[dict]:
    """
    Fetch up to 8 posts across the given subreddits using Reddit's public JSON API.
    Uses search when a query is provided, otherwise fetches top posts.
    """
    posts: list[dict] = []
    combined = "+".join(subreddits)
    headers = {"User-Agent": _USER_AGENT}

    if query:
        url = f"https://www.reddit.com/r/{combined}/search.json"
        params = {"q": query, "sort": "top", "t": "year", "limit": "8", "restrict_sr": "1"}
    else:
        url = f"https://www.reddit.com/r/{combined}/top.json"
        params = {"t": "year", "limit": "8"}

    try:
        with httpx.Client(timeout=_REQUEST_TIMEOUT) as client:
            response = client.get(url, params=params, headers=headers)
            response.raise_for_status()
            data = response.json()
    except Exception as e:
        logger.warning(f"reddit_grounding: error fetching posts from r/{combined}: {e}")
        return posts

    for child in data.get("data", {}).get("children", []):
        post_data = child.get("data", {})
        if post_data.get("stickied"):
            continue
        title = post_data.get("title", "").strip()
        if not title:
            continue

        # Fetch top comments for this post
        top_comments: list[str] = []
        try:
            post_id = post_data.get("id")
            sub_name = post_data.get("subreddit")
            comments_url = f"https://www.reddit.com/r/{sub_name}/comments/{post_id}.json"
            with httpx.Client(timeout=_REQUEST_TIMEOUT) as client:
                cr = client.get(comments_url, params={"limit": "5"}, headers=headers)
                cr.raise_for_status()
                comments_data = cr.json()
            if isinstance(comments_data, list) and len(comments_data) > 1:
                for comment_child in comments_data[1].get("data", {}).get("children", [])[:3]:
                    body = comment_child.get("data", {}).get("body", "").strip().replace("\n", " ")
                    if len(body) > 15 and body != "[deleted]" and body != "[removed]":
                        top_comments.append(body[:120])
        except Exception:
            pass

        posts.append({"title": title, "top_comments": top_comments})

    logger.info(f"reddit_grounding: fetched {len(posts)} posts from r/{combined}")
    return posts


def _format_context_block(posts: list[dict], subreddits: list[str]) -> str:
    if not posts:
        return ""

    sub_labels = ", ".join(f"r/{s}" for s in subreddits)
    lines: list[str] = [
        "=== SOCIAL LISTENING: WHAT REAL PEOPLE SAY ===",
        f"Source: Reddit ({sub_labels}) — real consumer voices, not statistics.",
        "Use these signals to make pain_points, purchase_behavior, and",
        "values_and_motivations feel authentic — borrow the language and",
        "concerns you see here.\n",
    ]

    total_chars = 0
    char_budget = 1400

    for post in posts:
        entry = f'[Post] "{post["title"]}"'
        for comment in post["top_comments"][:2]:
            entry += f'\n  → "{comment}"'
        entry += "\n"
        if total_chars + len(entry) > char_budget:
            break
        lines.append(entry)
        total_chars += len(entry)

    lines.append("=== END SOCIAL LISTENING ===\n")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def fetch_reddit_signals(location: str, topic_context: str) -> str:
    """
    Return a formatted social listening context block for the given location
    and topic context, suitable for injection into a GPT persona prompt.

    Returns "" if no subreddits are mapped for this location or any error occurs.
    No credentials required — uses Reddit's public JSON API.
    """
    country_key = get_country_key(location)
    if not country_key:
        logger.debug(f"reddit_grounding: no mapping for location '{location}'")
        return ""

    subreddits = _LOCATION_SUBREDDITS.get(country_key)
    if not subreddits:
        logger.debug(f"reddit_grounding: no subreddits defined for '{country_key}'")
        return ""

    cache_key = _build_cache_key(country_key, topic_context)
    cached = _CACHE.get(cache_key)
    if cached:
        content, fetched_at = cached
        if time.time() - fetched_at < _CACHE_TTL_SECONDS:
            logger.debug(f"reddit_grounding: cache hit for key '{cache_key}'")
            return content

    try:
        keywords = _extract_keywords(topic_context)
        query = " ".join(keywords) if keywords else ""
        posts = _fetch_posts(subreddits, query)
        result = _format_context_block(posts, subreddits)
    except Exception as e:
        logger.warning(f"reddit_grounding: unexpected error for '{location}': {e}")
        return ""

    _CACHE[cache_key] = (result, time.time())
    return result

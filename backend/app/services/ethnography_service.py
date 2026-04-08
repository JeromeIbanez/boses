"""
ethnography_service.py

Automated web ethnography pipeline for SEA markets (ID, PH, VN).

Architecture
------------
1. Crawl public sources per market (per-market functions, not a config dict)
2. Extract structured behavioral signals via LLM
3. Run quality gate (score >= 0.5 required to activate)
4. Store as CulturalContextSnapshot — "active" status means it gets injected
   into persona generation prompts. "draft" means quality gate failed silently.

Why per-market functions instead of a config dict + type dispatch:
    A config dict requires a handler per source type, adding an abstraction
    layer that earns its complexity only at 5+ markets. At 3 markets, explicit
    functions are more readable and easier to debug. Revisit if markets grow
    past 5 or sources need to be editable without a code deploy.

Safety principle:
    get_cultural_context_block() returns None for unrecognised locations.
    persona_generator.py only appends the block if it is not None.
    This means: no active snapshot → zero change to existing behaviour.

Sources by market (see plan for source selection rationale):
    PH: r/Philippines (3.5M members) — primary
    ID: Kaskus (primary), r/indonesia (supplement — Reddit is banned in ID,
        so this community skews VPN-using urban/tech users)
    VN: r/VietNam (1.4M members) — primary accessible source

Future sources (stubbed, fail gracefully):
    Shopee product reviews — requires product ID navigation, not yet implemented
    Google Play Store reviews — requires dynamic rendering workaround
    These are noted in the per-market functions with TODO comments.
"""
from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timedelta

import httpx
from app.services.openai_client import get_openai_client
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models.cultural_context import CulturalContextSnapshot
from app.services.grounding import get_country_key

logger = logging.getLogger(__name__)

_USER_AGENT = "boses-ethnography/1.0 (market research platform)"
_REQUEST_TIMEOUT = 10  # seconds
_STALENESS_DAYS = 30   # trigger refresh if active snapshot is older than this

# Map market codes to grounding.py country keys (reuse existing location detection)
_MARKET_TO_COUNTRY_KEY = {
    "ID": "indonesia",
    "PH": "philippines",
    "VN": "vietnam",
}
_COUNTRY_KEY_TO_MARKET = {v: k for k, v in _MARKET_TO_COUNTRY_KEY.items()}

# Required signal categories — used by quality gate
_REQUIRED_SIGNAL_KEYS = [
    "top_spending_categories",
    "trusted_brands",
    "dominant_anxieties",
    "aspirations",
    "digital_habits",
]


# ---------------------------------------------------------------------------
# Market detection
# ---------------------------------------------------------------------------

def _detect_market(location: str) -> str | None:
    """
    Detect which market code (ID/PH/VN) a location string belongs to.
    Delegates to get_country_key() from grounding.py so location mapping
    stays in one place and doesn't drift.
    Returns None for locations outside our supported markets.
    """
    country_key = get_country_key(location)
    return _COUNTRY_KEY_TO_MARKET.get(country_key)


# ---------------------------------------------------------------------------
# Reddit crawl helper (reuses pattern from reddit_grounding.py)
# ---------------------------------------------------------------------------

def _crawl_reddit_subreddit(
    subreddit: str,
    limit: int = 25,
    vertical: str | None = None,
) -> dict | None:
    """
    Fetch posts + comments from a subreddit via Reddit's public JSON API.
    No credentials required. Returns {source, post_count, text} or None on failure.

    When vertical is provided, uses Reddit's search endpoint with that keyword
    (e.g. "fintech", "beauty") instead of fetching top posts — this surfaces
    commercially relevant content rather than civic/general noise.

    NOTE: The subreddit slug is case-sensitive for Reddit's API.
    Verified slugs: Philippines, indonesia, VietNam
    """
    headers = {"User-Agent": _USER_AGENT}

    if vertical:
        url = f"https://www.reddit.com/r/{subreddit}/search.json"
        params = {"q": vertical, "sort": "top", "t": "month", "limit": str(limit), "restrict_sr": "1"}
        source_label = f"r/{subreddit} (search: {vertical})"
    else:
        url = f"https://www.reddit.com/r/{subreddit}/top.json"
        params = {"t": "month", "limit": str(limit)}
        source_label = f"r/{subreddit}"

    try:
        with httpx.Client(timeout=_REQUEST_TIMEOUT) as client:
            resp = client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.warning(f"[ethnography] Reddit crawl failed for {source_label}: {e}")
        return None

    posts = data.get("data", {}).get("children", [])
    text_chunks: list[str] = []

    for child in posts:
        post = child.get("data", {})
        if post.get("stickied"):
            continue
        title = post.get("title", "").strip()
        selftext = post.get("selftext", "").strip()
        if not title:
            continue
        chunk = f'[Post] "{title}"'
        if selftext and len(selftext) > 20:
            chunk += f"\n{selftext[:300]}"
        text_chunks.append(chunk)

        # Fetch top 3 comments for this post
        try:
            post_id = post.get("id")
            sub = post.get("subreddit")
            comments_url = f"https://www.reddit.com/r/{sub}/comments/{post_id}.json"
            with httpx.Client(timeout=_REQUEST_TIMEOUT) as client:
                cr = client.get(comments_url, params={"limit": "5"}, headers=headers)
                cr.raise_for_status()
                comments_data = cr.json()
            if isinstance(comments_data, list) and len(comments_data) > 1:
                for cc in comments_data[1].get("data", {}).get("children", [])[:3]:
                    body = cc.get("data", {}).get("body", "").strip().replace("\n", " ")
                    if len(body) > 20 and body not in ("[deleted]", "[removed]"):
                        text_chunks.append(f'  → "{body[:200]}"')
        except Exception:
            pass  # Comments are optional; continue without them

    if not text_chunks:
        logger.warning(f"[ethnography] {source_label}: no posts retrieved")
        return None

    logger.info(f"[ethnography] {source_label}: retrieved {len(posts)} posts")
    return {
        "source": source_label,
        "post_count": len(posts),
        "text": "\n".join(text_chunks[:60]),  # cap to ~60 chunks to control token size
    }


# ---------------------------------------------------------------------------
# Kaskus crawl (Indonesia's largest public forum)
# ---------------------------------------------------------------------------

def _crawl_kaskus() -> dict | None:
    """
    Attempt to fetch recent posts from Kaskus public forum pages.
    Kaskus is Indonesia's largest forum (~30M users) and posts in Bahasa
    Indonesia — more representative than Reddit for the Indonesian market.

    Falls back gracefully: if Kaskus blocks or changes structure, returns None
    and the pipeline continues with whatever other sources returned.

    TODO: Kaskus has changed their forum structure over the years. If this
    returns None consistently, check the current URL structure at
    kaskus.co.id/forum and update the category URLs below.
    """
    category_urls = [
        "https://www.kaskus.co.id/forum/0x2007000000000000/the-lounge/",
        "https://www.kaskus.co.id/forum/0x2010000000000000/fashion-beauty/",
    ]
    headers = {
        "User-Agent": _USER_AGENT,
        "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
    }

    text_chunks: list[str] = []

    for url in category_urls:
        try:
            with httpx.Client(timeout=_REQUEST_TIMEOUT, follow_redirects=True) as client:
                resp = client.get(url, headers=headers)
                resp.raise_for_status()
                html = resp.text

            # Very basic extraction: look for thread titles in the HTML.
            # Kaskus thread titles are typically in <a> tags inside thread list items.
            # This is intentionally simple — Kaskus may render differently.
            import re
            titles = re.findall(r'class="[^"]*thread[^"]*"[^>]*>([^<]{10,150})<', html)
            if not titles:
                # Fallback: grab any meaningful text content between tags
                titles = re.findall(r'>([A-Za-z\u00C0-\u024F\u0100-\u017E][^<]{15,120})<', html)

            for title in titles[:15]:
                clean = title.strip()
                if clean:
                    text_chunks.append(f'[Kaskus thread] "{clean}"')

        except Exception as e:
            logger.warning(f"[ethnography] Kaskus crawl failed for {url}: {e}")
            continue

    if not text_chunks:
        logger.warning("[ethnography] Kaskus: no content retrieved — skipping source")
        return None

    logger.info(f"[ethnography] Kaskus: retrieved {len(text_chunks)} thread titles")
    return {
        "source": "Kaskus forum",
        "post_count": len(text_chunks),
        "text": "\n".join(text_chunks),
    }


# ---------------------------------------------------------------------------
# Shopee crawl
# ---------------------------------------------------------------------------

_SHOPEE_MARKET_TLD = {"PH": "ph", "ID": "co.id", "VN": "vn"}
# Default search keyword per market when no vertical is provided
_SHOPEE_DEFAULT_KEYWORDS = {
    "PH": "bestseller",
    "ID": "terlaris",   # "bestselling" in Bahasa Indonesia
    "VN": "bán chạy",   # "bestselling" in Vietnamese
}


def _crawl_shopee_reviews(market_code: str, vertical: str | None = None) -> dict | None:
    """
    Fetch product reviews from Shopee for the given market via the public search + ratings API.

    Pipeline:
        1. Search for products by keyword (vertical if provided, else market default)
        2. Pick the product with the most reviews (highest comment_count)
        3. Fetch up to 20 reviews for that product

    Falls back gracefully: any HTTP error or unexpected response shape returns None.
    Shopee's API endpoints have been stable across markets (PH/ID/VN) but may
    require header adjustments if they start returning 403.
    """
    tld = _SHOPEE_MARKET_TLD.get(market_code)
    if not tld:
        logger.warning(f"[ethnography] Shopee: unsupported market '{market_code}'")
        return None

    keyword = vertical if vertical else _SHOPEE_DEFAULT_KEYWORDS.get(market_code, "bestseller")
    base_url = f"https://shopee.{tld}"
    headers = {
        "User-Agent": _USER_AGENT,
        "Referer": f"{base_url}/",
        "Accept": "application/json",
        "X-Requested-With": "XMLHttpRequest",
    }

    # Step 1: search for products
    try:
        search_url = f"{base_url}/api/v4/search/search_items"
        with httpx.Client(timeout=_REQUEST_TIMEOUT) as client:
            resp = client.get(
                search_url,
                params={"keyword": keyword, "limit": "10", "newest": "0"},
                headers=headers,
            )
            resp.raise_for_status()
            search_data = resp.json()
    except Exception as e:
        logger.warning(f"[ethnography] Shopee {market_code} search failed: {e}")
        return None

    items = search_data.get("items") or []
    if not items:
        logger.warning(f"[ethnography] Shopee {market_code}: no items returned for keyword '{keyword}'")
        return None

    # Step 2: pick item with highest comment_count > 0
    best_item = None
    best_count = 0
    for entry in items:
        basic = entry.get("item_basic") or {}
        count = basic.get("comment_count") or 0
        if count > best_count:
            best_count = count
            best_item = basic

    if not best_item or best_count == 0:
        logger.warning(f"[ethnography] Shopee {market_code}: no reviewed items found for '{keyword}'")
        return None

    item_id = best_item.get("itemid")
    shop_id = best_item.get("shopid")
    item_name = str(best_item.get("name", "product"))[:60]

    if not item_id or not shop_id:
        logger.warning(f"[ethnography] Shopee {market_code}: missing itemid/shopid")
        return None

    # Step 3: fetch reviews
    try:
        ratings_url = f"{base_url}/api/v4/item/get_ratings"
        with httpx.Client(timeout=_REQUEST_TIMEOUT) as client:
            resp = client.get(
                ratings_url,
                params={
                    "itemid": str(item_id),
                    "shopid": str(shop_id),
                    "limit": "20",
                    "offset": "0",
                    "filter": "0",
                    "type": "0",
                },
                headers=headers,
            )
            resp.raise_for_status()
            ratings_data = resp.json()
    except Exception as e:
        logger.warning(f"[ethnography] Shopee {market_code} ratings fetch failed: {e}")
        return None

    ratings = (ratings_data.get("data") or {}).get("ratings") or []
    text_chunks: list[str] = []
    for r in ratings:
        comment = (r.get("comment") or "").strip()
        stars = r.get("rating_star", "?")
        if comment and len(comment) > 10:
            text_chunks.append(f'[Shopee review, {stars}★] "{comment[:200]}"')

    if not text_chunks:
        logger.warning(f"[ethnography] Shopee {market_code}: no review text found for '{item_name}'")
        return None

    logger.info(f"[ethnography] Shopee {market_code}: {len(text_chunks)} reviews for '{item_name}'")
    return {
        "source": f"Shopee {market_code} ({item_name})",
        "post_count": len(text_chunks),
        "text": "\n".join(text_chunks[:30]),
    }


# ---------------------------------------------------------------------------
# Google Play Store crawl
# ---------------------------------------------------------------------------

_PLAY_STORE_APPS = {
    "ID": "com.gojek.app",
    "PH": "com.globe.gcash.android",
    "VN": "vn.momo.client",
}
_PLAY_STORE_APP_NAMES = {
    "ID": "Gojek",
    "PH": "GCash",
    "VN": "MoMo",
}
_PLAY_STORE_LOCALE = {
    "ID": "id",
    "PH": "en",
    "VN": "vi",
}


def _crawl_play_store_reviews(app_id: str, market_code: str) -> dict | None:
    """
    Fetch app reviews from Google Play Store for the market's primary consumer app:
        ID → Gojek, PH → GCash, VN → MoMo

    Primary approach: Play Store's internal batchexecute RPC endpoint (unofficial,
    reverse-engineered — same approach used by google-play-scraper and similar tools).

    Fallback: scrape review text from the app's Play Store HTML page.

    Both approaches fail gracefully (return None) if the response shape changes or
    the request is blocked. The pipeline continues with other sources.

    Note: vertical is NOT used here — these are fixed app IDs, not keyword-searched.
    """
    import re
    import urllib.parse

    app_name = _PLAY_STORE_APP_NAMES.get(market_code, app_id)
    lang = _PLAY_STORE_LOCALE.get(market_code, "en")
    text_chunks: list[str] = []

    # Primary: batchexecute POST
    try:
        inner = json.dumps([None, None, [2, 2, 40, None, None], app_id, None, lang])
        rpc = json.dumps([[["UsvDTd", inner, None, "generic"]]])
        body = f"f.req={urllib.parse.quote(rpc)}"

        with httpx.Client(timeout=_REQUEST_TIMEOUT) as client:
            resp = client.post(
                "https://play.google.com/_/PlayStoreUi/data/batchexecute",
                content=body,
                headers={
                    "User-Agent": _USER_AGENT,
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "*/*",
                },
            )
            resp.raise_for_status()
            text = resp.text

        # Strip Google's XSSI prefix
        if text.startswith(")]}'\n"):
            text = text[5:]

        outer = json.loads(text)
        inner_json = outer[0][2]
        payload = json.loads(inner_json)
        reviews = payload[0]

        for review in reviews:
            try:
                stars = review[2]
                review_text = str(review[4] or "").strip()
                if review_text and len(review_text) > 10:
                    text_chunks.append(f'[Play Store {app_name}, {stars}★] "{review_text[:200]}"')
            except (IndexError, TypeError):
                continue

    except Exception as e:
        logger.warning(f"[ethnography] Play Store batchexecute failed for {app_id}: {e}")

    # Fallback: HTML scraping
    if not text_chunks:
        try:
            url = f"https://play.google.com/store/apps/details?id={app_id}&hl=en&showAllReviews=true"
            with httpx.Client(timeout=_REQUEST_TIMEOUT, follow_redirects=True) as client:
                resp = client.get(url, headers={"User-Agent": _USER_AGENT})
                resp.raise_for_status()
                html = resp.text

            found = re.findall(r'<div jsname="sngebd"[^>]*>([^<]{10,500})</div>', html)
            for r in found[:40]:
                clean = r.strip()
                if clean:
                    text_chunks.append(f'[Play Store {app_name}] "{clean[:200]}"')

        except Exception as e:
            logger.warning(f"[ethnography] Play Store HTML fallback failed for {app_id}: {e}")

    if not text_chunks:
        logger.warning(f"[ethnography] Play Store: no reviews retrieved for {app_id} ({market_code})")
        return None

    logger.info(f"[ethnography] Play Store {app_name}: {len(text_chunks)} reviews")
    return {
        "source": f"Play Store {app_name} ({market_code})",
        "post_count": len(text_chunks),
        "text": "\n".join(text_chunks[:40]),
    }


# ---------------------------------------------------------------------------
# Per-market crawl functions
# ---------------------------------------------------------------------------

def _crawl_philippines(vertical: str | None = None) -> list[dict]:
    """
    Philippines crawl.

    Primary source: r/Philippines (3.5M members, confirmed active).
    Reddit is genuinely popular in PH due to high English literacy —
    less demographically biased than in ID or VN.

    Additional sources:
        - Shopee PH product reviews — real consumer purchase decisions and attitudes
        - Google Play Store reviews for GCash (com.globe.gcash.android) — most-used
          fintech app in PH; reviews surface digital behavior pain points and trust signals

    When vertical is provided, Reddit uses keyword search instead of top posts.
    Shopee searches using the vertical keyword; Play Store reviews are always for GCash.
    """
    batches: list[dict] = []

    reddit = _crawl_reddit_subreddit("Philippines", limit=25, vertical=vertical)
    if reddit:
        batches.append(reddit)

    shopee = _crawl_shopee_reviews("PH", vertical=vertical)
    if shopee:
        batches.append(shopee)

    play = _crawl_play_store_reviews(_PLAY_STORE_APPS["PH"], "PH")
    if play:
        batches.append(play)

    return batches


def _crawl_indonesia(vertical: str | None = None) -> list[dict]:
    """
    Indonesia crawl.

    Primary source: Kaskus (Indonesia's largest public forum, ~30M users,
    posts in Bahasa Indonesia — broad middle-class coverage).

    Supplement: r/indonesia (230K members). IMPORTANT: Reddit is banned in
    Indonesia. r/indonesia users are VPN-using, urban, tech-savvy — a
    self-selected demographic that does NOT represent the general population.
    Use as a supplement, not a primary signal.

    Additional sources:
        - Shopee ID product reviews — strong purchase-intent signal for this market
        - Google Play Store reviews for Gojek (com.gojek.app) — super-app covering
          ride-hailing, food, payments; reviews reflect broad urban consumer behavior

    Note: Kaskus is not vertically filtered — its HTML scraper uses category URLs,
    not a search API. Vertical filtering applies to Reddit and Shopee only.
    """
    batches: list[dict] = []

    kaskus = _crawl_kaskus()
    if kaskus:
        batches.append(kaskus)

    reddit = _crawl_reddit_subreddit("indonesia", limit=20, vertical=vertical)
    if reddit:
        batches.append(reddit)

    shopee = _crawl_shopee_reviews("ID", vertical=vertical)
    if shopee:
        batches.append(shopee)

    play = _crawl_play_store_reviews(_PLAY_STORE_APPS["ID"], "ID")
    if play:
        batches.append(play)

    return batches


def _crawl_vietnam(vertical: str | None = None) -> list[dict]:
    """
    Vietnam crawl.

    Primary source: r/VietNam (1.4M members, confirmed active, dual-language).
    Note: slug is "VietNam" (capital N) — verified from subreddit metadata.

    Skew note: this community has a meaningful expat presence and tends toward
    English. Local Vietnamese consumer signal is weaker here than Kaskus is
    for Indonesia. This is a known limitation for VN vs. the other markets.

    Additional sources:
        - Shopee VN product reviews — strongest supplementary signal for this market
          given the Reddit community's expat skew
        - Google Play Store reviews for MoMo (vn.momo.client) — dominant e-wallet in VN
    """
    batches: list[dict] = []

    reddit = _crawl_reddit_subreddit("VietNam", limit=25, vertical=vertical)
    if reddit:
        batches.append(reddit)

    shopee = _crawl_shopee_reviews("VN", vertical=vertical)
    if shopee:
        batches.append(shopee)

    play = _crawl_play_store_reviews(_PLAY_STORE_APPS["VN"], "VN")
    if play:
        batches.append(play)

    return batches


def _dispatch_crawl(market_code: str, vertical: str | None = None) -> list[dict]:
    """Route to the correct per-market crawl function."""
    if market_code == "PH":
        return _crawl_philippines(vertical=vertical)
    elif market_code == "ID":
        return _crawl_indonesia(vertical=vertical)
    elif market_code == "VN":
        return _crawl_vietnam(vertical=vertical)
    else:
        logger.warning(f"[ethnography] No crawl function for market '{market_code}'")
        return []


# ---------------------------------------------------------------------------
# LLM signal extraction
# ---------------------------------------------------------------------------

def _extract_signals(market_code: str, batches: list[dict], vertical: str | None = None) -> dict:
    """
    Send all crawled text to GPT-4o and extract structured behavioral signals.
    Returns a dict matching the signals_json schema, or raises on failure.

    The prompt instructs the model to:
    - Extract aggregate behavioral patterns, NOT individual opinions
    - Weight Kaskus (ID) content more heavily than Reddit due to demographic breadth
    - When vertical is set, focus signals on that product/service category
    - Return only valid JSON
    """
    if not batches:
        raise ValueError("No source batches to extract signals from")

    raw_content = ""
    for batch in batches:
        raw_content += f"\n\n--- SOURCE: {batch['source']} ({batch['post_count']} posts) ---\n"
        raw_content += batch["text"]

    market_labels = {"ID": "Indonesia", "PH": "Philippines", "VN": "Vietnam"}
    market_label = market_labels.get(market_code, market_code)

    system_prompt = (
        "You are a cultural anthropologist and consumer research analyst. "
        "Your job is to synthesise raw social media, forum, and product review content into "
        "structured behavioral signals about a consumer market. "
        "Extract AGGREGATE PATTERNS — not individual opinions. "
        "Every signal you extract must be grounded in the provided text. "
        "Do not invent signals not supported by the content. "
        "Return only valid JSON."
    )

    vertical_line = (
        f"Focus especially on signals relevant to the '{vertical}' vertical.\n\n"
        if vertical else ""
    )

    user_prompt = (
        f"Below is raw content crawled from public sources about the {market_label} consumer market. "
        f"{vertical_line}"
        f"Extract structured behavioral signals into the following JSON schema:\n\n"
        "{\n"
        f'  "market": "{market_code}",\n'
        '  "top_spending_categories": ["list of 3-6 categories consumers discuss spending on"],\n'
        '  "trusted_brands": ["list of 3-6 brands/services mentioned positively"],\n'
        '  "distrusted_brands": ["list of 2-4 brands/services mentioned negatively or with complaints"],\n'
        '  "dominant_anxieties": ["list of 3-6 recurring financial, social, or life anxieties"],\n'
        '  "aspirations": ["list of 3-6 things people aspire to or optimise for in life"],\n'
        '  "cultural_behaviors": ["list of 3-5 distinctive cultural or social behaviors visible in the content"],\n'
        '  "digital_habits": ["list of 3-5 specific apps, platforms, or digital behaviors mentioned"],\n'
        '  "price_sensitivity_signals": ["list of 3-5 signals about how price-conscious this market is"],\n'
        f'  "source_summary": "one sentence describing what was synthesised and approximate post count"\n'
        "}\n\n"
        "IMPORTANT:\n"
        "- If Kaskus content is present, weight it more heavily than Reddit for Indonesian signals "
        "(Reddit users in Indonesia are a self-selected VPN-using minority).\n"
        "- Each list must have at least 3 items. If the content does not support 3 items for a category, "
        "use what you can find and note the limitation in source_summary.\n"
        "- Do not hallucinate signals. Only include what is grounded in the provided text.\n\n"
        "RAW CONTENT:\n"
        f"{raw_content[:8000]}"  # bumped from 6000 — more sources now contributing
    )

    client = get_openai_client()
    response = client.chat.completions.create(
        model=settings.OPENAI_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
        max_tokens=1500,
    )

    return json.loads(response.choices[0].message.content)


# ---------------------------------------------------------------------------
# Quality gate
# ---------------------------------------------------------------------------

def _compute_quality_score(signals: dict) -> float:
    """
    Rules-based quality gate. Returns 0.0–1.0.
    A snapshot must score >= 0.5 to be activated.

    Scoring:
        +0.2 per required signal category that has >= 3 items (max 5 categories = 1.0)
        Any missing or null required key caps the score at 0.0.
    """
    for key in _REQUIRED_SIGNAL_KEYS:
        if key not in signals or not isinstance(signals.get(key), list):
            logger.warning(f"[ethnography] Quality gate: missing required key '{key}'")
            return 0.0

    score = 0.0
    for key in _REQUIRED_SIGNAL_KEYS:
        items = signals.get(key, [])
        if len(items) >= 3:
            score += 0.2

    return round(score, 2)


# ---------------------------------------------------------------------------
# Snapshot persistence
# ---------------------------------------------------------------------------

def _get_next_version(db, market_code: str) -> int:
    """Return the next version number for a market."""
    latest = db.execute(
        select(CulturalContextSnapshot)
        .where(CulturalContextSnapshot.market_code == market_code)
        .order_by(CulturalContextSnapshot.version.desc())
    ).scalars().first()
    return (latest.version + 1) if latest else 1


def _archive_active_snapshots(db, market_code: str) -> None:
    """Archive all currently active snapshots for a market."""
    active = db.execute(
        select(CulturalContextSnapshot)
        .where(CulturalContextSnapshot.market_code == market_code)
        .where(CulturalContextSnapshot.status == "active")
    ).scalars().all()
    for snap in active:
        snap.status = "archived"


# ---------------------------------------------------------------------------
# Public interface — refresh entry point
# ---------------------------------------------------------------------------

def refresh_market_context(market_code: str, vertical: str | None = None) -> None:
    """
    Main entry point. Called as a FastAPI background task.

    1. Crawl all configured sources for the market (Reddit, Shopee, Play Store)
    2. Extract structured signals via LLM
    3. Compute quality score
    4. If score >= 0.5: archive previous active snapshot, save new as active
    5. If score < 0.5: save as draft (silent failure — existing behaviour unchanged)

    When vertical is provided (e.g. "fintech", "beauty"), Reddit and Shopee crawls
    use that keyword to surface category-specific content. Stored in raw_sources
    as a _meta entry for operator visibility.
    """
    logger.info(
        f"[ethnography] Starting refresh for market '{market_code}'"
        + (f" (vertical: {vertical})" if vertical else "")
    )

    batches = _dispatch_crawl(market_code, vertical=vertical)
    raw_sources = [{"source": b["source"], "post_count": b["post_count"]} for b in batches]

    # Store vertical in raw_sources for operator inspection — no schema change needed
    if vertical:
        raw_sources.insert(0, {"source": "_meta", "vertical": vertical})

    if not batches:
        logger.warning(f"[ethnography] No data crawled for market '{market_code}' — aborting refresh")
        return

    try:
        signals = _extract_signals(market_code, batches, vertical=vertical)
    except Exception as e:
        logger.error(f"[ethnography] Signal extraction failed for '{market_code}': {e}")
        return

    quality_score = _compute_quality_score(signals)
    logger.info(f"[ethnography] Quality score for '{market_code}': {quality_score}")

    db = SessionLocal()
    try:
        version = _get_next_version(db, market_code)
        now = datetime.utcnow()

        if quality_score >= 0.5:
            _archive_active_snapshots(db, market_code)
            status = "active"
            activated_at = now
            logger.info(f"[ethnography] Activating snapshot v{version} for '{market_code}'")
        else:
            status = "draft"
            activated_at = None
            logger.warning(
                f"[ethnography] Quality gate not met for '{market_code}' "
                f"(score={quality_score}) — saved as draft, not activated"
            )

        snapshot = CulturalContextSnapshot(
            id=uuid.uuid4(),
            market_code=market_code,
            status=status,
            version=version,
            signals_json=signals,
            raw_sources=raw_sources,
            quality_score=quality_score,
            created_at=now,
            activated_at=activated_at,
        )
        db.add(snapshot)
        db.commit()
        logger.info(f"[ethnography] Snapshot saved: market={market_code} status={status} v={version}")
    except Exception as e:
        logger.error(f"[ethnography] Failed to save snapshot for '{market_code}': {e}")
        db.rollback()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Public interface — context injection helpers
# ---------------------------------------------------------------------------

def get_cultural_context_block(location: str) -> str | None:
    """
    Called from persona_generator.py. Returns a formatted context block
    for injection into the persona generation prompt, or None if:
    - The location is not in a supported market (ID/PH/VN)
    - No active snapshot exists for that market
    - Any DB error occurs (fail-safe: never block persona generation)

    The returned block is clearly labelled as soft context so the LLM
    does not treat it as hard constraints.
    """
    try:
        market_code = _detect_market(location)
        if not market_code:
            return None

        db = SessionLocal()
        try:
            snapshot = db.execute(
                select(CulturalContextSnapshot)
                .where(CulturalContextSnapshot.market_code == market_code)
                .where(CulturalContextSnapshot.status == "active")
                .order_by(CulturalContextSnapshot.version.desc())
            ).scalars().first()
        finally:
            db.close()

        if not snapshot or not snapshot.signals_json:
            return None

        signals = snapshot.signals_json
        market_labels = {"ID": "Indonesia", "PH": "Philippines", "VN": "Vietnam"}
        market_label = market_labels.get(market_code, market_code)

        def fmt_list(key: str) -> str:
            items = signals.get(key, [])
            return ", ".join(str(i) for i in items) if items else "N/A"

        block = (
            f"=== BEHAVIORAL SIGNALS: {market_label.upper()} MARKET (v{snapshot.version}) ===\n"
            "Synthesised from recent public conversations in this market. "
            "Treat as soft behavioral context — use to make personas feel grounded "
            "in real local life, not as rigid constraints.\n\n"
            f"Top spending categories: {fmt_list('top_spending_categories')}\n"
            f"Trusted brands/services: {fmt_list('trusted_brands')}\n"
            f"Distrusted brands: {fmt_list('distrusted_brands')}\n"
            f"Dominant anxieties: {fmt_list('dominant_anxieties')}\n"
            f"Aspirations: {fmt_list('aspirations')}\n"
            f"Cultural behaviors: {fmt_list('cultural_behaviors')}\n"
            f"Digital habits: {fmt_list('digital_habits')}\n"
            f"Price sensitivity: {fmt_list('price_sensitivity_signals')}\n"
            f"Source: {signals.get('source_summary', 'N/A')}\n"
            "=== END BEHAVIORAL SIGNALS ===\n"
        )

        logger.info(
            f"[ethnography] Injecting {market_code} cultural context (v{snapshot.version}) "
            f"into persona generation for location: {location!r}"
        )
        return block

    except Exception as e:
        logger.warning(f"[ethnography] get_cultural_context_block failed for '{location}': {e}")
        return None  # Never block persona generation


def should_refresh(location: str) -> bool:
    """
    Returns True if this location maps to a supported market AND:
    - No active snapshot exists, OR
    - The active snapshot is older than _STALENESS_DAYS

    Called from persona_groups.py router to decide whether to queue a
    background refresh alongside persona generation.
    """
    try:
        market_code = _detect_market(location)
        if not market_code:
            return False

        db = SessionLocal()
        try:
            snapshot = db.execute(
                select(CulturalContextSnapshot)
                .where(CulturalContextSnapshot.market_code == market_code)
                .where(CulturalContextSnapshot.status == "active")
                .order_by(CulturalContextSnapshot.version.desc())
            ).scalars().first()
        finally:
            db.close()

        if not snapshot:
            return True

        age = datetime.utcnow() - snapshot.created_at
        return age > timedelta(days=_STALENESS_DAYS)

    except Exception as e:
        logger.warning(f"[ethnography] should_refresh check failed for '{location}': {e}")
        return False  # Don't trigger refresh on error

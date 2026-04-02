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
from openai import OpenAI
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

def _crawl_reddit_subreddit(subreddit: str, limit: int = 25) -> dict | None:
    """
    Fetch top posts + comments from a subreddit via Reddit's public JSON API.
    No credentials required. Returns {source, post_count, text} or None on failure.

    NOTE: The subreddit slug is case-sensitive for Reddit's API.
    Verified slugs: Philippines, indonesia, VietNam
    """
    headers = {"User-Agent": _USER_AGENT}
    url = f"https://www.reddit.com/r/{subreddit}/top.json"
    params = {"t": "month", "limit": str(limit)}

    try:
        with httpx.Client(timeout=_REQUEST_TIMEOUT) as client:
            resp = client.get(url, params=params, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except Exception as e:
        logger.warning(f"[ethnography] Reddit crawl failed for r/{subreddit}: {e}")
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
        logger.warning(f"[ethnography] r/{subreddit}: no posts retrieved")
        return None

    logger.info(f"[ethnography] r/{subreddit}: retrieved {len(posts)} posts")
    return {
        "source": f"r/{subreddit}",
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
# Per-market crawl functions
# ---------------------------------------------------------------------------

def _crawl_philippines() -> list[dict]:
    """
    Philippines crawl.

    Primary source: r/Philippines (3.5M members, confirmed active).
    Reddit is genuinely popular in PH due to high English literacy —
    less demographically biased than in ID or VN.

    Future sources (not yet implemented):
        - Shopee PH product reviews (requires product ID navigation)
        - Google Play Store reviews for GCash (com.globe.gcash.android)
          — requires dynamic rendering workaround or unofficial API
    """
    batches: list[dict] = []

    reddit = _crawl_reddit_subreddit("Philippines", limit=25)
    if reddit:
        batches.append(reddit)

    return batches


def _crawl_indonesia() -> list[dict]:
    """
    Indonesia crawl.

    Primary source: Kaskus (Indonesia's largest public forum, ~30M users,
    posts in Bahasa Indonesia — broad middle-class coverage).

    Supplement: r/indonesia (230K members). IMPORTANT: Reddit is banned in
    Indonesia. r/indonesia users are VPN-using, urban, tech-savvy — a
    self-selected demographic that does NOT represent the general population.
    Use as a supplement, not a primary signal.

    Future sources (not yet implemented):
        - Shopee ID product reviews
        - Google Play Store reviews for Gojek (com.gojek.app)
    """
    batches: list[dict] = []

    kaskus = _crawl_kaskus()
    if kaskus:
        batches.append(kaskus)

    reddit = _crawl_reddit_subreddit("indonesia", limit=20)
    if reddit:
        batches.append(reddit)

    return batches


def _crawl_vietnam() -> list[dict]:
    """
    Vietnam crawl.

    Primary source: r/VietNam (1.4M members, confirmed active, dual-language).
    Note: slug is "VietNam" (capital N) — verified from subreddit metadata.

    Skew note: this community has a meaningful expat presence and tends toward
    English. Local Vietnamese consumer signal is weaker here than Kaskus is
    for Indonesia. This is a known limitation for VN vs. the other markets.

    Future sources (not yet implemented):
        - Shopee VN product reviews (strongest signal for this market)
        - Google Play Store reviews for MoMo (vn.momo.client)
    """
    batches: list[dict] = []

    reddit = _crawl_reddit_subreddit("VietNam", limit=25)
    if reddit:
        batches.append(reddit)

    return batches


def _dispatch_crawl(market_code: str) -> list[dict]:
    """Route to the correct per-market crawl function."""
    if market_code == "PH":
        return _crawl_philippines()
    elif market_code == "ID":
        return _crawl_indonesia()
    elif market_code == "VN":
        return _crawl_vietnam()
    else:
        logger.warning(f"[ethnography] No crawl function for market '{market_code}'")
        return []


# ---------------------------------------------------------------------------
# LLM signal extraction
# ---------------------------------------------------------------------------

def _extract_signals(market_code: str, batches: list[dict]) -> dict:
    """
    Send all crawled text to GPT-4o and extract structured behavioral signals.
    Returns a dict matching the signals_json schema, or raises on failure.

    The prompt instructs the model to:
    - Extract aggregate behavioral patterns, NOT individual opinions
    - Weight Kaskus (ID) content more heavily than Reddit due to demographic breadth
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
        "Your job is to synthesise raw social media and forum content into "
        "structured behavioral signals about a consumer market. "
        "Extract AGGREGATE PATTERNS — not individual opinions. "
        "Every signal you extract must be grounded in the provided text. "
        "Do not invent signals not supported by the content. "
        "Return only valid JSON."
    )

    user_prompt = (
        f"Below is raw content crawled from public sources about the {market_label} consumer market. "
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
        f"{raw_content[:6000]}"  # cap to manage token cost
    )

    client = OpenAI(api_key=settings.openai_api_key)
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

def refresh_market_context(market_code: str) -> None:
    """
    Main entry point. Called as a FastAPI background task.

    1. Crawl all configured sources for the market
    2. Extract structured signals via LLM
    3. Compute quality score
    4. If score >= 0.5: archive previous active snapshot, save new as active
    5. If score < 0.5: save as draft (silent failure — existing behaviour unchanged)
    """
    logger.info(f"[ethnography] Starting refresh for market '{market_code}'")

    batches = _dispatch_crawl(market_code)
    raw_sources = [{"source": b["source"], "post_count": b["post_count"]} for b in batches]

    if not batches:
        logger.warning(f"[ethnography] No data crawled for market '{market_code}' — aborting refresh")
        return

    try:
        signals = _extract_signals(market_code, batches)
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

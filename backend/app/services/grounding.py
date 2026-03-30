"""
grounding.py
Loads country-level demographic data from grounding_data.json and matches
a location string (e.g. "Metro Manila, Philippines") to the right country entry.

To add a new country:
  1. Add a key to grounding_data.json using the _template.
  2. Add location keywords to _LOCATION_MAP below.
  3. Optionally run scripts/fetch_world_bank.py to populate numeric fields.
"""
from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_DATA_FILE = Path(__file__).parent.parent / "data" / "grounding_data.json"

# ---------------------------------------------------------------------------
# Location → country key mapping
# Add keywords (lowercase) that should map to a country key in grounding_data.json
# ---------------------------------------------------------------------------

_LOCATION_MAP: dict[str, str] = {
    # Philippines
    "philippines": "philippines",
    "pilipinas": "philippines",
    "ph": "philippines",
    "manila": "philippines",
    "metro manila": "philippines",
    "ncr": "philippines",
    "cebu": "philippines",
    "davao": "philippines",
    "quezon city": "philippines",
    "makati": "philippines",
    "pasig": "philippines",
    "taguig": "philippines",
    "bgc": "philippines",
    "ortigas": "philippines",
    "mindanao": "philippines",
    "visayas": "philippines",
    "luzon": "philippines",

    # Indonesia
    "indonesia": "indonesia",
    "jakarta": "indonesia",
    "bali": "indonesia",
    "surabaya": "indonesia",
    "bandung": "indonesia",
    "medan": "indonesia",
    "semarang": "indonesia",
    "jogja": "indonesia",
    "yogyakarta": "indonesia",
    "jabodetabek": "indonesia",

    # Singapore
    "singapore": "singapore",
    "sg": "singapore",
    "orchard": "singapore",
    "jurong": "singapore",
    "woodlands": "singapore",

    # Malaysia
    "malaysia": "malaysia",
    "kuala lumpur": "malaysia",
    "kl": "malaysia",
    "penang": "malaysia",
    "johor": "malaysia",
    "my": "malaysia",

    # Vietnam
    "vietnam": "vietnam",
    "viet nam": "vietnam",
    "ho chi minh": "vietnam",
    "saigon": "vietnam",
    "hanoi": "vietnam",
    "da nang": "vietnam",
    "hoi an": "vietnam",

    # Thailand
    "thailand": "thailand",
    "bangkok": "thailand",
    "chiang mai": "thailand",
    "phuket": "thailand",
    "pattaya": "thailand",
    "isan": "thailand",

    # United States
    "united states": "usa",
    "usa": "usa",
    "u.s.": "usa",
    "us": "usa",
    "new york": "usa",
    "los angeles": "usa",
    "california": "usa",

    # United Kingdom
    "united kingdom": "uk",
    "uk": "uk",
    "britain": "uk",
    "england": "uk",
    "london": "uk",

    # India
    "india": "india",
    "mumbai": "india",
    "delhi": "india",
    "bangalore": "india",
    "chennai": "india",
}


# ---------------------------------------------------------------------------
# Data loader
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _load_data() -> dict[str, Any]:
    try:
        with open(_DATA_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load grounding_data.json: {e}")
        return {}


def get_country_key(location: str) -> str | None:
    """
    Map a freeform location string to a grounding_data.json country key.
    Returns None if no match found.
    """
    if not location:
        return None
    loc_lower = location.lower().strip()

    # Direct match
    if loc_lower in _LOCATION_MAP:
        return _LOCATION_MAP[loc_lower]

    # Substring match — check if any keyword appears in the location string
    for keyword, country_key in _LOCATION_MAP.items():
        if keyword in loc_lower:
            return country_key

    return None


def get_grounding_stats(location: str) -> dict[str, Any] | None:
    """
    Return the full grounding stats dict for a location, or None if not found.
    Strips internal metadata keys (starting with _).
    """
    country_key = get_country_key(location)
    if not country_key:
        logger.debug(f"No grounding data found for location: '{location}'")
        return None

    data = _load_data()
    stats = data.get(country_key)
    if not stats:
        logger.debug(f"Country key '{country_key}' not in grounding_data.json")
        return None

    # Strip metadata keys
    return {k: v for k, v in stats.items() if not k.startswith("_")}


def format_grounding_context(location: str) -> tuple[str, list[str]]:
    """
    Returns (context_text, source_citations) for injection into a GPT prompt.
    context_text is a compact, human-readable summary of the country stats.
    source_citations is a list of source strings for data_source_references.

    Returns ("", []) if no data available for the location.
    """
    stats = get_grounding_stats(location)
    if not stats:
        return "", []

    lines: list[str] = []

    lines.append(f"=== REAL DEMOGRAPHIC DATA FOR THIS MARKET ===")
    lines.append(f"Use these statistics as hard anchors. Do not contradict them.\n")

    if stats.get("population"):
        lines.append(f"Population: {stats['population']:,}")
    if stats.get("median_age"):
        lines.append(f"Median age: {stats['median_age']}")
    if stats.get("gdp_per_capita_usd"):
        lines.append(f"GDP per capita: USD {stats['gdp_per_capita_usd']:,}")
    if stats.get("urban_population_pct"):
        lines.append(f"Urban population: {int(stats['urban_population_pct'] * 100)}%")

    # Income distribution
    inc = stats.get("income_distribution", {})
    if any(v for v in inc.values() if isinstance(v, float)):
        lines.append("\nIncome distribution:")
        for band, pct in inc.items():
            if band != "description" and isinstance(pct, float):
                lines.append(f"  - {band.replace('_', '-').title()}: {int(pct * 100)}% of households")

    # Employment
    emp = stats.get("employment", {})
    if emp.get("top_occupations"):
        lines.append("\nCommon occupations:")
        for occ in emp["top_occupations"][:6]:
            lines.append(f"  - {occ}")

    # Digital
    dig = stats.get("digital", {})
    if dig.get("internet_penetration_pct"):
        lines.append(f"\nInternet penetration: {int(dig['internet_penetration_pct'] * 100)}%")
    if dig.get("social_media_users_pct"):
        lines.append(f"Social media users: {int(dig['social_media_users_pct'] * 100)}%")
    if dig.get("avg_daily_social_media_hours"):
        lines.append(f"Avg daily social media use: {dig['avg_daily_social_media_hours']} hours")
    if dig.get("top_platforms_ranked"):
        lines.append("Top platforms: " + ", ".join(
            p.split(" (")[0] for p in dig["top_platforms_ranked"][:4]
        ))
    if dig.get("top_ecommerce_platforms"):
        lines.append("Top e-commerce: " + ", ".join(dig["top_ecommerce_platforms"]))

    # Consumer behavior notes
    cb = stats.get("consumer_behavior", {})
    if cb.get("notes"):
        lines.append("\nKey consumer behavior insights:")
        for note in cb["notes"][:5]:
            lines.append(f"  - {note}")

    # Regional notes — find matching region
    regional = stats.get("regional_notes", {})
    if regional:
        loc_lower = location.lower()
        for region_key, region_note in regional.items():
            if any(word in loc_lower for word in region_key.lower().split("_")):
                lines.append(f"\nRegional context ({region_key.replace('_', ' ')}): {region_note}")
                break

    lines.append("\n=== END DEMOGRAPHIC DATA ===\n")

    # Source citations
    raw_sources = stats.get("_sources", [])  # won't be present after strip, load raw
    data = _load_data()
    country_key = get_country_key(location)
    raw_sources = data.get(country_key, {}).get("_sources", [])

    return "\n".join(lines), raw_sources

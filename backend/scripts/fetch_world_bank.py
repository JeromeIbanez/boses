"""
fetch_world_bank.py
Fetches key demographic indicators from the World Bank free API and updates
grounding_data.json with fresh figures.

Usage:
    python scripts/fetch_world_bank.py                  # update all countries
    python scripts/fetch_world_bank.py --country PH     # update one country

The World Bank API is completely free — no API key required.

Adding a new country:
    1. Add a row to COUNTRY_CONFIGS below.
    2. Add the country entry to grounding_data.json using the _template.
    3. Run this script.
"""

import argparse
import json
import ssl
import sys
from pathlib import Path
import urllib.request
import urllib.error

# macOS doesn't ship with root CA certs for Python — bypass verification for this utility script
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

DATA_FILE = Path(__file__).parent.parent / "app" / "data" / "grounding_data.json"

# ---------------------------------------------------------------------------
# World Bank indicator codes we care about
# Full list: https://data.worldbank.org/indicator
# ---------------------------------------------------------------------------
INDICATORS = {
    "population":          "SP.POP.TOTL",
    "median_age":          "SP.POP.MEDI.AE.IN",   # median age (some gaps — fallback to manual)
    "gdp_per_capita_usd":  "NY.GDP.PCAP.CD",
    "urban_population_pct":"SP.URB.TOTL.IN.ZS",   # returns as percentage 0–100
    "internet_pct":        "IT.NET.USER.ZS",       # returns as percentage 0–100
    "age_0_14_pct":        "SP.POP.0014.TO.ZS",
    "age_15_64_pct":       "SP.POP.1564.TO.ZS",
    "age_65_plus_pct":     "SP.POP.65UP.TO.ZS",
    "literacy_rate":       "SE.ADT.LITR.ZS",
    "unemployment_rate":   "SL.UEM.TOTL.ZS",
}

# ---------------------------------------------------------------------------
# Country config: grounding_data.json key → World Bank ISO2 code
# Add new countries here.
# ---------------------------------------------------------------------------
COUNTRY_CONFIGS = {
    "philippines": "PH",
    "indonesia":   "ID",
    "singapore":   "SG",
    "malaysia":    "MY",
    "vietnam":     "VN",
    "thailand":    "TH",
    "usa":         "US",
    "uk":          "GB",
    "india":       "IN",
}


def fetch_indicator(country_code: str, indicator_code: str) -> float | None:
    """Fetch the most recent value for a World Bank indicator."""
    url = (
        f"https://api.worldbank.org/v2/country/{country_code}/indicator/{indicator_code}"
        f"?format=json&mrv=1&per_page=1"
    )
    try:
        with urllib.request.urlopen(url, timeout=10, context=_SSL_CTX) as resp:
            raw = json.loads(resp.read())
        if len(raw) < 2 or not raw[1]:
            return None
        entry = raw[1][0]
        return entry.get("value")
    except (urllib.error.URLError, Exception) as e:
        print(f"  WARNING: Could not fetch {indicator_code} for {country_code}: {e}")
        return None


def update_country(data: dict, country_key: str, iso2: str) -> bool:
    """Fetch World Bank data for one country and update the data dict."""
    if country_key not in data:
        print(f"  SKIP: '{country_key}' not in grounding_data.json — add it first using _template")
        return False

    print(f"  Fetching World Bank data for {country_key} ({iso2})...")
    entry = data[country_key]

    # Population
    pop = fetch_indicator(iso2, INDICATORS["population"])
    if pop is not None:
        entry["population"] = int(pop)
        print(f"    population: {entry['population']:,}")

    # GDP per capita
    gdp = fetch_indicator(iso2, INDICATORS["gdp_per_capita_usd"])
    if gdp is not None:
        entry["gdp_per_capita_usd"] = round(gdp)
        print(f"    gdp_per_capita_usd: {entry['gdp_per_capita_usd']:,}")

    # Urban population
    urban = fetch_indicator(iso2, INDICATORS["urban_population_pct"])
    if urban is not None:
        entry["urban_population_pct"] = round(urban / 100, 3)
        print(f"    urban_population_pct: {entry['urban_population_pct']}")

    # Internet penetration (stored in digital sub-key)
    internet = fetch_indicator(iso2, INDICATORS["internet_pct"])
    if internet is not None:
        if "digital" not in entry:
            entry["digital"] = {}
        entry["digital"]["internet_penetration_pct"] = round(internet / 100, 3)
        print(f"    internet_penetration_pct: {entry['digital']['internet_penetration_pct']}")

    # Age distribution
    age_0_14 = fetch_indicator(iso2, INDICATORS["age_0_14_pct"])
    age_15_64 = fetch_indicator(iso2, INDICATORS["age_15_64_pct"])
    age_65   = fetch_indicator(iso2, INDICATORS["age_65_plus_pct"])
    if all(v is not None for v in [age_0_14, age_15_64, age_65]):
        entry["age_distribution"] = {
            "0_14":    round(age_0_14 / 100, 3),
            "15_64":   round(age_15_64 / 100, 3),
            "65_plus": round(age_65 / 100, 3),
        }
        print(f"    age_distribution: {entry['age_distribution']}")

    # Literacy
    literacy = fetch_indicator(iso2, INDICATORS["literacy_rate"])
    if literacy is not None:
        if "education" not in entry:
            entry["education"] = {}
        entry["education"]["literacy_rate"] = round(literacy / 100, 3)
        print(f"    literacy_rate: {entry['education']['literacy_rate']}")

    # Unemployment
    unemp = fetch_indicator(iso2, INDICATORS["unemployment_rate"])
    if unemp is not None:
        if "employment" not in entry:
            entry["employment"] = {}
        entry["employment"]["unemployment_rate"] = round(unemp / 100, 3)
        print(f"    unemployment_rate: {entry['employment']['unemployment_rate']}")

    return True


def main():
    parser = argparse.ArgumentParser(description="Refresh World Bank data in grounding_data.json")
    parser.add_argument("--country", help="Country key to update (e.g. philippines). Default: all.")
    args = parser.parse_args()

    print(f"Loading {DATA_FILE}...")
    with open(DATA_FILE, "r") as f:
        data = json.load(f)

    if args.country:
        targets = {args.country: COUNTRY_CONFIGS.get(args.country)}
        if not targets[args.country]:
            print(f"ERROR: '{args.country}' not in COUNTRY_CONFIGS. Add it to the script first.")
            sys.exit(1)
    else:
        targets = COUNTRY_CONFIGS

    for country_key, iso2 in targets.items():
        update_country(data, country_key, iso2)

    # Update last_updated timestamp
    from datetime import date
    data["_meta"]["last_updated"] = str(date.today())

    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

    print(f"\nDone. {DATA_FILE} updated.")


if __name__ == "__main__":
    main()

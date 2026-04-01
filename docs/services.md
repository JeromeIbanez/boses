_Last updated: 2026-04-01_

# Services

The service layer lives in `backend/app/services/`. All AI calls use `gpt-4o` via the OpenAI Python SDK.

## Service Overview

| File | Primary Function(s) | Uses LLM | Notes |
|---|---|---|---|
| `simulation_engine.py` | `run_simulation()` | Yes | Concept test pipeline |
| `idi_engine.py` | `run_idi_ai()`, `generate_idi_report_from_messages()` | Yes | IDI pipeline |
| `persona_generator.py` | `generate_personas()` | Yes | Two-pass generation |
| `briefing_extractor.py` | `extract_text()` | No | PDF + image parsing |
| `grounding.py` | `format_grounding_context()` | No | Market stats from JSON |
| `reddit_grounding.py` | `fetch_reddit_signals()` | No | Reddit public API |
| `library_matcher.py` | `find_library_matches()`, `save_persona_to_library()` | No | Scoring-based matching |

---

## Simulation Engine (`simulation_engine.py`)

Routes to the correct engine based on `simulation.simulation_type`.

**Concept test flow:**
1. Load all personas in the group
2. Build a system prompt with persona profile + grounding context
3. Build a user prompt with briefing text + question
4. Call `gpt-4o` per persona at `temperature=0.9`
5. Parse structured JSON response into `SimulationResult` (individual)
6. After all personas: generate aggregate at `temperature=0.7`
7. Set `simulation.status = "complete"`

Failed personas are tracked individually — a single failure does not abort the run. If all personas fail, status is set to `"failed"`.

---

## IDI Engine (`idi_engine.py`)

**AI-automated IDI (`run_idi_ai`):**
1. Parse script questions from `idi_script_text`
2. For each persona: conduct a multi-turn conversation using script questions
3. Generate a per-persona transcript and structured analysis
4. Store results as `SimulationResult` rows with `result_type="idi_individual"` and `"idi_aggregate"`
5. Progress tracked in `simulation.progress` JSONB

**Manual IDI report (`generate_idi_report_from_messages`):**
1. Load existing `IDIMessage` rows for the simulation
2. Format transcript from message history
3. Call `gpt-4o` to generate a structured analysis report
4. Save as `SimulationResult`

Key helpers:
- `_build_persona_system_prompt(persona, briefing_text)` — constructs persona character prompt
- `_parse_questions(script_text)` — splits script into individual interview questions
- `_analyse_persona_transcript(client, persona, transcript)` — generates analysis dict

---

## Persona Generator (`persona_generator.py`)

Uses a pluggable `PersonaDataSource` abstract base class. Currently active: `SyntheticPersonaSource`.

**Two-pass generation:**
1. **Pass 1** (skeleton): Generate N persona stubs with demographic fields at `temperature=1.2`
   - Includes grounding context from `grounding.py`
   - Includes Reddit signals from `reddit_grounding.py`
2. **Pass 2** (expansion): Expand each stub to a full rich profile at `temperature=1.0`

**Library integration:**
- Before generating synthetically, `find_library_matches()` checks for matching library personas
- Matches above the 0.70 threshold are used as-is; remaining slots are filled synthetically
- New synthetic personas are saved back to the library via `save_persona_to_library()`

Updates `persona_group.generation_status`: `"pending"` → `"generating"` → `"complete"` (or `"failed"`)

---

## Briefing Extractor (`briefing_extractor.py`)

Extracts readable text from uploaded briefing files.

| File Type | Handler | Library |
|---|---|---|
| `pdf` | Page-by-page text extraction | `pdfminer.six` |
| `text` | Direct UTF-8 read | stdlib |
| `image` | Returns placeholder message | `Pillow` (future OCR) |
| `.docx` | Word document text extraction | `python-docx` |

---

## Grounding Service (`grounding.py`)

Provides market statistics context for persona generation prompts.

- Data source: `/backend/app/data/grounding_data.json` — pre-loaded JSON with country-level market data
- `get_country_key(location)` — maps location strings to country keys (e.g. "Manila" → "philippines")
- `get_grounding_stats(location)` → raw stats dict or `None`
- `format_grounding_context(location)` → `(context_text, source_citations)` tuple injected into GPT prompts

---

## Reddit Grounding (`reddit_grounding.py`)

Fetches real social listening signals from Reddit to enrich persona generation.

- Uses Reddit's public JSON API (no authentication required)
- Location → subreddit mappings: Philippines, Indonesia, Singapore, Malaysia, Vietnam, Thailand, USA, UK, India
- **6-hour TTL cache** to avoid redundant API calls
- `fetch_reddit_signals(location, topic_context)` → formatted context string
  - Fetches top posts from relevant subreddits
  - Extracts top 3 comments per post
  - Formats as a structured context block injected into persona generation prompts

---

## Library Matcher (`library_matcher.py`)

Scores library personas against a new persona group to find reusable matches.

**Scoring weights:**

| Factor | Weight |
|---|---|
| Age range overlap | 35% |
| Gender | 20% |
| Income level | 20% |
| Location | 15% |
| Occupation | 10% |

**Threshold:** 0.70 — personas above this score are used directly from the library.

- `score_persona(library_persona, group)` → float 0.0–1.0
- `find_library_matches(db, group, limit=50)` → ranked list of `(LibraryPersona, score)` tuples
- `save_persona_to_library(db, persona, match_score, existing_library_id)` → creates or updates a `LibraryPersona` and `PersonaLibraryLink`

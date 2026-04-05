_Last updated: 2026-04-05_

# Services

The service layer lives in `backend/app/services/`. All AI calls use `gpt-4o` via the OpenAI Python SDK.

## Service Overview

| File | Primary Function(s) | Uses LLM | Notes |
|---|---|---|---|
| `simulation_engine.py` | `run_simulation()` | Yes | Routes to correct engine by type |
| `idi_engine.py` | `run_idi_ai()`, `generate_idi_report_from_messages()` | Yes | IDI pipeline |
| `focus_group_engine.py` | `run_focus_group()` | Yes | 2-round group discussion with moderator |
| `survey_engine.py` | `run_survey()` | Yes | Per-persona survey fill-out |
| `conjoint_engine.py` | `run_conjoint()` | Yes | Choice-based conjoint analysis |
| `persona_generator.py` | `generate_personas()` | Yes | Two-pass generation with library + ethnography context |
| `ethnography_service.py` | `refresh_market_context()`, `get_cultural_context_block()` | Yes | SEA web ethnography pipeline |
| `avatar_service.py` | `generate_avatars_for_group()` | Yes | DALL-E 3 persona portrait generation |
| `benchmarking_service.py` | `compute_convergence()`, `score_reproducibility_study()` | No | Cross-simulation trust scoring |
| `briefing_extractor.py` | `extract_text()` | No | PDF + image parsing |
| `grounding.py` | `format_grounding_context()` | No | Market stats from JSON |
| `reddit_grounding.py` | `fetch_reddit_signals()` | No | Reddit public API (6h TTL cache) |
| `library_matcher.py` | `find_library_matches()`, `save_persona_to_library()` | No | Scoring-based matching |
| `prompts.py` | — | No | Centralised prompt templates for all engines |

---

## Simulation Engine (`simulation_engine.py`)

Routes to the correct engine based on `simulation.simulation_type`.

| Type | Engine called |
|---|---|
| `concept_test` | Internal concept-test pipeline |
| `idi_ai` | `idi_engine.run_idi_ai()` |
| `idi_manual` | (no background task; driven by chat messages endpoint) |
| `focus_group` | `focus_group_engine.run_focus_group()` |
| `survey` | `survey_engine.run_survey()` |
| `conjoint` | `conjoint_engine.run_conjoint()` |

**Concept test flow:**
1. Load all personas in the group
2. Build a system prompt with persona profile + grounding context
3. Build a user prompt with briefing text + question
4. Call `gpt-4o` per persona at `temperature=0.9`
5. Parse structured JSON response into `SimulationResult` (individual)
6. After all personas: generate aggregate at `temperature=0.7`
7. Set `simulation.status = "complete"`
8. Call `maybe_score_reproducibility()` if this run is part of a study

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

## Focus Group Engine (`focus_group_engine.py`)

**Flow:**
1. **Moderator opening** — LLM generates an opening statement + first question
2. **Round 1** — each persona gives an initial response at `temperature=0.9`
3. **Moderator bridge** — LLM synthesises Round 1 and poses a follow-up question
4. **Round 2** — each persona reacts to other participants' Round 1 statements
5. **Aggregate report** — LLM extracts moderator summary, consensus themes, disagreements, sentiment distribution, and recommendations
6. Stores `focus_group_individual` and `focus_group_aggregate` `SimulationResult` rows

Round 2 is skipped if only one persona succeeded in Round 1. Individual Round 2 failures are non-fatal.

---

## Survey Engine (`survey_engine.py`)

**Flow:**
1. Load parsed `survey_schema` from simulation (uploaded via `/survey` endpoint)
2. For each persona: one LLM call fills out all questions at `temperature=0.85`
   - Question types: `likert` (numeric rating), `multiple_choice` (one option), `open_ended` (free text)
3. Aggregate: compute distributions for likert/MC, call LLM for open-ended theme extraction
4. Generate overall executive summary + recommendations via LLM
5. Store `survey_individual` and `survey_aggregate` results

---

## Conjoint Engine (`conjoint_engine.py`)

Choice-Based Conjoint (CBC) analysis using forced-choice tasks.

**Flow:**
1. Generate N choice-set pairs from attribute/level design (stored in `survey_schema`)
2. For each persona: send all tasks in one LLM call at `temperature=0.85`; parse JSON choices
3. Compute per-level part-worth utilities and attribute importance per persona
4. Aggregate: average part-worths, run first-choice market share simulation on 3 hypothetical profiles
5. Generate LLM narrative (executive summary + recommendations)
6. Store `conjoint_individual` and `conjoint_aggregate` results

**Part-worth computation** (no scipy):
- raw_score[attr][level] = chosen_count / (chosen + rejected)
- Zero-center within each attribute → part-worth
- importance = (max_pw − min_pw) normalised to sum to 100%

---

## Persona Generator (`persona_generator.py`)

Uses a pluggable `PersonaDataSource` abstract base class. Currently active: `SyntheticPersonaSource`.

**Two-pass generation:**
1. **Pass 1** (skeleton): Generate N persona stubs with demographic + psychographic fields at `temperature=1.2`
   - Includes grounding context from `grounding.py`
   - Includes Reddit signals from `reddit_grounding.py`
   - Includes cultural context block from `ethnography_service.get_cultural_context_block()` (if active snapshot exists for the market)
2. **Pass 2** (expansion): Expand each stub to a full rich profile at `temperature=1.0`
3. **Avatars**: After text generation, `avatar_service.generate_avatars_for_group()` runs concurrently via thread pool

**Library integration:**
- Before generating synthetically, `find_library_matches()` checks for matching library personas
- Matches above the 0.70 threshold are used as-is; remaining slots are filled synthetically
- New synthetic personas are saved back to the library via `save_persona_to_library()`

Updates `persona_group.generation_status`: `"pending"` → `"generating"` → `"complete"` (or `"failed"`)

---

## Ethnography Service (`ethnography_service.py`)

Automated web ethnography pipeline for SEA markets (ID, PH, VN).

**Sources by market:**
| Market | Primary Source | Supplement |
|---|---|---|
| PH | r/Philippines (Reddit) | — |
| ID | Kaskus forum (Bahasa ID) | r/indonesia (VPN-using minority — used as supplement only) |
| VN | r/VietNam (Reddit) | — |

**Pipeline (`refresh_market_context`):**
1. Crawl configured sources for the market
2. Extract structured behavioral signals via `gpt-4o` (LLM, `temperature=0.3`)
3. Compute quality score (rules-based, 0.0–1.0; threshold 0.5 to activate)
4. If quality ≥ 0.5: archive previous active snapshot, save new `CulturalContextSnapshot` as `active`
5. If quality < 0.5: save as `draft` (silent failure, existing behaviour unchanged)

**Staleness check (`should_refresh`):** Returns true if no active snapshot exists OR snapshot is older than 30 days. Called lazily from persona_groups router after each generate request.

**Context injection (`get_cultural_context_block`):** Called from `persona_generator.py`. Returns a formatted text block with market signals (spending categories, trusted brands, anxieties, aspirations, digital habits, etc.) for injection into the persona generation prompt. Returns `None` for unsupported markets or if no active snapshot — never blocks generation.

---

## Avatar Service (`avatar_service.py`)

Generates photorealistic DALL-E 3 headshots for personas.

**Prompt construction:**
- No-text constraint first (DALL-E weights early tokens)
- Ethnicity hint from location (maps cities → Filipino / Indonesian / Vietnamese / Thai / Malaysian / Singaporean / South Asian Indian)
- Income level → clothing quality
- Personality traits → facial expression
- Archetype label → posture/energy
- Psychographic segment → demeanor

**Storage:**
- Production (Supabase configured): uploads to `{SUPABASE_AVATARS_BUCKET}/avatars/{persona_id}.png` via REST PUT; returns public URL
- Local dev fallback: saves to `{UPLOAD_DIR}/avatars/{persona_id}.png`; returns `/uploads/avatars/{id}.png`

Avatar generation is non-blocking — failure is logged and does not affect persona data.
Avatar URL is propagated to the linked `LibraryPersona` record if one exists.

---

## Benchmarking Service (`benchmarking_service.py`)

Three-layer trust system for simulation results.

### Phase 1: Cross-simulation Convergence (`compute_convergence`)

Compares aggregate results across completed simulations sharing the same persona group (and optional briefing). Returns pairwise scores and an overall convergence score.

**Pairwise metrics (per simulation pair):**
- Direction match: dominant sentiment agrees (50% weight)
- Distribution similarity: 1 − Jensen-Shannon divergence between sentiment distributions (30% weight)
- Theme overlap: word-level Jaccard similarity of top themes (20% weight)

**Interpretation:** ≥ 0.75 = strong, ≥ 0.5 = moderate, < 0.5 = weak.

Works across all simulation types (concept_test, focus_group, idi, survey, conjoint) by resolving the correct aggregate result_type per type.

### Phase 2: Reproducibility Scoring (`score_reproducibility_study`)

Scores a set of N repeat runs for confidence in results.

**Metrics:**
| Metric | Weight | Description |
|---|---|---|
| Sentiment agreement rate | 40% | Fraction of runs with the same dominant sentiment |
| Distribution variance score | 35% | 1 − mean pairwise JSD across runs |
| Theme overlap coefficient | 25% | Fraction of theme tokens appearing in ≥ 60% of runs |

Composite `confidence_score` is a weighted average of available metrics. `maybe_score_reproducibility()` is called after each simulation finishes and triggers full scoring once all runs in a study are done.

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

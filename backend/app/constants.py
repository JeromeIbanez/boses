"""
Application-wide constants.
Import from here instead of scattering magic numbers across the codebase.
"""

# ---------------------------------------------------------------------------
# Simulation timeouts & concurrency
# ---------------------------------------------------------------------------

# How long a simulation can stay in running/pending/generating_report before
# it's considered stuck and auto-marked as failed.
SIMULATION_TIMEOUT_MINUTES: int = 20

# Max number of persona reactions run in parallel inside the concept-test engine.
MAX_PARALLEL_PERSONAS: int = 5

# ---------------------------------------------------------------------------
# Rate limits
# ---------------------------------------------------------------------------

# POST /simulations — per user per hour
SIMULATION_CREATE_RATE_LIMIT: str = "20/hour"

# ---------------------------------------------------------------------------
# LLM temperatures
# ---------------------------------------------------------------------------

# Concept-test individual persona reaction
CONCEPT_TEST_TEMPERATURE: float = 0.9

# Concept-test aggregate summary
CONCEPT_TEST_AGGREGATE_TEMPERATURE: float = 0.7

# Survey schema parsing / structured extraction (deterministic)
SURVEY_PARSE_TEMPERATURE: float = 0.0

# Conjoint design generation (needs some creativity)
CONJOINT_DESIGN_TEMPERATURE: float = 0.85

# IDI script parsing (deterministic)
IDI_PARSE_TEMPERATURE: float = 0.0

# ---------------------------------------------------------------------------
# Conjoint analysis
# ---------------------------------------------------------------------------

# Bounds on the number of choice tasks in a conjoint study
CONJOINT_MIN_TASKS: int = 6
CONJOINT_MAX_TASKS: int = 20

# ---------------------------------------------------------------------------
# Reliability / reproducibility checks
# ---------------------------------------------------------------------------

# Minimum and maximum number of repeat runs allowed per reliability check
RELIABILITY_MIN_RUNS: int = 2
RELIABILITY_MAX_RUNS: int = 5
RELIABILITY_DEFAULT_RUNS: int = 3

# ---------------------------------------------------------------------------
# Sentiment scoring
# ---------------------------------------------------------------------------

SENTIMENT_SCORES: dict[str, float] = {
    "Positive": 1.0,
    "Neutral": 0.0,
    "Negative": -1.0,
}

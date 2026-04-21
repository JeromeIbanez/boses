"""
Central prompt registry for all simulation engines.

All prompt-building logic lives here so prompts can be reviewed, tuned,
and iterated on independently of engine orchestration code.

Structure:
  - _persona_identity_block()  — shared identity section used by all engines
  - _HUMAN_VOICE_DIRECTIVE     — shared behavioural directive string
  - concept_test_*             — Concept Test prompts
  - focus_group_*              — Focus Group prompts (personas + moderator)
  - idi_*                      — IDI prompts (AI-assisted and manual)
  - survey_*                   — Survey prompts
  - conjoint_*                 — Conjoint / Trade-Off Test prompts
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.persona import Persona


# ---------------------------------------------------------------------------
# Shared building blocks
# ---------------------------------------------------------------------------

def _persona_identity_block(persona: "Persona") -> str:
    """
    Core identity section injected into every persona system prompt.
    Covers demographics, psychographics, and the richer behavioural fields
    that make responses feel specific and grounded.
    """
    traits = ", ".join(persona.personality_traits or [])
    return (
        f"You are {persona.full_name}, a {persona.age}-year-old {persona.gender} from {persona.location}. "
        f"You work as {persona.occupation} and earn a {persona.income_level} income. "
        f"Background: {persona.educational_background or 'Not specified'}. "
        f"Family: {persona.family_situation or 'Not specified'}. "
        f"Personality: {traits or 'Not specified'}. "
        f"What drives you: {persona.values_and_motivations or 'Not specified'}. "
        f"Your frustrations: {persona.pain_points or 'Not specified'}. "
        f"Media habits: {persona.media_consumption or 'Not specified'}. "
        f"Purchase behavior: {persona.purchase_behavior or 'Not specified'}. "
        f"Brand attitudes: {persona.brand_attitudes or 'Not specified'}. "
        f"What triggers you to buy: {persona.buying_triggers or 'Not specified'}. "
        f"Who you want to be: {persona.aspirational_identity or 'Not specified'}. "
    )


# Shared behavioural directive — paste into any system prompt that needs it.
# Explicitly counters AI-typical patterns: over-structuring, formal connectors,
# exhaustive coverage, and the tendency to sound like a product reviewer.
_HUMAN_VOICE_DIRECTIVE = (
    "Speak exactly as this person would in real conversation — natural, unpolished, and emotionally honest. "
    "Use hedging when uncertain ('I think', 'honestly', 'I'm not sure but'). "
    "Don't structure your answer as a list. Don't try to be comprehensive. "
    "Say what genuinely stands out to you, even if it's just one thing. "
    "You can be blunt, enthusiastic, skeptical, or indifferent — whatever fits your character."
)


# ---------------------------------------------------------------------------
# Concept Test
# ---------------------------------------------------------------------------

def concept_test_system_prompt(persona: "Persona") -> str:
    return (
        _persona_identity_block(persona)
        + "You are participating in a market research exercise. "
        + _HUMAN_VOICE_DIRECTIVE
    )


def concept_test_user_prompt(briefing_text: str, prompt_question: str) -> str:
    return (
        f"Here is the briefing material:\n\n"
        f"---\n{briefing_text}\n---\n\n"
        f"Question: {prompt_question}\n\n"
        "Please respond in character. Return a JSON object with exactly these keys:\n"
        '  "reaction": your immediate gut response (2–3 sentences in first person, natural voice — not a formal analysis)\n'
        '  "sentiment": one of "Positive", "Neutral", or "Negative"\n'
        '  "reasoning": why you feel this way (3–5 sentences in your natural voice, citing specifics from the briefing)\n'
        '  "notable_quote": one sentence that best captures your opinion\n'
        '  "key_themes": an array of 3 short theme strings that came up for you'
    )


def concept_test_aggregate_user_prompt(
    n: int,
    group_name: str,
    group_location: str,
    group_occupation: str,
    age_min: int,
    age_max: int,
    prompt_question: str,
    reactions_text: str,
) -> str:
    return (
        f"You are a senior market research analyst. Below are reactions from {n} consumers "
        f"in the \"{group_name}\" demographic ({group_location}, {group_occupation}, ages {age_min}–{age_max}) "
        f"to the following question: \"{prompt_question}\"\n\n"
        f"INDIVIDUAL REACTIONS:\n{reactions_text}\n\n"
        "Please provide:\n"
        "1. OVERALL SENTIMENT: The dominant sentiment and confidence level\n"
        "2. SENTIMENT DISTRIBUTION: Count of Positive / Neutral / Negative (one per line, format: \"Positive: N\")\n"
        "3. TOP THEMES: The 3–5 most recurring themes across all responses (comma-separated)\n"
        "4. SUMMARY: A 2–3 paragraph narrative synthesizing what this group thinks and feels\n"
        "5. STRATEGIC RECOMMENDATIONS: 2–3 concrete, actionable suggestions for the marketing team\n\n"
        "Be specific. Reference actual responses. Be direct about what worked and what didn't."
    )


# ---------------------------------------------------------------------------
# Focus Group
# ---------------------------------------------------------------------------

def focus_group_system_prompt(persona: "Persona", briefing_text: str) -> str:
    briefing_block = (
        f"\n\nBackground material for context:\n---\n{briefing_text}\n---"
        if briefing_text else ""
    )
    return (
        _persona_identity_block(persona)
        + f"A day in your life: {persona.day_in_the_life or 'Not specified'}. "
        + "You are participating in a focus group discussion with other consumers. "
        + _HUMAN_VOICE_DIRECTIVE
        + briefing_block
    )


def focus_group_round2_user_prompt(opening: str, others_block: str, bridge: str) -> str:
    return (
        f"The moderator opened with:\n{opening}\n\n"
        f"Other participants said:\n{others_block}\n\n"
        f"The moderator then asked:\n{bridge}\n\n"
        "React to what genuinely interests or bothers you in what others said — you don't have to address everything. "
        "You can agree, push back, or go off in a new direction. 2–4 sentences is fine."
    )


# Moderator prompts — these drive the LLM that acts as the group facilitator,
# not the persona LLMs.
FOCUS_GROUP_MODERATOR_SYSTEM_PROMPT = (
    "You are a professional qualitative research moderator. Keep your language neutral, warm, and concise."
)


def focus_group_moderator_opening_user_prompt(
    topic: str, briefing_text: str, n_participants: int
) -> str:
    context_block = (
        f"\n\nBriefing context:\n---\n{briefing_text}\n---" if briefing_text else ""
    )
    return (
        f"You are facilitating a focus group with {n_participants} consumer participants. "
        f"The research topic is: \"{topic}\"\n"
        f"{context_block}\n\n"
        "Write a brief, professional opening for the focus group (2–3 sentences) that:\n"
        "- Welcomes participants and sets a comfortable, open tone\n"
        "- States the topic clearly without leading the group\n"
        "- Ends with a clear, open-ended first question to kick off discussion\n\n"
        "Write only the moderator's spoken words. No stage directions, no labels."
    )


def focus_group_moderator_bridge_user_prompt(
    topic: str, round1_entries: list[dict]
) -> str:
    responses_block = "\n".join(
        f"- {e['speaker']}: {e['text']}" for e in round1_entries
    )
    return (
        f"Topic: \"{topic}\"\n\n"
        f"Here are the initial responses from focus group participants:\n{responses_block}\n\n"
        "As the moderator, write a brief bridge (2–3 sentences) that:\n"
        "- Acknowledges what you heard (without judging or agreeing)\n"
        "- Highlights any emerging tensions or interesting differences\n"
        "- Poses a follow-up question that invites participants to respond to each other or dig deeper\n\n"
        "Write only the moderator's spoken words. No stage directions, no labels."
    )


def focus_group_aggregate_user_prompt(
    topic: str, transcript_text: str, group_name: str
) -> str:
    return (
        f"You are a senior qualitative research analyst. Below is the full transcript of a focus group "
        f"on the topic: \"{topic}\"\n\n"
        f"GROUP: {group_name}\n\n"
        f"TRANSCRIPT:\n{transcript_text}\n\n"
        "Provide a structured analysis with the following sections — use the exact labels shown:\n\n"
        "MODERATOR SUMMARY: A 2–3 paragraph narrative of how the discussion unfolded, key dynamics, and overall group sentiment.\n"
        "CONSENSUS THEMES: The 3–5 themes that most participants agreed on (comma-separated).\n"
        "DISAGREEMENTS: The 2–4 points where participants meaningfully diverged (comma-separated).\n"
        "SENTIMENT DISTRIBUTION:\n"
        "Positive: N\n"
        "Neutral: N\n"
        "Negative: N\n"
        "RECOMMENDATIONS: 2–3 concrete, actionable recommendations for the research team based on the discussion.\n\n"
        "Be specific. Reference what participants actually said."
    )


# ---------------------------------------------------------------------------
# IDI (In-Depth Interview)
# ---------------------------------------------------------------------------

def idi_system_prompt(persona: "Persona", briefing_text: str) -> str:
    briefing_block = (
        f"\n\nFor context, here is background material relevant to this interview:\n---\n{briefing_text}\n---"
        if briefing_text else ""
    )
    return (
        _persona_identity_block(persona)
        + f"How you use technology: {persona.digital_behavior or 'Not specified'}. "
        + f"A day in your life: {persona.day_in_the_life or 'Not specified'}. "
        + "You are participating in a one-on-one research interview. "
        + "Speak exactly as this person would in real conversation — natural, unpolished, and emotionally honest. "
        + "Use hedging when uncertain ('I think', 'honestly', 'I'm not sure but'). "
        + "Answer the question in your natural voice. If something triggers a memory or strong reaction, go there — that's the good stuff. "
        + "Don't over-explain. Don't structure your answer as a list."
        + briefing_block
    )


def idi_analyse_persona_user_prompt(
    full_name: str, age: int, occupation: str, location: str, transcript: str
) -> str:
    return (
        f"You are a qualitative research analyst. Below is an interview transcript with "
        f"{full_name} ({age}, {occupation}, {location}).\n\n"
        f"TRANSCRIPT:\n{transcript}\n\n"
        "Analyse this interview and respond in the following EXACT format:\n\n"
        "SENTIMENT: <Positive | Neutral | Negative>\n"
        "SUMMARY: <2-3 sentence summary of this person's overall perspective>\n"
        "KEY THEMES: <3-5 comma-separated themes that emerged>\n"
        "NOTABLE QUOTES:\n"
        "- \"<verbatim quote from transcript>\" — <1 sentence context>\n"
        "- \"<verbatim quote from transcript>\" — <1 sentence context>\n"
        "- \"<verbatim quote from transcript>\" — <1 sentence context>"
    )


def idi_aggregate_user_prompt(
    group_name: str, question_summary: str, per_persona_block: str, n: int
) -> str:
    return (
        f"You are a senior qualitative research analyst. You have just completed in-depth interviews "
        f"with {n} participants from the \"{group_name}\" segment.\n\n"
        f"RESEARCH FOCUS:\n{question_summary}\n\n"
        f"INDIVIDUAL INTERVIEW SUMMARIES:\n{per_persona_block}\n\n"
        "Write a professional IDI research report with the following EXACT sections:\n\n"
        "EXECUTIVE SUMMARY:\n"
        "<2-3 paragraphs synthesising the key findings across all respondents>\n\n"
        "CROSS-PERSONA THEMES:\n"
        "<List 3-5 themes that appeared across multiple interviews. For each theme, note which respondents held it. "
        "Format: \"Theme name: description (held by: Name1, Name2)\">\n\n"
        "PER-PERSONA HIGHLIGHTS:\n"
        "<One key takeaway per respondent that captures their unique perspective. Format: \"Name: key takeaway\">\n\n"
        "RECOMMENDATIONS:\n"
        "<3 concrete, actionable recommendations for the team based on these findings>"
    )


# ---------------------------------------------------------------------------
# Survey
# ---------------------------------------------------------------------------

def survey_system_prompt(persona: "Persona", briefing_text: str) -> str:
    briefing_block = (
        f"\n\nFor context, here is background material relevant to this survey:\n---\n{briefing_text}\n---"
        if briefing_text else ""
    )
    return (
        _persona_identity_block(persona)
        + "You are filling out a market research survey. Answer as you genuinely would — not how you think you 'should' answer. "
        + "For open-ended questions, be brief and honest, the way you'd actually write in a real survey. "
        + "Use hedging when uncertain. Don't try to be comprehensive or polished."
        + briefing_block
    )


def survey_user_prompt(question_lines: list[str]) -> str:
    return (
        "Please fill out the following survey questions as yourself. "
        "Return ONLY a valid JSON array — no markdown, no explanation. "
        "Each element: {\"id\": \"<question id>\", \"answer\": <value>}.\n"
        "For likert: answer is an integer.\n"
        "For multiple_choice: answer is the exact option string.\n"
        "For open_ended: answer is a string (2–4 sentences).\n\n"
        "QUESTIONS:\n" + "\n".join(question_lines)
    )


def survey_aggregate_user_prompt(
    group_name: str,
    group_location: str,
    group_occupation: str,
    age_min: int,
    age_max: int,
    n: int,
    summary_context: str,
) -> str:
    return (
        f"You are a senior market researcher. {n} respondents "
        f"from the '{group_name}' group ({group_location}, {group_occupation}, ages {age_min}–{age_max}) "
        f"completed a survey. Here are the results per question:\n\n{summary_context}\n\n"
        "Return ONLY valid JSON (no markdown):\n"
        '{"executive_summary": "2–3 paragraph narrative", "recommendations": "2–3 actionable bullet points"}'
    )


# ---------------------------------------------------------------------------
# Conjoint / Trade-Off Test
# ---------------------------------------------------------------------------

def conjoint_system_prompt(persona: "Persona", briefing_text: str) -> str:
    briefing_block = (
        f"\n\nProduct context:\n---\n{briefing_text}\n---"
        if briefing_text else ""
    )
    return (
        _persona_identity_block(persona)
        + "You are making real purchasing decisions. Choose based on your actual priorities, "
        + "values, and budget — not what seems 'objectively best'. "
        + "Think about how you'd actually weigh this in a real shopping decision — what you notice first, "
        + "what you'd overlook, what would make you hesitate."
        + briefing_block
    )


def conjoint_user_prompt(category: str, tasks_text: str) -> str:
    return (
        f"You are choosing between options for: {category}.\n\n"
        "For each task below, you MUST choose either A or B — you cannot choose both or neither.\n"
        "Return ONLY a valid JSON array with no markdown, no code blocks, no explanation:\n"
        '[{"task": 1, "chosen": "A", "reasoning": "<1-2 sentences in first person why you chose this>"}, ...]\n\n'
        "Your reasoning should sound like a real person making a quick mental calculation, not a product review.\n\n"
        f"{tasks_text}"
    )


def conjoint_narrative_user_prompt(
    category: str,
    group_name: str,
    group_location: str,
    group_occupation: str,
    age_min: int,
    age_max: int,
    n: int,
    importance_lines: str,
    reasoning_block: str,
) -> str:
    return (
        f"You are a senior market research analyst. {n} consumers from "
        f"the '{group_name}' group ({group_location}, {group_occupation}, "
        f"ages {age_min}–{age_max}) completed a conjoint trade-off study on: {category}\n\n"
        f"ATTRIBUTE IMPORTANCE (what actually drives their choices):\n{importance_lines}\n\n"
        f"SAMPLE VERBATIM REASONING:\n{reasoning_block}\n\n"
        "Return ONLY valid JSON (no markdown, no code fences):\n"
        '{"executive_summary": "2-3 paragraph narrative of what drives choices and what this means for the product team", '
        '"recommendations": "2-3 concrete product or pricing recommendations based on these trade-off preferences"}'
    )

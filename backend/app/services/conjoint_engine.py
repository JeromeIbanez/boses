"""
Conjoint / Trade-Off Test simulation engine.

Runs a Choice-Based Conjoint (CBC) analysis using paired forced-choice tasks.
Each persona receives a batch of tasks where they must choose between two fully
specified product profiles, revealing what they actually trade off rather than
what they say they value.

Flow:
  1. Generate N choice-set pairs from attribute/level design
  2. For each persona: send all tasks in ONE LLM call, parse JSON choices
  3. Compute part-worth utilities + attribute importance per persona
  4. Aggregate: average part-worths, market share simulation, LLM narrative
"""
import json
import logging
import random
from collections import defaultdict
from datetime import datetime

from openai import OpenAI
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models.persona import Persona
from app.models.simulation import Simulation
from app.models.simulation_result import SimulationResult
from app.services.prompts import conjoint_system_prompt, conjoint_user_prompt, conjoint_narrative_user_prompt

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Profile generation
# ---------------------------------------------------------------------------

def _generate_choice_sets(
    attributes: list[dict],
    n_tasks: int,
    seed: int | None = None,
) -> list[tuple[dict, dict]]:
    """
    Generate n_tasks pairs of product profiles.
    Each profile specifies exactly one level per attribute.
    Profiles A and B within a task are guaranteed to differ on at least one attribute.
    """
    rng = random.Random(seed)
    attr_names = [a["name"] for a in attributes]
    attr_levels = {a["name"]: a["levels"] for a in attributes}

    tasks = []
    for _ in range(n_tasks):
        for _attempt in range(20):
            profile_a = {name: rng.choice(attr_levels[name]) for name in attr_names}
            profile_b = {name: rng.choice(attr_levels[name]) for name in attr_names}
            if profile_a != profile_b:
                tasks.append((profile_a, profile_b))
                break
        else:
            # Degenerate case: force profiles to differ on the first attribute that has >1 level
            profile_b = dict(profile_a)
            for name in attr_names:
                levels = attr_levels[name]
                if len(levels) > 1:
                    others = [lv for lv in levels if lv != profile_a[name]]
                    profile_b[name] = rng.choice(others)
                    break
            tasks.append((profile_a, profile_b))

    return tasks


# ---------------------------------------------------------------------------
# Persona system prompt
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# Persona LLM call — all tasks batched in one request
# ---------------------------------------------------------------------------

def _run_persona_tasks(
    client: OpenAI,
    system_prompt: str,
    category: str,
    tasks: list[tuple[dict, dict]],
) -> list[dict]:
    """
    Present all choice tasks to the persona in a single LLM call.
    Returns a list of dicts: [{task: int, chosen: "A"|"B", reasoning: str}, ...]
    Retries once at temperature=0 if JSON parsing fails.
    Raises ValueError if both attempts fail.
    """
    lines = []
    for i, (a, b) in enumerate(tasks, 1):
        a_str = " | ".join(f"{k}={v}" for k, v in a.items())
        b_str = " | ".join(f"{k}={v}" for k, v in b.items())
        lines.append(f"TASK {i}:\n  Option A: {a_str}\n  Option B: {b_str}")
    tasks_text = "\n\n".join(lines)

    user_prompt = conjoint_user_prompt(category, tasks_text)

    for temperature in (0.85, 0.0):
        try:
            response = client.chat.completions.create(
                model=settings.OPENAI_MODEL,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
            )
            raw = (response.choices[0].message.content or "").strip()
            # Strip markdown code fences if present
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
                raw = raw.strip()
            parsed = json.loads(raw)
            if isinstance(parsed, list) and len(parsed) == len(tasks):
                return parsed
        except Exception:
            continue

    raise ValueError("Could not parse conjoint choices from LLM response after retry")


# ---------------------------------------------------------------------------
# Utility computation (no scipy)
# ---------------------------------------------------------------------------

def _compute_utilities(
    task_results: list[dict],
    tasks: list[tuple[dict, dict]],
    attributes: list[dict],
) -> dict:
    """
    Compute per-level part-worth utilities and per-attribute importance.

    Algorithm:
    - For each task: record the levels in the chosen and rejected profiles
    - raw_score[attr][level] = chosen_count / (chosen_count + rejected_count)
    - Zero-center scores within each attribute → part-worth
    - importance = (max_pw - min_pw) across levels, normalised to sum to 100
    """
    chosen_count: dict[str, dict[str, int]] = {a["name"]: {} for a in attributes}
    rejected_count: dict[str, dict[str, int]] = {a["name"]: {} for a in attributes}

    for result in task_results:
        task_idx = result.get("task", 0) - 1  # 1-indexed in prompt
        if task_idx < 0 or task_idx >= len(tasks):
            continue
        profile_a, profile_b = tasks[task_idx]
        chosen = result.get("chosen", "A")
        chosen_profile = profile_a if chosen == "A" else profile_b
        rejected_profile = profile_b if chosen == "A" else profile_a

        for attr_name in chosen_profile:
            lv_c = chosen_profile[attr_name]
            lv_r = rejected_profile[attr_name]
            chosen_count[attr_name][lv_c] = chosen_count[attr_name].get(lv_c, 0) + 1
            rejected_count[attr_name][lv_r] = rejected_count[attr_name].get(lv_r, 0) + 1

    part_worths: dict[str, dict[str, float]] = {}
    importance_raw: dict[str, float] = {}

    for attr in attributes:
        name = attr["name"]
        levels = attr["levels"]
        raw_scores = {}
        for lv in levels:
            c = chosen_count[name].get(lv, 0)
            r = rejected_count[name].get(lv, 0)
            raw_scores[lv] = c / (c + r) if (c + r) > 0 else 0.5

        mean = sum(raw_scores.values()) / len(raw_scores)
        centered = {lv: round(raw_scores[lv] - mean, 4) for lv in levels}
        part_worths[name] = centered
        importance_raw[name] = max(centered.values()) - min(centered.values())

    total_importance = sum(importance_raw.values()) or 1.0
    importances = {
        name: round(importance_raw[name] / total_importance * 100, 1)
        for name in importance_raw
    }
    top_driver = max(importances, key=lambda k: importances[k])

    return {
        "part_worths": part_worths,
        "attribute_importances": importances,
        "top_driver": top_driver,
    }


# ---------------------------------------------------------------------------
# Hypothetical profiles for market share simulation
# ---------------------------------------------------------------------------

def _build_hypothetical_profiles(attributes: list[dict]) -> list[dict]:
    """
    Auto-generate 3 hypothetical product profiles for market share simulation:
    - Best Value: cheapest on price-like attributes, mid-tier on features
    - Premium: best on all dimensions
    - Balanced: mid-tier across all attributes

    Heuristic: attribute names containing 'price', 'cost', 'fee', 'rate' →
    first level = lowest price (best value), last level = highest price (premium).
    All other attributes: last level = best, first level = worst.
    """
    price_keywords = ("price", "cost", "fee", "rate", "tariff")

    best_value: dict[str, str] = {}
    premium: dict[str, str] = {}
    balanced: dict[str, str] = {}

    for attr in attributes:
        name = attr["name"]
        levels = attr["levels"]
        mid = levels[len(levels) // 2]
        is_price_like = any(kw in name.lower() for kw in price_keywords)

        if is_price_like:
            best_value[name] = levels[0]   # cheapest
            premium[name] = levels[-1]     # most expensive
            balanced[name] = mid
        else:
            best_value[name] = mid
            premium[name] = levels[-1]     # best feature level
            balanced[name] = mid

    return [
        {"name": "Best Value", "attributes": best_value},
        {"name": "Premium", "attributes": premium},
        {"name": "Balanced", "attributes": balanced},
    ]


# ---------------------------------------------------------------------------
# Market share simulation (first-choice rule)
# ---------------------------------------------------------------------------

def _simulate_market_share(
    all_persona_part_worths: list[dict[str, dict[str, float]]],
    hypothetical_profiles: list[dict],
) -> dict:
    """
    First-choice rule: each persona votes for the hypothetical product with the
    highest summed part-worth score. Market share = votes / total * 100.
    """
    votes: dict[int, int] = {i: 0 for i in range(len(hypothetical_profiles))}

    for persona_pw in all_persona_part_worths:
        best_idx = 0
        best_score = float("-inf")
        for idx, profile in enumerate(hypothetical_profiles):
            score = sum(
                persona_pw.get(attr, {}).get(level, 0.0)
                for attr, level in profile["attributes"].items()
            )
            if score > best_score:
                best_score = score
                best_idx = idx
        votes[best_idx] += 1

    total = sum(votes.values()) or 1
    return {
        "profiles_tested": hypothetical_profiles,
        "shares": {
            hypothetical_profiles[i]["name"]: round(votes[i] / total * 100, 1)
            for i in range(len(hypothetical_profiles))
        },
    }


# ---------------------------------------------------------------------------
# LLM narrative summary
# ---------------------------------------------------------------------------

def _generate_narrative(
    client: OpenAI,
    category: str,
    importances: dict[str, float],
    part_worths: dict[str, dict[str, float]],
    individual_results: list[dict],
    group,
) -> tuple[str, str]:
    """Generate executive summary and recommendations via LLM."""
    importance_lines = "\n".join(
        f"- {attr}: {pct:.1f}% importance"
        for attr, pct in sorted(importances.items(), key=lambda x: -x[1])
    )
    # Collect sample verbatim reasoning from the first task of up to 5 personas
    reasonings = []
    for r in individual_results[:5]:
        tasks = r.get("tasks", [])
        if tasks and tasks[0].get("reasoning"):
            reasonings.append(f'- {r["persona_name"]}: "{tasks[0]["reasoning"]}"')
    reasoning_block = "\n".join(reasonings) if reasonings else "No verbatim data available."

    prompt = conjoint_narrative_user_prompt(
        category=category,
        group_name=group.name,
        group_location=group.location,
        group_occupation=group.occupation,
        age_min=group.age_min,
        age_max=group.age_max,
        n=len(individual_results),
        importance_lines=importance_lines,
        reasoning_block=reasoning_block,
    )
    try:
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
        )
        raw = (response.choices[0].message.content or "").strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        parsed = json.loads(raw)
        return parsed.get("executive_summary", ""), parsed.get("recommendations", "")
    except Exception as e:
        logger.error(f"Conjoint narrative generation failed: {e}")
        return "", ""


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def run_conjoint(simulation_id: str) -> None:
    client = OpenAI(api_key=settings.openai_api_key)
    db = SessionLocal()
    sim_ref = simulation_id[:8]

    try:
        simulation = db.get(Simulation, simulation_id)
        if not simulation:
            return

        simulation.status = "running"
        db.commit()

        personas = db.execute(
            select(Persona).where(Persona.persona_group_id == simulation.persona_group_id)
        ).scalars().all()

        if not personas:
            raise ValueError("No personas found for this group. Please generate personas first.")

        design = simulation.survey_schema or {}
        attributes: list[dict] = design.get("attributes", [])
        n_tasks: int = design.get("n_tasks", 10)

        if not attributes or len(attributes) < 2:
            raise ValueError("Conjoint design requires at least 2 attributes.")
        if any(len(a.get("levels", [])) < 2 for a in attributes):
            raise ValueError("Each attribute must have at least 2 levels.")

        category = simulation.prompt_question or "the product"
        briefing_text = simulation.briefing.extracted_text if simulation.briefing else ""
        group = simulation.persona_group

        tasks = _generate_choice_sets(attributes, n_tasks)
        total = len(personas)
        individual_results: list[dict] = []
        failed_personas: list[str] = []
        all_persona_part_worths: list[dict] = []

        for i, persona in enumerate(personas, 1):
            simulation.progress = {
                "stage": "choice_tasks",
                "current": i,
                "total": total,
                "current_name": persona.full_name,
                "completed": [r["persona_name"] for r in individual_results],
                "failed": failed_personas[:],
            }
            db.commit()
            logger.info(f"[conjoint:{sim_ref}] Persona {i}/{total}: {persona.full_name}")

            try:
                system_prompt = conjoint_system_prompt(persona, briefing_text)
                task_responses = _run_persona_tasks(client, system_prompt, category, tasks)
                utilities = _compute_utilities(task_responses, tasks, attributes)

                # Enrich tasks with profile data for transparent storage
                enriched_tasks = []
                for resp in task_responses:
                    idx = resp.get("task", 0) - 1
                    if 0 <= idx < len(tasks):
                        a, b = tasks[idx]
                        enriched_tasks.append({
                            "task_index": resp["task"],
                            "profile_a": a,
                            "profile_b": b,
                            "chosen": resp.get("chosen", "A"),
                            "reasoning": resp.get("reasoning", ""),
                        })

                result = SimulationResult(
                    simulation_id=simulation_id,
                    persona_id=persona.id,
                    result_type="conjoint_individual",
                    report_sections={
                        "tasks": enriched_tasks,
                        "attribute_importances": utilities["attribute_importances"],
                        "part_worths": utilities["part_worths"],
                        "top_driver": utilities["top_driver"],
                    },
                )
                db.add(result)
                individual_results.append({
                    "persona_name": persona.full_name,
                    "persona_id": str(persona.id),
                    "utilities": utilities,
                    "tasks": enriched_tasks,
                })
                all_persona_part_worths.append(utilities["part_worths"])
                logger.info(
                    f"[conjoint:{sim_ref}] ✓ {persona.full_name} — "
                    f"top driver: {utilities['top_driver']}"
                )

            except Exception as e:
                logger.error(f"[conjoint:{sim_ref}] ✗ {persona.full_name}: {e}")
                failed_personas.append(persona.full_name)

        if not individual_results:
            raise RuntimeError(f"All {len(personas)} persona(s) failed to respond.")

        if failed_personas:
            simulation.error_message = (
                f"{len(failed_personas)} of {len(personas)} persona(s) failed: "
                + ", ".join(failed_personas)
            )

        # ------------------------------------------------------------------ #
        # Aggregate step
        # ------------------------------------------------------------------ #
        simulation.status = "generating_report"
        simulation.progress = {
            "stage": "generating_report",
            "current": total,
            "total": total,
            "current_name": None,
            "completed": [r["persona_name"] for r in individual_results],
            "failed": failed_personas[:],
        }
        db.commit()
        logger.info(f"[conjoint:{sim_ref}] Generating aggregate report…")

        # Average part-worths across all personas
        agg_part_worths: dict[str, dict[str, float]] = {}
        for attr in attributes:
            name = attr["name"]
            levels = attr["levels"]
            agg_part_worths[name] = {
                lv: round(
                    sum(pw.get(name, {}).get(lv, 0.0) for pw in all_persona_part_worths)
                    / len(all_persona_part_worths),
                    4,
                )
                for lv in levels
            }

        # Recompute importance from aggregate part-worths (more consistent than averaging importances)
        importance_raw = {
            attr["name"]: (
                max(agg_part_worths[attr["name"]].values())
                - min(agg_part_worths[attr["name"]].values())
            )
            for attr in attributes
        }
        total_imp = sum(importance_raw.values()) or 1.0
        agg_importances = {
            name: round(importance_raw[name] / total_imp * 100, 1)
            for name in importance_raw
        }

        # Market share simulation
        hypothetical_profiles = _build_hypothetical_profiles(attributes)
        market_share = _simulate_market_share(all_persona_part_worths, hypothetical_profiles)

        # Persona segments by top driver
        segments_map: dict[str, list[str]] = defaultdict(list)
        for r in individual_results:
            segments_map[r["utilities"]["top_driver"]].append(r["persona_id"])
        persona_segments = [
            {"label": f"{driver}-Driven", "persona_ids": pids, "top_driver": driver}
            for driver, pids in segments_map.items()
        ]

        # LLM narrative
        executive_summary, recommendations = _generate_narrative(
            client, category, agg_importances, agg_part_worths, individual_results, group
        )

        agg_result = SimulationResult(
            simulation_id=simulation_id,
            persona_id=None,
            result_type="conjoint_aggregate",
            report_sections={
                "attribute_importances": agg_importances,
                "part_worths": agg_part_worths,
                "market_share_simulation": market_share,
                "persona_segments": persona_segments,
                "executive_summary": executive_summary,
                "recommendations": recommendations,
            },
        )
        db.add(agg_result)

        simulation.status = "complete"
        simulation.completed_at = datetime.utcnow()
        db.commit()
        logger.info(
            f"[conjoint:{sim_ref}] Complete — "
            f"{len(individual_results)}/{total} personas succeeded"
        )
        _trigger_scoring(simulation_id)

    except Exception as e:
        logger.error(f"[conjoint:{sim_ref}] Failed: {e}")
        try:
            simulation = db.get(Simulation, simulation_id)
            if simulation:
                simulation.status = "failed"
                simulation.error_message = str(e)
                db.commit()
        except Exception:
            db.rollback()
        _trigger_scoring(simulation_id)
    finally:
        db.close()


def _trigger_scoring(simulation_id: str) -> None:
    try:
        from app.services.simulation_engine import _trigger_post_completion_scoring
        _trigger_post_completion_scoring(simulation_id)
    except Exception:
        pass

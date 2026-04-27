"""
Boses MCP tool implementations.

Tool descriptions are the primary signal agents use to decide when and how to
call each tool — keep them accurate and action-oriented.
"""
from __future__ import annotations

import logging

from mcp.server.fastmcp import FastMCP

from mcp_server import client
from mcp_server.config import BOSES_APP_URL
from mcp_server.context import get_api_key

logger = logging.getLogger(__name__)

mcp = FastMCP("Boses Market Simulation Platform", host="0.0.0.0")


def _audit(tool_name: str) -> None:
    """Emit a structured audit log line: tool name + first 16 chars of API key."""
    key = get_api_key() or ""
    prefix = (key[:16] + "...") if len(key) > 16 else (key or "no-key")
    logger.info(f"[audit] tool={tool_name} key={prefix}")


# ---------------------------------------------------------------------------
# 1. list_projects
# ---------------------------------------------------------------------------

@mcp.tool()
async def list_projects() -> str:
    """
    List all projects in the Boses workspace.
    Returns a list of projects with their IDs and names.
    Always call this first to get a project_id before doing anything else.
    """
    _audit("list_projects")
    projects = await client.list_projects()
    if not projects:
        return "No projects found. Create one first using create_project."
    lines = [f"- {p['name']} (id: {p['id']})" for p in projects]
    return "Projects:\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# 2. create_project
# ---------------------------------------------------------------------------

@mcp.tool()
async def create_project(
    name: str,
    description: str = "",
) -> str:
    """
    Create a new project in the Boses workspace.
    Returns the new project's ID and name.
    Use this before creating persona groups or running simulations.

    Args:
        name: A short, descriptive name for the project, e.g. "Q3 Snack Launch SEA".
        description: Optional context about the project's research goals.
    """
    _audit("create_project")
    project = await client.create_project(name, description)
    return (
        f"Project '{project['name']}' created.\n"
        f"- ID: {project['id']}\n"
        f"Use project_id '{project['id']}' when calling list_persona_groups or run_simulation."
    )


# ---------------------------------------------------------------------------
# 3. delete_project
# ---------------------------------------------------------------------------

@mcp.tool()
async def delete_project(project_id: str) -> str:
    """
    Permanently delete a Boses project and all its data (persona groups, simulations, briefings).
    This cannot be undone — confirm with the user before calling.

    Args:
        project_id: The ID of the project to delete.
    """
    _audit("delete_project")
    await client.delete_project(project_id)
    return f"Project '{project_id}' and all its data have been deleted."


# ---------------------------------------------------------------------------
# 4. list_persona_groups
# ---------------------------------------------------------------------------

@mcp.tool()
async def list_persona_groups(project_id: str) -> str:
    """
    List all persona groups in a Boses project.
    Returns each group's ID, name, demographic summary, generation status, and persona count.
    Use this to find an existing audience before creating a new one.

    Args:
        project_id: The ID of the project (get this from list_projects).
    """
    _audit("list_persona_groups")
    groups = await client.list_persona_groups(project_id)
    if not groups:
        return "No persona groups found in this project."

    lines = []
    for g in groups:
        status = g.get("generation_status", "unknown")
        count = g.get("persona_count", "?")
        age = f"{g.get('age_min')}–{g.get('age_max')}"
        gender = g.get("gender", "All")
        location = g.get("location", "")
        income = g.get("income_level", "")
        lines.append(
            f"- {g['name']} (id: {g['id']}) | {count} personas | {age}yo {gender} | {location} | {income} income | status: {status}"
        )
    return "Persona groups:\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# 5. create_persona_group
# ---------------------------------------------------------------------------

@mcp.tool()
async def create_persona_group(
    project_id: str,
    name: str,
    description: str = "",
    age_min: int = 18,
    age_max: int = 45,
    gender: str = "All",
    location: str = "Southeast Asia",
    occupation: str = "Mixed",
    income_level: str = "Middle",
    psychographic_notes: str = "",
) -> str:
    """
    Create a new AI persona group from a demographic spec and generate all personas.
    This is a blocking call — it waits until all personas are fully generated (~30–90s).

    You can either:
    - Pass the 'description' field with a natural-language spec like
      "Metro Manila mothers, 28–40, middle income, health-conscious" and let Boses
      extract the structured fields automatically, OR
    - Pass the structured fields directly (age_min, age_max, gender, location, etc.)

    If both are provided, the structured fields override the parsed description.

    Args:
        project_id: The ID of the project.
        name: A short label for this group, e.g. "SEA Millennial Women".
        description: (Optional) Natural-language demographic description. If provided,
                     Boses will parse it and use it to fill any unspecified fields.
        age_min: Minimum age (default 18).
        age_max: Maximum age (default 45).
        gender: One of "All", "Female", "Male", "Non-binary" (default "All").
        location: City, region, or country, e.g. "Jakarta, Indonesia" (default "Southeast Asia").
        occupation: Job type or work description, e.g. "Office workers" (default "Mixed").
        income_level: One of "Low", "Middle", "Upper-middle", "High" (default "Middle").
        psychographic_notes: Optional lifestyle, values, or behavioral context.
    """
    _audit("create_persona_group")
    payload: dict = {
        "name": name,
        "age_min": age_min,
        "age_max": age_max,
        "gender": gender,
        "location": location,
        "occupation": occupation,
        "income_level": income_level,
    }
    if psychographic_notes:
        payload["psychographic_notes"] = psychographic_notes

    # If a natural-language description is provided, let the backend parse it
    # and fill in any fields not explicitly set.
    if description:
        try:
            parsed = await client.parse_persona_prompt(project_id, description)
            # Merge parsed fields as defaults (explicit args take precedence)
            for field in ("age_min", "age_max", "gender", "location", "occupation", "income_level", "psychographic_notes"):
                if field in parsed and payload.get(field) in (None, "", 18, 45, "All", "Southeast Asia", "Mixed", "Middle"):
                    payload[field] = parsed[field]
            if not payload.get("name") or payload["name"] == name:
                # Keep user-supplied name but allow parsed name as fallback
                payload["name"] = name or parsed.get("name", name)
        except Exception:
            pass  # Fall back to the structured fields as-is

    # Step 1: Create the group
    group = await client.create_persona_group(project_id, payload)
    group_id = group["id"]

    # Step 2: Trigger generation
    await client.generate_persona_group(project_id, group_id)

    # Step 3: Poll until complete
    try:
        group = await client.poll_persona_group_until_ready(project_id, group_id)
    except (TimeoutError, RuntimeError) as e:
        return f"Persona group '{name}' was created (id: {group_id}) but generation did not complete: {e}"

    count = group.get("persona_count", "?")
    return (
        f"Persona group '{group['name']}' is ready.\n"
        f"- ID: {group_id}\n"
        f"- {count} personas generated\n"
        f"- Demographics: {group.get('age_min')}–{group.get('age_max')}yo, "
        f"{group.get('gender')}, {group.get('location')}, {group.get('income_level')} income\n"
        f"Use group_id '{group_id}' when calling run_simulation."
    )


# ---------------------------------------------------------------------------
# 6. delete_persona_group
# ---------------------------------------------------------------------------

@mcp.tool()
async def delete_persona_group(project_id: str, group_id: str) -> str:
    """
    Permanently delete a persona group and all its generated personas.
    This cannot be undone — confirm with the user before calling.

    Args:
        project_id: The ID of the project.
        group_id: The ID of the persona group to delete.
    """
    _audit("delete_persona_group")
    await client.delete_persona_group(project_id, group_id)
    return f"Persona group '{group_id}' has been deleted."


# ---------------------------------------------------------------------------
# 7. list_briefings
# ---------------------------------------------------------------------------

@mcp.tool()
async def list_briefings(project_id: str) -> str:
    """
    List all briefing documents attached to a Boses project.
    Returns each briefing's ID, title, file type, and description.
    Use this to find existing briefings before uploading duplicates —
    you can reuse a briefing_id across multiple simulations.

    Args:
        project_id: The ID of the project.
    """
    _audit("list_briefings")
    briefings = await client.list_briefings(project_id)
    if not briefings:
        return "No briefings found in this project. Use create_briefing to upload one."

    lines = []
    for b in briefings:
        file_type = b.get("file_type", "unknown")
        description = b.get("description") or ""
        desc_part = f" — {description}" if description else ""
        lines.append(f"- {b['title']} (id: {b['id']}) | type: {file_type}{desc_part}")
    return "Briefings:\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# 8. create_briefing
# ---------------------------------------------------------------------------

@mcp.tool()
async def create_briefing(
    project_id: str,
    title: str,
    content: str,
    description: str = "",
) -> str:
    """
    Upload a BACKGROUND or CONTEXT document to a Boses project as plain text.
    Use for supporting material that gives personas additional context:
    brand guidelines, product specs, ad copy, competitor reports, etc.

    Do NOT use this for survey question documents — if the user shares a survey
    questionnaire and wants to run a "survey" simulation, extract the questions
    from it and pass them as survey_schema to run_simulation instead.

    The returned briefing_id can be passed to run_simulation via briefing_ids
    so all persona types (concept_test, focus_group, idi_ai, conjoint) can
    reference the document during the simulation.

    Args:
        project_id: The ID of the project to attach the briefing to.
        title: A short label for this briefing, e.g. "Q3 Brand Guidelines".
        content: The full text content of the document.
        description: Optional one-line summary of what the document contains.
    """
    _audit("create_briefing")
    briefing = await client.create_briefing(project_id, title, content, description)
    return (
        f"Briefing '{briefing['title']}' created.\n"
        f"- ID: {briefing['id']}\n"
        f"- Characters stored: {len(content)}\n"
        f"Pass briefing_id '{briefing['id']}' in the briefing_ids list when calling run_simulation."
    )


# ---------------------------------------------------------------------------
# 9. list_simulations
# ---------------------------------------------------------------------------

@mcp.tool()
async def list_simulations(project_id: str) -> str:
    """
    List all simulations in a Boses project.
    Returns each simulation's ID, type, status, and creation time.
    Use this to check what research has already been run before starting a new simulation.

    Args:
        project_id: The ID of the project.
    """
    _audit("list_simulations")
    simulations = await client.list_simulations(project_id)
    if not simulations:
        return "No simulations found in this project."

    lines = []
    for s in simulations:
        sim_type = s.get("simulation_type", "unknown")
        status = s.get("status", "unknown")
        created = s.get("created_at", "")[:10] if s.get("created_at") else ""
        created_part = f" | created: {created}" if created else ""
        lines.append(f"- {sim_type} (id: {s['id']}) | status: {status}{created_part}")
    return "Simulations:\n" + "\n".join(lines)


# ---------------------------------------------------------------------------
# 10. run_simulation
# ---------------------------------------------------------------------------

@mcp.tool()
async def run_simulation(
    project_id: str,
    simulation_type: str,
    persona_group_ids: list[str],
    prompt_question: str = "",
    survey_schema: dict | None = None,
    idi_script_text: str = "",
    briefing_ids: list[str] | None = None,
) -> str:
    """
    Start a market simulation in Boses. Returns immediately with a simulation_id.
    Use get_simulation_status to poll until complete, then get_simulation_results.

    Simulation types:
    - "concept_test": React to a concept, ad copy, product idea. Requires prompt_question.
    - "focus_group": Group discussion around a topic. Requires prompt_question.
    - "survey": Structured questionnaire. Requires survey_schema (JSON with questions array).
    - "idi_ai": AI-conducted in-depth interview. Optional idi_script_text.
    - "conjoint": Conjoint analysis for feature/price tradeoffs. Requires prompt_question (product category).

    IMPORTANT — handling uploaded files:
    - If the user shares a survey questionnaire document → parse the questions out of it
      and pass them as survey_schema. Do NOT store it as a briefing.
      survey_schema format: {"questions": [{"id": "q1", "text": "...", "type": "likert|open|multiple_choice", "options": [...]}]}
    - If the user shares a background/context document (brand guide, product spec, etc.)
      → call create_briefing first, then pass the returned ID in briefing_ids.

    Args:
        project_id: The ID of the project.
        simulation_type: One of "concept_test", "focus_group", "survey", "idi_ai", "conjoint".
        persona_group_ids: List of persona group IDs to use as the audience.
        prompt_question: The research question or concept to test (required for most types).
        survey_schema: For survey type — a dict with a "questions" array (see format above).
        idi_script_text: For idi_ai — optional interview script or topic guide.
        briefing_ids: Optional list of briefing document IDs to include as context.
    """
    _audit("run_simulation")
    payload: dict = {
        "simulation_type": simulation_type,
        "persona_group_ids": persona_group_ids,
    }
    if prompt_question:
        payload["prompt_question"] = prompt_question
    if survey_schema:
        payload["survey_schema"] = survey_schema
    if idi_script_text:
        payload["idi_script_text"] = idi_script_text
    if briefing_ids:
        payload["briefing_ids"] = briefing_ids

    sim = await client.create_simulation(project_id, payload)
    sim_id = sim["id"]
    return (
        f"Simulation started.\n"
        f"- ID: {sim_id}\n"
        f"- Type: {simulation_type}\n"
        f"- Status: {sim.get('status', 'pending')}\n"
        f"Now call get_simulation_status(project_id='{project_id}', simulation_id='{sim_id}') "
        f"every 15 seconds until status is 'complete'."
    )


# ---------------------------------------------------------------------------
# 11. abort_simulation
# ---------------------------------------------------------------------------

@mcp.tool()
async def abort_simulation(project_id: str, simulation_id: str) -> str:
    """
    Abort a running simulation immediately.
    Use this if the simulation is taking too long or was started by mistake.
    Aborted simulations cannot be resumed.

    Args:
        project_id: The ID of the project.
        simulation_id: The ID of the simulation to abort.
    """
    _audit("abort_simulation")
    await client.abort_simulation(project_id, simulation_id)
    return f"Simulation '{simulation_id}' has been aborted."


# ---------------------------------------------------------------------------
# 12. get_simulation_status
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_simulation_status(project_id: str, simulation_id: str) -> str:
    """
    Check the current status of a simulation.
    Poll every 10–15 seconds until status is "complete" or "failed".

    Possible statuses:
    - "pending" / "running" / "generating_report" — still in progress, keep polling
    - "complete" — finished, call get_simulation_results now
    - "failed" — something went wrong

    Args:
        project_id: The ID of the project.
        simulation_id: The ID of the simulation (from run_simulation).
    """
    _audit("get_simulation_status")
    sim = await client.get_simulation(project_id, simulation_id)
    status = sim.get("status", "unknown")
    progress = sim.get("progress") or {}

    if status == "complete":
        return f"Simulation is complete. Call get_simulation_results now."

    if status == "failed":
        error = sim.get("error_message", "Unknown error")
        return f"Simulation failed: {error}"

    # Show progress if available
    current = progress.get("current", 0)
    total = progress.get("total", "?")
    current_name = progress.get("current_name", "")
    msg = f"Status: {status}"
    if total and total != "?":
        msg += f" ({current}/{total} personas"
        if current_name:
            msg += f", currently: {current_name}"
        msg += ")"
    msg += ". Keep polling every 15 seconds."
    return msg


# ---------------------------------------------------------------------------
# 13. get_simulation_results
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_simulation_results(project_id: str, simulation_id: str) -> str:
    """
    Get a plain-English summary of simulation results.
    Only call this after get_simulation_status returns "complete".

    Returns: dominant sentiment, full sentiment distribution, top themes,
    key recommendations, and a narrative summary.

    Args:
        project_id: The ID of the project.
        simulation_id: The ID of the simulation.
    """
    _audit("get_simulation_results")
    results = await client.get_simulation_results(project_id, simulation_id)
    if not results:
        return "No results found. The simulation may still be running."

    # Find the aggregate result
    aggregate = next(
        (r for r in results if r.get("result_type") in (
            "aggregate", "focus_group_aggregate", "idi_aggregate",
            "survey_aggregate", "conjoint_aggregate",
        )),
        None,
    )

    individual_results = [r for r in results if r.get("result_type") in (
        "individual", "idi_individual", "survey_response",
    )]

    lines: list[str] = []

    if aggregate:
        # Sentiment distribution
        dist = aggregate.get("sentiment_distribution") or {}
        if dist:
            total = sum(v for v in dist.values() if isinstance(v, (int, float)))
            if total > 0:
                pct = {k: round(v / total * 100) for k, v in dist.items() if isinstance(v, (int, float))}
                dominant = max(pct, key=lambda k: pct[k])
                lines.append(f"**Dominant sentiment: {dominant}**")
                dist_str = " | ".join(f"{k}: {v}%" for k, v in sorted(pct.items(), key=lambda x: -x[1]))
                lines.append(f"Distribution: {dist_str}")
            lines.append("")

        # Top themes
        themes = aggregate.get("top_themes") or []
        report = aggregate.get("report_sections") or {}
        if not themes and report:
            themes = report.get("cross_persona_themes") or report.get("themes") or report.get("top_themes") or []
        if themes:
            lines.append(f"**Top themes:** {', '.join(themes[:8])}")
            lines.append("")

        # Summary
        summary = aggregate.get("summary_text") or report.get("executive_summary") or report.get("summary") or ""
        if summary:
            lines.append("**Summary:**")
            lines.append(summary[:800] + ("…" if len(summary) > 800 else ""))
            lines.append("")

        # Recommendations
        recs = aggregate.get("recommendations") or report.get("recommendations") or ""
        if recs:
            lines.append("**Recommendations:**")
            lines.append(recs[:600] + ("…" if len(recs) > 600 else ""))
            lines.append("")

    # Individual breakdown (top 3)
    if individual_results:
        lines.append(f"**Individual responses ({len(individual_results)} personas):**")
        sentiments: dict[str, int] = {}
        for r in individual_results:
            s = r.get("sentiment", "Unknown")
            sentiments[s] = sentiments.get(s, 0) + 1
        for s, count in sorted(sentiments.items(), key=lambda x: -x[1]):
            lines.append(f"  - {s}: {count} persona(s)")
        lines.append("")

    if not lines:
        return "Results are available but no structured data was found. View the full report in the Boses app."

    lines.append(f"For charts, per-persona details, and the full report → call get_simulation_url.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 14. get_simulation_url
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_simulation_url(project_id: str, simulation_id: str) -> str:
    """
    Get the direct URL to the full Boses results page for this simulation.
    Always call this at the end of any simulation workflow and include the link in your response.
    The Boses app shows charts, per-persona breakdowns, themes, and export options.

    Args:
        project_id: The ID of the project.
        simulation_id: The ID of the simulation.
    """
    _audit("get_simulation_url")
    url = f"{BOSES_APP_URL}/projects/{project_id}/simulations/{simulation_id}"
    return f"Full results in Boses: {url}"


# ---------------------------------------------------------------------------
# 15. get_workspace_info
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_workspace_info() -> str:
    """
    Get a quick overview of the current Boses workspace: project names and IDs.
    Use this as a starting point — then call list_persona_groups, list_simulations,
    or list_briefings on a specific project_id for more detail.
    """
    _audit("get_workspace_info")
    projects = await client.list_projects()
    if not projects:
        return "Workspace is empty — no projects yet. Call create_project to get started."

    lines = [f"**Workspace has {len(projects)} project(s):**"]
    for p in projects:
        lines.append(f"- {p['name']} (id: {p['id']})")
    lines.append("\nUse list_persona_groups, list_simulations, or list_briefings with a project_id to dive deeper.")
    return "\n".join(lines)

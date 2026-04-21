"""
Per-company Slack notifications via Incoming Webhooks.

Called fire-and-forget after a simulation completes or fails.
Each company configures its own webhook URL in Settings → Integrations.
"""
import logging
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

APP_URL = "https://app.temujintechnologies.com"

_SIMULATION_TYPE_LABELS = {
    "concept_test": "Concept Test",
    "survey": "Survey",
    "focus_group": "Focus Group",
    "idi_ai": "In-Depth Interview (AI)",
    "idi_manual": "In-Depth Interview (Manual)",
    "conjoint": "Conjoint Analysis",
}


def notify_simulation_complete(
    *,
    webhook_url: str,
    simulation_id: str,
    project_id: str,
    project_name: str,
    simulation_type: str,
    persona_count: int,
    status: str,  # "complete" | "failed"
    error_message: Optional[str] = None,
) -> None:
    """POST a Slack Block Kit message to the company webhook. Swallows all errors."""
    try:
        label = _SIMULATION_TYPE_LABELS.get(simulation_type, simulation_type)
        results_url = f"{APP_URL}/projects/{project_id}/simulations/{simulation_id}"

        if status == "complete":
            header_text = f":white_check_mark: Simulation complete"
            color = "#22c55e"
            body_text = (
                f"*{label}* across *{persona_count} persona{'s' if persona_count != 1 else ''}* "
                f"finished successfully."
            )
        else:
            header_text = f":x: Simulation failed"
            color = "#ef4444"
            body_text = error_message or "An unexpected error occurred."

        payload = {
            "attachments": [
                {
                    "color": color,
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"*{header_text}*\n{body_text}",
                            },
                        },
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"Project: *{project_name}*",
                                }
                            ],
                        },
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {"type": "plain_text", "text": "View results"},
                                    "url": results_url,
                                    "style": "primary",
                                }
                            ],
                        },
                    ],
                }
            ]
        }

        with httpx.Client(timeout=10) as client:
            resp = client.post(webhook_url, json=payload)
            if resp.status_code != 200:
                logger.warning(
                    f"Slack webhook returned {resp.status_code} for sim {simulation_id[:8]}: {resp.text[:200]}"
                )

    except Exception as e:
        logger.warning(f"Slack notification skipped for sim {simulation_id[:8]}: {e}")


def maybe_notify_slack(simulation_id: str, status: str) -> None:
    """
    Look up the simulation's company webhook URL and send a notification if configured.
    Creates its own DB session — safe to call from background threads.
    """
    try:
        from app.database import SessionLocal
        from app.models.simulation import Simulation
        from app.models.project import Project
        from app.models.company import Company

        db = SessionLocal()
        try:
            simulation = db.get(Simulation, simulation_id)
            if not simulation:
                return

            project = db.get(Project, str(simulation.project_id))
            if not project or not project.company_id:
                return

            company = db.get(Company, str(project.company_id))
            if not company or not company.slack_webhook_url:
                return

            # Count personas across all linked groups
            persona_count = 0
            from app.models.persona import Persona
            from sqlalchemy import select, func
            group_ids = [g.id for g in (simulation.persona_groups or [])]
            if not group_ids and simulation.persona_group_id:
                group_ids = [simulation.persona_group_id]
            if group_ids:
                persona_count = db.execute(
                    select(func.count()).where(Persona.persona_group_id.in_(group_ids))
                ).scalar() or 0

            notify_simulation_complete(
                webhook_url=company.slack_webhook_url,
                simulation_id=simulation_id,
                project_id=str(project.id),
                project_name=project.name,
                simulation_type=simulation.simulation_type,
                persona_count=persona_count,
                status=status,
                error_message=simulation.error_message if status == "failed" else None,
            )
        finally:
            db.close()

    except Exception as e:
        logger.warning(f"maybe_notify_slack failed for sim {simulation_id[:8]}: {e}")

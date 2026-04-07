"""
slack_notifier.py

Sends Slack webhook notifications when simulations complete or fail.
Set SLACK_WEBHOOK_URL in .env to enable. No-op if unset.

Uses only stdlib (json + urllib) — no extra dependencies.
"""
import json
import logging
import urllib.request

from app.config import settings

logger = logging.getLogger(__name__)

_SIM_TYPE_LABELS = {
    "concept_test": "Concept Test",
    "idi_ai": "In-Depth Interview (AI)",
    "idi_manual": "In-Depth Interview (Manual)",
    "survey": "Survey",
    "focus_group": "Focus Group",
    "conjoint": "Conjoint Analysis",
}


def notify_simulation_complete(simulation_id: str) -> None:
    """
    Send a Slack Block Kit notification for a completed or failed simulation.

    No-op if SLACK_WEBHOOK_URL is not configured.
    Always safe to call — swallows all exceptions internally.
    """
    if not settings.SLACK_WEBHOOK_URL:
        return

    try:
        from app.database import SessionLocal
        from app.models.simulation import Simulation

        db = SessionLocal()
        try:
            simulation = db.get(Simulation, simulation_id)
            if not simulation:
                logger.warning(f"[slack] Simulation {simulation_id[:8]} not found — skipping notification")
                return

            # Resolve all values inside the session before closing
            project_name = simulation.project.name if simulation.project else "Unknown project"
            group_name = simulation.persona_group.name if simulation.persona_group else "Unknown group"
            sim_type = simulation.simulation_type
            status = simulation.status
            error_message = simulation.error_message or "An unexpected error occurred"
            result_count = len(simulation.results)
        finally:
            db.close()

        sim_type_label = _SIM_TYPE_LABELS.get(sim_type, sim_type)

        if status == "complete":
            color = "#36a64f"
            header_text = "✅  Simulation complete"
            body_text = f"*{result_count} persona response{'s' if result_count != 1 else ''}* generated"
        else:
            color = "#e01e5a"
            header_text = "❌  Simulation failed"
            body_text = error_message

        payload = {
            "attachments": [
                {
                    "color": color,
                    "blocks": [
                        {
                            "type": "header",
                            "text": {"type": "plain_text", "text": header_text, "emoji": True},
                        },
                        {
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": body_text},
                        },
                        {
                            "type": "section",
                            "fields": [
                                {"type": "mrkdwn", "text": f"*Project*\n{project_name}"},
                                {"type": "mrkdwn", "text": f"*Simulation Type*\n{sim_type_label}"},
                                {"type": "mrkdwn", "text": f"*Persona Group*\n{group_name}"},
                            ],
                        },
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {"type": "plain_text", "text": "Open Boses"},
                                    "url": "https://app.temujintechnologies.com",
                                    "style": "primary",
                                }
                            ],
                        },
                    ],
                }
            ]
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            settings.SLACK_WEBHOOK_URL,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            logger.info(
                f"[slack] Notification sent for simulation {simulation_id[:8]} "
                f"(status={status}, http={resp.status})"
            )

    except Exception as e:
        logger.warning(f"[slack] Notification failed for simulation {simulation_id[:8]}: {e}")

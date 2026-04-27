"""Email notifications via Resend — fire-and-forget, all exceptions swallowed."""
import logging

logger = logging.getLogger(__name__)


def send_invite_email(to_email: str, invite_url: str) -> None:
    """Send an invite email with a one-time signup link."""
    try:
        from app.config import settings
        if not getattr(settings, "RESEND_API_KEY", ""):
            logger.warning("RESEND_API_KEY not set — invite email not sent to %s", to_email)
            return

        import resend
        resend.api_key = settings.RESEND_API_KEY

        resend.Emails.send({
            "from": "Jerome at Boses <jerome@temujintechnologies.com>",
            "to": [to_email],
            "subject": "You're invited to try Boses",
            "html": f"""
<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f9fafb; margin: 0; padding: 40px 0;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0" style="background: #ffffff; border-radius: 12px; padding: 40px; border: 1px solid #e5e7eb;">
          <tr>
            <td>
              <p style="margin: 0 0 4px; font-size: 13px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em;">Boses</p>
              <h1 style="margin: 0 0 16px; font-size: 22px; font-weight: 600; color: #111827;">You're invited</h1>
              <p style="margin: 0 0 8px; font-size: 15px; color: #374151;">
                Great speaking with you. Here's your personal invite link to get started with Boses.
              </p>
              <p style="margin: 0 0 32px; font-size: 14px; color: #6b7280;">
                This link is single-use and expires in 7 days.
              </p>
              <a href="{invite_url}"
                 style="display: inline-block; background: #111827; color: #ffffff; text-decoration: none;
                        padding: 12px 24px; border-radius: 8px; font-size: 15px; font-weight: 500;">
                Create your account →
              </a>
              <hr style="margin: 40px 0; border: none; border-top: 1px solid #e5e7eb;" />
              <p style="margin: 0; font-size: 13px; color: #9ca3af;">
                If you weren't expecting this, you can safely ignore it.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
""",
        })
        logger.info("Sent invite email to %s", to_email)
    except Exception as e:
        logger.warning("Invite email failed for %s: %s", to_email, e)
        raise


def send_workspace_invite_email(
    to_email: str,
    invite_url: str,
    company_name: str,
    inviter_name: str,
) -> None:
    """Send a workspace invite email from a company admin to a colleague."""
    try:
        from app.config import settings
        if not getattr(settings, "RESEND_API_KEY", ""):
            logger.warning("RESEND_API_KEY not set — workspace invite email not sent to %s", to_email)
            return

        import resend
        resend.api_key = settings.RESEND_API_KEY

        resend.Emails.send({
            "from": "Boses <notifications@temujintechnologies.com>",
            "to": [to_email],
            "subject": f"{inviter_name} invited you to join {company_name} on Boses",
            "html": f"""
<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f9fafb; margin: 0; padding: 40px 0;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0" style="background: #ffffff; border-radius: 12px; padding: 40px; border: 1px solid #e5e7eb;">
          <tr>
            <td>
              <p style="margin: 0 0 4px; font-size: 13px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em;">Boses</p>
              <h1 style="margin: 0 0 16px; font-size: 22px; font-weight: 600; color: #111827;">You're invited to join {company_name}</h1>
              <p style="margin: 0 0 8px; font-size: 15px; color: #374151;">
                <strong>{inviter_name}</strong> has invited you to collaborate on <strong>{company_name}</strong>'s workspace on Boses — an AI market simulation platform.
              </p>
              <p style="margin: 0 0 32px; font-size: 14px; color: #6b7280;">
                This invite link expires in 7 days.
              </p>
              <a href="{invite_url}"
                 style="display: inline-block; background: #111827; color: #ffffff; text-decoration: none;
                        padding: 12px 24px; border-radius: 8px; font-size: 15px; font-weight: 500;">
                Join workspace →
              </a>
              <hr style="margin: 40px 0; border: none; border-top: 1px solid #e5e7eb;" />
              <p style="margin: 0; font-size: 13px; color: #9ca3af;">
                If you weren't expecting this invite, you can safely ignore it.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
""",
        })
        logger.info("Sent workspace invite email to %s", to_email)
    except Exception as e:
        logger.warning("Workspace invite email failed for %s: %s", to_email, e)
        raise


def maybe_notify_email(simulation_id: str, status: str) -> None:
    """Send a simulation-complete email to the owning user, if Resend is configured."""
    try:
        from app.config import settings
        if not getattr(settings, "RESEND_API_KEY", ""):
            return

        from app.database import SessionLocal
        from app.models.simulation import Simulation
        from app.models.project import Project
        from app.models.company import Company
        from app.models.user import User
        from sqlalchemy import select

        db = SessionLocal()
        try:
            sim = db.get(Simulation, simulation_id)
            if not sim:
                return

            project = db.get(Project, sim.project_id)
            if not project:
                return

            company = db.get(Company, project.company_id)
            if not company:
                return

            # Get all users in the company to notify
            users = db.execute(
                select(User).where(User.company_id == company.id)
            ).scalars().all()
            if not users:
                return

            share_url = (
                f"{settings.FRONTEND_URL}/share/{sim.share_token}"
                if sim.share_token
                else f"{settings.FRONTEND_URL}/projects/{sim.project_id}/simulations/{simulation_id}"
            )

            sim_type_label = {
                "concept_test": "Concept Test",
                "focus_group": "Focus Group",
                "idi_ai": "In-Depth Interview",
                "idi_manual": "Manual IDI",
                "survey": "Survey",
                "conjoint": "Conjoint Analysis",
            }.get(sim.simulation_type, sim.simulation_type.replace("_", " ").title())

            status_label = "completed" if status == "complete" else status

            for user in users:
                _send_completion_email(
                    to_email=user.email,
                    project_name=project.name,
                    sim_type=sim_type_label,
                    status_label=status_label,
                    results_url=share_url,
                )
        finally:
            db.close()

    except Exception as e:
        logger.warning(f"Email notification skipped for {simulation_id[:8]}: {e}")


def _send_completion_email(
    to_email: str,
    project_name: str,
    sim_type: str,
    status_label: str,
    results_url: str,
) -> None:
    import resend
    from app.config import settings

    resend.api_key = settings.RESEND_API_KEY

    resend.Emails.send({
        "from": "Boses <notifications@temujintechnologies.com>",
        "to": [to_email],
        "subject": f"Your {sim_type} simulation is {status_label}",
        "html": f"""
<!DOCTYPE html>
<html>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f9fafb; margin: 0; padding: 40px 0;">
  <table width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td align="center">
        <table width="560" cellpadding="0" cellspacing="0" style="background: #ffffff; border-radius: 12px; padding: 40px; border: 1px solid #e5e7eb;">
          <tr>
            <td>
              <p style="margin: 0 0 4px; font-size: 13px; color: #6b7280; text-transform: uppercase; letter-spacing: 0.05em;">Boses</p>
              <h1 style="margin: 0 0 24px; font-size: 22px; font-weight: 600; color: #111827;">Your simulation is ready</h1>
              <p style="margin: 0 0 8px; font-size: 15px; color: #374151;">
                Your <strong>{sim_type}</strong> simulation for <strong>{project_name}</strong> has {status_label}.
              </p>
              <p style="margin: 0 0 32px; font-size: 15px; color: #374151;">
                Click below to view the results.
              </p>
              <a href="{results_url}"
                 style="display: inline-block; background: #111827; color: #ffffff; text-decoration: none;
                        padding: 12px 24px; border-radius: 8px; font-size: 15px; font-weight: 500;">
                View results →
              </a>
              <hr style="margin: 40px 0; border: none; border-top: 1px solid #e5e7eb;" />
              <p style="margin: 0; font-size: 13px; color: #9ca3af;">
                You're receiving this because you have a Boses account. Manage notifications in
                <a href="{settings.FRONTEND_URL}/settings" style="color: #6b7280;">Settings</a>.
              </p>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
""",
    })
    logger.info(f"Sent completion email to {to_email}")

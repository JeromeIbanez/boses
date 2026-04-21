"""
Avatar generation service.

Generates a photorealistic headshot for each persona using gpt-image-1 and
stores it persistently, returning a URL for the image.

Storage (production): Supabase Storage bucket — avatars/{persona_id}.png
  Public URL: {SUPABASE_URL}/storage/v1/object/public/{bucket}/avatars/{persona_id}.png

Storage (local dev fallback): {UPLOAD_DIR}/avatars/{persona_id}.png
  Served at: /uploads/avatars/{persona_id}.png
"""
import base64
import logging
import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

from openai import OpenAI

from app.config import settings
from app.database import SessionLocal

logger = logging.getLogger(__name__)

_GENDER_MAP = {
    "male": "man",
    "female": "woman",
    "non-binary": "person",
    "Male": "man",
    "Female": "woman",
}

# Maps location keywords to ethnic/cultural descriptors so each market
# produces visually distinct, culturally accurate portraits.
_ETHNICITY_HINTS: list[tuple[list[str], str]] = [
    (["philippines", "manila", "cebu", "davao", "quezon", "makati", "bgc", "ortigas"], "Filipino"),
    (["indonesia", "jakarta", "bali", "surabaya", "bandung", "yogyakarta"], "Indonesian"),
    (["vietnam", "ho chi minh", "hanoi", "saigon", "da nang", "hue"], "Vietnamese"),
    (["thailand", "bangkok", "chiang mai", "phuket"], "Thai"),
    (["malaysia", "kuala lumpur", "kl", "penang", "johor"], "Malaysian"),
    (["singapore"], "Singaporean"),
    (["india", "mumbai", "delhi", "bangalore", "chennai", "hyderabad"], "South Asian Indian"),
]


def _ethnicity_hint(location: str) -> str:
    loc = location.lower()
    for keywords, descriptor in _ETHNICITY_HINTS:
        if any(kw in loc for kw in keywords):
            return descriptor
    return ""


def _build_prompt(persona) -> str:
    gender_word = _GENDER_MAP.get(persona.gender, "person")
    ethnicity = _ethnicity_hint(persona.location or "")

    # ── No-text constraint first ──────────────────────────────────────────────
    no_text = (
        "A photorealistic studio portrait photograph. "
        "No text, no words, no letters, no labels, no watermarks, no overlays of any kind anywhere in the image."
    )

    # ── Subject ───────────────────────────────────────────────────────────────
    ethnicity_clause = f"{ethnicity} " if ethnicity else ""
    subject = f"Subject is a {ethnicity_clause}{gender_word}, {persona.age} years old."

    # ── Income → grooming and clothing quality ────────────────────────────────
    income_map = {
        "low": "modest, simple clothing",
        "lower-middle": "neat everyday clothing",
        "middle": "clean smart-casual clothing",
        "upper-middle": "polished professional attire",
        "high": "refined, well-tailored clothing",
    }
    income_key = (persona.income_level or "").lower().replace(" ", "-").replace("_", "-")
    clothing = income_map.get(income_key, "smart-casual clothing")
    clothing_line = f"Wearing {clothing}."

    # ── Personality traits → expression keywords ──────────────────────────────
    # Use pure adjectives — no label-colon patterns that DALL-E may render as text
    expression_line = ""
    if persona.personality_traits:
        traits = ", ".join(persona.personality_traits[:4])
        expression_line = f"Facial expression is {traits}."

    # ── Archetype → energy and bearing ───────────────────────────────────────
    archetype_line = ""
    if persona.archetype_label:
        archetype_line = f"Posture and energy embodies {persona.archetype_label}."

    # ── VALS segment → posture hint ───────────────────────────────────────────
    vals_line = ""
    if persona.psychographic_segment:
        vals_line = f"Demeanor reflects {persona.psychographic_segment} sensibility."

    # ── Shot style ────────────────────────────────────────────────────────────
    style = (
        "Neutral solid light grey background, soft natural lighting, "
        "upper body shot, subject looking directly at camera, sharp focus on face, "
        "photorealistic, high resolution, no props, nothing in background."
    )

    parts = [no_text, subject, clothing_line, expression_line, archetype_line, vals_line, style]
    return " ".join(p for p in parts if p)


def generate_avatar(client: OpenAI, persona) -> str | None:
    """
    Generate a gpt-image-1 headshot for the persona and save it locally.
    Returns the URL path (e.g. '/uploads/avatars/<id>.png') or None on failure.
    Never raises — avatar failure must not block persona generation.
    Retries up to 4 times on transient network errors (DNS, connection reset).
    """
    import httpx

    _TRANSIENT = (httpx.ConnectError, httpx.RemoteProtocolError, httpx.TimeoutException, OSError)
    max_attempts = 4
    _RETRY_DELAYS = [5, 15, 30]  # seconds; longer waits survive post-hibernate DNS recovery

    for attempt in range(1, max_attempts + 1):
        try:
            prompt = _build_prompt(persona)

            response = client.images.generate(
                model="gpt-image-1",
                prompt=prompt,
                size="1024x1024",
                quality="medium",
                n=1,
            )

            b64_data = response.data[0].b64_json
            if not b64_data:
                logger.warning(f"Empty b64 response for persona {persona.id}")
                return None

            image_bytes = base64.b64decode(b64_data)

            if settings.supabase_configured:
                key = f"avatars/{persona.id}.png"
                upload_url = f"{settings.SUPABASE_URL}/storage/v1/object/{settings.SUPABASE_AVATARS_BUCKET}/{key}"
                headers = {
                    "Authorization": f"Bearer {settings.SUPABASE_SERVICE_KEY}",
                    "Content-Type": "image/png",
                }
                resp = httpx.put(upload_url, content=image_bytes, headers=headers)
                resp.raise_for_status()
                return f"{settings.SUPABASE_URL}/storage/v1/object/public/{settings.SUPABASE_AVATARS_BUCKET}/{key}"
            else:
                avatars_dir = os.path.join(settings.UPLOAD_DIR, "avatars")
                os.makedirs(avatars_dir, exist_ok=True)
                file_path = os.path.join(avatars_dir, f"{persona.id}.png")
                with open(file_path, "wb") as f:
                    f.write(image_bytes)
                return f"/uploads/avatars/{persona.id}.png"

        except _TRANSIENT as e:
            if attempt < max_attempts:
                delay = _RETRY_DELAYS[attempt - 1]
                logger.warning(f"Avatar transient error for {persona.id} (attempt {attempt}/{max_attempts}), retrying in {delay}s: {e}")
                time.sleep(delay)
            else:
                logger.error(f"Avatar generation failed for persona {persona.id} after {max_attempts} attempts: {type(e).__name__}: {e}")
                return None
        except Exception as e:
            logger.error(f"Avatar generation failed for persona {persona.id}: {type(e).__name__}: {e}")
            return None


def _generate_and_save(client: OpenAI, persona_id: str) -> None:
    """
    Worker run in a thread: generate avatar, write to project persona,
    and propagate to the linked LibraryPersona if one exists.

    DB connections are held only during the brief read and write phases —
    not during the slow OpenAI call — so the connection isn't killed by
    the server's idle timeout mid-generation.
    """
    from app.models.library_persona import LibraryPersona
    from app.models.persona import Persona

    # Phase 1: read persona data, then immediately release the connection.
    pid = uuid.UUID(persona_id)
    db = SessionLocal()
    try:
        persona = db.get(Persona, pid)
        if not persona:
            return
        library_persona_id = persona.library_persona_id
        db.expunge(persona)
    except Exception as e:
        logger.warning(f"Background avatar worker failed for {persona_id} (fetch): {e}")
        return
    finally:
        db.close()

    # Phase 2: generate the avatar with no DB connection held.
    url = generate_avatar(client, persona)
    if not url:
        return

    # Phase 3: write back with a fresh connection.
    db = SessionLocal()
    try:
        persona = db.get(Persona, pid)
        if persona:
            persona.avatar_url = url
        if library_persona_id:
            lib = db.get(LibraryPersona, library_persona_id)
            if lib:
                lib.avatar_url = url
        db.commit()
    except Exception as e:
        logger.warning(f"Background avatar worker failed for {persona_id} (save): {e}")
        db.rollback()
    finally:
        db.close()


def generate_avatars_for_group(client: OpenAI, persona_ids: list[str]) -> None:
    """
    Generate avatars concurrently for a list of persona IDs.
    Called after group text generation is complete — does not block the main flow.
    Uses one thread per persona so all DALL-E calls run in parallel.
    """
    if not persona_ids:
        return
    with ThreadPoolExecutor(max_workers=min(len(persona_ids), 4)) as pool:
        futures = {pool.submit(_generate_and_save, client, pid): pid for pid in persona_ids}
        for future in as_completed(futures):
            pid = futures[future]
            try:
                future.result()
                logger.info(f"Avatar ready for persona {pid}")
            except Exception as e:
                logger.warning(f"Avatar future failed for {pid}: {e}")

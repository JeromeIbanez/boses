"""
Avatar generation service.

Generates a photorealistic headshot for each persona using DALL-E 3,
saves it to disk, and returns a path suitable for serving as a static file.

Storage: {UPLOAD_DIR}/avatars/{persona_id}.png
Served at: /uploads/avatars/{persona_id}.png

TODO: replace local file storage with S3 for production deployments.
"""
import base64
import logging
import os
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

    # ── Subject line ──────────────────────────────────────────────────────────
    ethnicity_clause = f"{ethnicity} " if ethnicity else ""
    subject = (
        f"Plain portrait photograph of a {ethnicity_clause}{gender_word}, "
        f"{persona.age} years old, from {persona.location}. "
        f"Name: {persona.full_name}. "          # anchors uniqueness per person
        f"Unique individual — distinct from any other portrait."
    )

    # ── Occupation & income — shapes grooming, clothing, bearing ─────────────
    occupation_line = f"Works as: {persona.occupation}. Income level: {persona.income_level}."

    # ── Psychographic & archetype — shapes expression and energy ─────────────
    psycho_parts = []
    if persona.archetype_label:
        psycho_parts.append(f"archetype: {persona.archetype_label}")
    if persona.psychographic_segment:
        psycho_parts.append(f"VALS segment: {persona.psychographic_segment}")
    psycho_line = f"Consumer profile — {', '.join(psycho_parts)}." if psycho_parts else ""

    # ── Personality traits — facial expression and mood ──────────────────────
    trait_line = ""
    if persona.personality_traits:
        trait_line = f"Personality: {', '.join(persona.personality_traits)}."

    # ── Aspirational identity — how they present themselves ──────────────────
    aspiration_line = ""
    if persona.aspirational_identity:
        # Keep it short — first sentence only
        first_sentence = persona.aspirational_identity.split(".")[0].strip()
        if first_sentence:
            aspiration_line = f"Self-image: {first_sentence}."

    # ── Family situation — age and life-stage visual cues ────────────────────
    family_line = ""
    if persona.family_situation:
        first_sentence = persona.family_situation.split(".")[0].strip()
        if first_sentence:
            family_line = f"Life stage: {first_sentence}."

    # ── Shot style — always plain portrait, never illustrative ───────────────
    style = (
        "Plain, photorealistic portrait. "
        "Neutral solid light grey background. "
        "Natural soft studio lighting. "
        "Upper body, looking directly at camera. "
        "No props, no text, no watermarks, no logos, no graphic elements. "
        "High-quality photography, sharp focus on face."
    )

    parts = [subject, occupation_line, psycho_line, trait_line, aspiration_line, family_line, style]
    return " ".join(p for p in parts if p)


def generate_avatar(client: OpenAI, persona) -> str | None:
    """
    Generate a DALL-E 3 headshot for the persona and save it locally.
    Returns the URL path (e.g. '/uploads/avatars/<id>.png') or None on failure.
    Never raises — avatar failure must not block persona generation.
    """
    try:
        prompt = _build_prompt(persona)

        response = client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size="1024x1024",
            quality="standard",
            response_format="b64_json",
            n=1,
        )

        b64_data = response.data[0].b64_json
        if not b64_data:
            logger.warning(f"Empty b64 response for persona {persona.id}")
            return None

        image_bytes = base64.b64decode(b64_data)

        avatars_dir = os.path.join(settings.UPLOAD_DIR, "avatars")
        os.makedirs(avatars_dir, exist_ok=True)
        file_path = os.path.join(avatars_dir, f"{persona.id}.png")

        with open(file_path, "wb") as f:
            f.write(image_bytes)

        return f"/uploads/avatars/{persona.id}.png"

    except Exception as e:
        logger.warning(f"Avatar generation failed for persona {persona.id}: {e}")
        return None


def _generate_and_save(client: OpenAI, persona_id: str) -> None:
    """Worker run in a thread: generate avatar and write avatar_url to DB."""
    from app.models.persona import Persona
    db = SessionLocal()
    try:
        persona = db.get(Persona, uuid.UUID(persona_id))
        if not persona:
            return
        url = generate_avatar(client, persona)
        if url:
            persona.avatar_url = url
            db.commit()
    except Exception as e:
        logger.warning(f"Background avatar worker failed for {persona_id}: {e}")
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
    with ThreadPoolExecutor(max_workers=len(persona_ids)) as pool:
        futures = {pool.submit(_generate_and_save, client, pid): pid for pid in persona_ids}
        for future in as_completed(futures):
            pid = futures[future]
            try:
                future.result()
                logger.info(f"Avatar ready for persona {pid}")
            except Exception as e:
                logger.warning(f"Avatar future failed for {pid}: {e}")

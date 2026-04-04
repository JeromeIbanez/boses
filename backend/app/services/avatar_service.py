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


def _build_prompt(persona) -> str:
    gender_word = _GENDER_MAP.get(persona.gender, "person")
    traits = ""
    if persona.personality_traits:
        # Take up to 2 positive-sounding traits for the visual prompt
        traits = ", ".join(persona.personality_traits[:2])
        traits = f" {traits}."

    return (
        f"Professional photorealistic headshot portrait of a {persona.age}-year-old {gender_word} "
        f"from {persona.location}, working as a {persona.occupation}.{traits} "
        f"Natural soft lighting, neutral light grey background, upper body framing, "
        f"looking directly at camera, high-quality photography, "
        f"appearance consistent with {persona.income_level} income level. "
        f"No text, no watermarks, no graphics."
    )


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

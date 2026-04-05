import base64

from openai import OpenAI
from pdfminer.high_level import extract_text as pdf_extract_text

from app.config import settings

_MIME_TYPES = {
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
    "gif": "image/gif",
}


def _analyze_image(file_path: str) -> str:
    with open(file_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")
    ext = file_path.rsplit(".", 1)[-1].lower()
    mime = _MIME_TYPES.get(ext, "image/png")
    client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": (
                        "You are a market research analyst. Describe this image in detail for use as a briefing "
                        "that AI consumer personas will react to in a simulated research study. Cover: what is shown, "
                        "the visual style and tone, any text or slogans visible, the apparent target audience, "
                        "and the key message being communicated. Be factual and descriptive."
                    ),
                },
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ],
        }],
        max_tokens=1000,
    )
    return response.choices[0].message.content or "[Image could not be analyzed]"


def extract_text(file_path: str, file_type: str) -> str | None:
    if file_type == "pdf":
        try:
            return pdf_extract_text(file_path)
        except Exception:
            return None
    elif file_type == "text":
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception:
            return None
    elif file_type == "image":
        try:
            return _analyze_image(file_path)
        except Exception:
            return "[Image uploaded but could not be analyzed. Add a text description for best results.]"
    return None

from pdfminer.high_level import extract_text as pdf_extract_text


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
        # For MVP, images are stored but text extraction is not performed.
        # Users should include image descriptions in their text briefings.
        return "[Image uploaded. For best simulation results, include a text description of this image in your briefing.]"
    return None

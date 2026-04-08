import base64
import os
import re
import shutil
import subprocess
import tempfile

from app.services.openai_client import get_openai_client
from pdfminer.high_level import extract_text as pdf_extract_text

from app.config import settings

# Resolved once at import time; None if ffmpeg is not installed.
_FFMPEG = shutil.which("ffmpeg")

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
    client = get_openai_client()
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


def _transcribe_audio(file_path: str) -> str:
    client = get_openai_client()
    with open(file_path, "rb") as f:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
        )
    return transcript.text


def _analyze_video(file_path: str) -> str:
    if not _FFMPEG:
        raise RuntimeError("ffmpeg not found — install it with: brew install ffmpeg (Mac) or apt-get install ffmpeg (Linux)")
    client = get_openai_client()
    frames_b64: list[str] = []
    transcript = ""

    # Extract key frames using system ffmpeg
    try:
        # Parse duration from ffmpeg's stderr output (no ffprobe needed)
        probe = subprocess.run(
            [_FFMPEG, "-i", file_path],
            capture_output=True, text=True, timeout=30,
        )
        match = re.search(r"Duration:\s*(\d+):(\d+):([\d.]+)", probe.stderr)
        if not match:
            raise ValueError("Could not parse video duration")
        h, m, s = int(match.group(1)), int(match.group(2)), float(match.group(3))
        duration = h * 3600 + m * 60 + s
        with tempfile.TemporaryDirectory() as tmpdir:
            num_frames = 4
            for i in range(num_frames):
                t = duration * (i + 1) / (num_frames + 1)
                frame_path = os.path.join(tmpdir, f"frame_{i}.jpg")
                subprocess.run(
                    [_FFMPEG, "-ss", str(t), "-i", file_path,
                     "-vframes", "1", "-q:v", "2", frame_path, "-y"],
                    capture_output=True, timeout=30,
                )
                if os.path.exists(frame_path):
                    with open(frame_path, "rb") as fh:
                        frames_b64.append(base64.b64encode(fh.read()).decode("utf-8"))
    except Exception:
        pass

    # Transcribe audio track with Whisper
    audio_tmp = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            audio_tmp = tmp.name
        subprocess.run(
            [_FFMPEG, "-i", file_path, "-vn", "-ar", "16000", "-ac", "1",
             "-b:a", "64k", audio_tmp, "-y"],
            capture_output=True, timeout=60,
        )
        if os.path.exists(audio_tmp) and os.path.getsize(audio_tmp) > 0:
            with open(audio_tmp, "rb") as fh:
                t = client.audio.transcriptions.create(model="whisper-1", file=fh)
                transcript = t.text
    except Exception:
        pass
    finally:
        if audio_tmp and os.path.exists(audio_tmp):
            os.unlink(audio_tmp)

    if not frames_b64 and not transcript:
        return "[Video could not be analyzed. Add a text description for best results.]"

    # Analyse with GPT-4o Vision (frames + transcript as context)
    prompt_text = (
        "You are a market research analyst. Analyze this video for use as a briefing "
        "that AI consumer personas will react to in a simulated research study. "
        "Cover: what is shown visually, the visual style and tone, any text or slogans visible, "
        "the apparent target audience, and the key message being communicated. Be factual and descriptive."
    )
    if transcript:
        prompt_text += f"\n\nAudio transcript: {transcript}"

    if frames_b64:
        content: list = [{"type": "text", "text": prompt_text}]
        for b64 in frames_b64:
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": content}],
            max_tokens=1200,
        )
    else:
        # No frames — summarise transcript only
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": (
                "You are a market research analyst. Summarize this video transcript for use as a briefing "
                "that AI consumer personas will react to in a simulated research study. "
                "Cover the key messages, tone, and apparent target audience.\n\n"
                f"Transcript: {transcript}"
            )}],
            max_tokens=1000,
        )

    analysis = response.choices[0].message.content or "[Video analysis unavailable]"
    if transcript:
        return f"{analysis}\n\nTranscript: {transcript}"
    return analysis


# ~12,000 chars ≈ 3,000 tokens — long enough to keep short briefs verbatim
_SUMMARY_CHAR_THRESHOLD = 12_000


def summarize_if_long(text: str, title: str) -> str | None:
    """
    Return an AI summary when text exceeds the threshold, else None.
    Called at upload time; result is cached in briefing.summary_text.
    """
    if not text or len(text) <= _SUMMARY_CHAR_THRESHOLD:
        return None
    client = get_openai_client()
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": (
                f"You are a market research analyst. The following is a briefing document titled \"{title}\".\n\n"
                "Summarize it concisely for use in a consumer research simulation. "
                "Preserve all key information that AI personas would need to react authentically: "
                "product or campaign details, key messages, target audience, value proposition, "
                "tone, and any specific claims or visuals described. "
                "Aim for ~400 words. Do not add commentary — just the summary.\n\n"
                f"{text[:60_000]}"  # hard cap to avoid absurdly large payloads
            ),
        }],
        max_tokens=600,
        temperature=0.3,
    )
    return response.choices[0].message.content or None


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
    elif file_type == "audio":
        try:
            return _transcribe_audio(file_path)
        except Exception:
            return "[Audio could not be transcribed. Add a text description for best results.]"
    elif file_type == "video":
        try:
            return _analyze_video(file_path)
        except Exception:
            return "[Video could not be analyzed. Add a text description for best results.]"
    return None

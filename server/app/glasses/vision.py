"""Vision AI provider — the only module that talks to the Claude API.

Kept inside `glasses/` because it exists to interpret photos coming from the
Meta AI glasses. Uses the official Anthropic SDK with structured outputs so we
get validated JSON back (no fragile string parsing).

Set VISION_PROVIDER=mock (or leave ANTHROPIC_API_KEY empty) to run the whole
pipeline without an API key — handy for local testing of the capture flow.
"""
import base64
import os

from pydantic import BaseModel

from ..config import config


# --- Structured output schemas (the model is forced to return these) ------


class ClassifyResult(BaseModel):
    type: str          # tasks | notes | receipt | event | unknown
    confidence: float  # 0..1


class ExtractedTask(BaseModel):
    text: str
    status: str        # todo | done
    confidence: float  # 0..1


class TaskList(BaseModel):
    tasks: list[ExtractedTask]


# --- Provider selection ---------------------------------------------------


def _use_mock() -> bool:
    return config.vision_provider == "mock" or not config.anthropic_api_key


_MEDIA_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def _encode_image(path: str) -> tuple[str, str]:
    ext = os.path.splitext(path)[1].lower()
    media_type = _MEDIA_TYPES.get(ext, "image/jpeg")
    with open(path, "rb") as f:
        data = base64.standard_b64encode(f.read()).decode("utf-8")
    return data, media_type


_client = None


def _anthropic():
    global _client
    if _client is None:
        import anthropic

        _client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    return _client


def _image_message(path: str, prompt: str) -> list[dict]:
    data, media_type = _encode_image(path)
    return [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {"type": "base64", "media_type": media_type, "data": data},
                },
                {"type": "text", "text": prompt},
            ],
        }
    ]


# --- Public API -----------------------------------------------------------


def classify(path: str, prompt: str) -> ClassifyResult:
    """Classify a photo into a PhotoType string + confidence."""
    if _use_mock():
        return ClassifyResult(type="tasks", confidence=0.95)

    resp = _anthropic().messages.parse(
        model=config.vision_model,
        max_tokens=1024,
        thinking={"type": "adaptive"},
        messages=_image_message(path, prompt),
        output_format=ClassifyResult,
    )
    return resp.parsed_output or ClassifyResult(type="unknown", confidence=0.0)


def extract_tasks(path: str, prompt: str) -> list[ExtractedTask]:
    """Read a handwritten task list photo into structured tasks."""
    if _use_mock():
        return [
            ExtractedTask(text="Buy groceries", status="todo", confidence=0.9),
            ExtractedTask(text="Email the team", status="todo", confidence=0.88),
            ExtractedTask(text="Morning run", status="done", confidence=0.92),
        ]

    resp = _anthropic().messages.parse(
        model=config.vision_model,
        max_tokens=4096,
        thinking={"type": "adaptive"},
        messages=_image_message(path, prompt),
        output_format=TaskList,
    )
    return resp.parsed_output.tasks if resp.parsed_output else []

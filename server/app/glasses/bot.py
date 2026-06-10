"""Voice/text write-back bot (phase 4).

The glasses can't call your server directly, but they *can* send a WhatsApp/
Messenger message by voice. This bot receives those messages and mutates state:

    "add: call dentist"  → add a task
    "done: review PRs"   → mark a task done
    "done: gym"          → log a habit (falls back to habit if no task matches)
    "log water"          → log a habit

Exposed as a webhook (`/bot`) the messaging platform calls. The command parser
(`handle_message`) is transport-agnostic, so it's trivially testable.
"""
import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from .. import renderer, store
from ..config import config

log = logging.getLogger(__name__)
router = APIRouter()

USAGE = "Try: 'add <task>', 'done <task or habit>', or 'log <habit>'."

_ADD_VERBS = ("add", "todo", "note")
_DONE_VERBS = ("done", "did", "finished", "completed", "complete")


def _strip_verb(text: str, verb: str) -> str:
    return text[len(verb):].lstrip(": ").strip()


def _refresh() -> None:
    store.bump_version()
    renderer.render()


def handle_message(text: str, sender: str = "?") -> str:
    """Parse a command and apply it. Returns a short reply."""
    raw = text.strip()
    low = raw.lower()
    log.info("bot message from %s: %r", sender, raw)

    for verb in _ADD_VERBS:
        if low.startswith(verb):
            arg = _strip_verb(raw, verb)
            if not arg:
                return USAGE
            n = store.add_tasks(
                [{"text": arg, "status": "todo", "confidence": 1.0}],
                source_photo="voice",
            )
            _refresh()
            return f"Added: {arg}" if n else f"Already on your list: {arg}"

    if low.startswith("log"):
        arg = _strip_verb(raw, "log")
        if not arg:
            return USAGE
        name = store.log_habit(arg)
        if name:
            _refresh()
            return f"Logged habit: {name}"
        return f"No habit named '{arg}'."

    for verb in _DONE_VERBS:
        if low.startswith(verb):
            arg = _strip_verb(raw, verb)
            if not arg:
                return USAGE
            task = store.mark_task_done(arg)
            if task:
                _refresh()
                return f"Done: {task}"
            habit = store.log_habit(arg)  # "done gym" → gym is a habit
            if habit:
                _refresh()
                return f"Logged habit: {habit}"
            return f"Couldn't find a task or habit matching '{arg}'."

    return USAGE


def _extract(payload: dict) -> tuple[str, str]:
    """Pull (text, sender) from either a generic body or a WhatsApp Cloud webhook."""
    if "text" in payload:  # generic: {"text": "...", "sender": "..."}
        return str(payload.get("text", "")), str(payload.get("sender", "?"))
    try:  # WhatsApp Cloud API message shape
        value = payload["entry"][0]["changes"][0]["value"]
        msg = value["messages"][0]
        return msg["text"]["body"], msg.get("from", "?")
    except (KeyError, IndexError, TypeError):
        return "", "?"


@router.get("/bot")
async def verify(request: Request) -> PlainTextResponse:
    """WhatsApp webhook verification handshake."""
    p = request.query_params
    if (
        p.get("hub.mode") == "subscribe"
        and config.whatsapp_verify_token
        and p.get("hub.verify_token") == config.whatsapp_verify_token
    ):
        return PlainTextResponse(p.get("hub.challenge", ""))
    return PlainTextResponse("forbidden", status_code=403)


@router.post("/bot")
async def receive(request: Request) -> JSONResponse:
    payload = await request.json()
    text, sender = _extract(payload)
    if not text.strip():
        return JSONResponse({"reply": USAGE})
    reply = handle_message(text, sender)
    # TODO: to send `reply` back to the user, POST to the WhatsApp Graph API
    #       using config.whatsapp_token. For now we just return it in the response.
    return JSONResponse({"reply": reply})

"""Voice/text write-back bot (phase 4).

The glasses can't call your server directly, but they *can* send a WhatsApp/
Messenger message by voice. This bot receives those messages and mutates state:

    "done: gym"          → mark habit/task done
    "add: call dentist"  → add a task
    "log water"          → increment a habit counter

Implemented as a webhook the messaging platform calls.
"""


def handle_message(text: str, sender: str) -> str:
    """Parse a command and apply it. Returns a short reply.

    TODO:
      - parse verb (done/add/log/move) + argument
      - call store mutators, then store.bump_version()
      - return a confirmation string
    """
    raise NotImplementedError("bot.handle_message — phase 4")

"""The public message board: the ONLY channel through which the agents can talk to each other."""

import asyncio
import json
import logging
import time
from dataclasses import asdict, dataclass
from pathlib import Path

log = logging.getLogger(__name__)


@dataclass
class Message:
    id: int  # 1-based, so board.messages[after_id:] are the messages newer than after_id
    author: str
    content: str
    time: float  # seconds since the board was created

    def render(self) -> str:
        minutes, seconds = divmod(int(self.time), 60)
        return f"#{self.id} [{minutes:02d}:{seconds:02d}] {self.author}: {self.content}"


class MessageBoard:
    def __init__(self, log_path: Path, label: str = ""):
        self.messages: list[Message] = []
        self.log_path = log_path  # board.jsonl: one JSON record per message
        self.text_path = log_path.with_suffix(".txt")  # board.txt: the same messages, rendered for reading
        self.label = label
        self.start = time.monotonic()
        self._changed = asyncio.Event()

    def post(self, author: str, content: str) -> Message:
        message = Message(len(self.messages) + 1, author, content, round(time.monotonic() - self.start, 1))
        self.messages.append(message)
        with self.log_path.open("a") as f:
            f.write(json.dumps(asdict(message), ensure_ascii=False) + "\n")
        with self.text_path.open("a") as f:
            f.write(message.render() + "\n\n")
        log.info("[%s] %s", self.label, message.render()[:300])
        # Wake everyone waiting for a post, and give the next waiters a fresh event.
        changed, self._changed = self._changed, asyncio.Event()
        changed.set()
        return message

    def unread(self, reader: str, after_id: int) -> list[Message]:
        """Messages newer than the reader's cursor, without the reader's own posts."""
        return [m for m in self.messages[after_id:] if m.author != reader]

    async def wait_for_unread(self, reader: str, after_id: int, timeout: float) -> list[Message]:
        deadline = time.monotonic() + timeout
        while not self.unread(reader, after_id):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                await asyncio.wait_for(self._changed.wait(), remaining)
            except TimeoutError:
                break
        return self.unread(reader, after_id)

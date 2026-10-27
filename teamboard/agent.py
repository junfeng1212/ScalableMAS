"""One agent: an LLM in a tool-calling loop, with its own sandbox and access to the public board."""

import json
import time
from collections import Counter
from pathlib import Path

# Stop reasons after which retrying with a reminder makes no sense (all providers).
ABNORMAL_STOPS = {"refusal", "max_tokens", "model_context_window_exceeded", "incomplete", "length"}

NO_TOOL_REMINDER = (
    "You did not call any tool. Keep working with your tools, coordinate through the message board, "
    "and call finish when the answer is well supported."
)


class Agent:
    def __init__(self, name: str, llm, toolbox, max_steps: int, trace_path: Path):
        self.name = name
        self.llm = llm
        self.toolbox = toolbox
        self.max_steps = max_steps
        self.trace_path = trace_path
        self.steps = 0
        self.usage = Counter()
        self.start = time.monotonic()

    async def run(self, task: str) -> str:
        """Works on the task until it calls finish; returns how the agent stopped."""
        self.llm.add_user(task)
        for step in range(1, self.max_steps + 1):
            self.steps = step
            reply = await self.llm.step()
            self.usage.update(reply.usage)

            if not reply.tool_calls:
                self.trace(step, reply, [])
                if reply.stop_reason in ABNORMAL_STOPS:
                    return f"stopped:{reply.stop_reason}"
                self.llm.add_user(NO_TOOL_REMINDER)
                continue

            outputs = [await self.toolbox.execute(call) for call in reply.tool_calls]
            self.trace(step, reply, outputs)
            if self.toolbox.finished:
                return "finished"
            # Reminders go into the last tool output rather than a separate user turn.
            note = self.toolbox.status_note(step, self.max_steps)
            if note:
                outputs[-1] += "\n\n" + note
            self.llm.add_tool_results([(call.id, output) for call, output in zip(reply.tool_calls, outputs)])
        return "max_steps"

    def trace(self, step: int, reply, outputs: list[str]) -> None:
        record = {
            "step": step,
            "time": round(time.monotonic() - self.start, 1),
            "reasoning": reply.reasoning,
            "text": reply.text,
            "tool_calls": [
                {"name": call.name, "args": call.args, "output": output} for call, output in zip(reply.tool_calls, outputs)
            ],
            "stop_reason": reply.stop_reason,
            "usage": reply.usage,
        }
        with self.trace_path.open("a") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

"""End-to-end run of one query with scripted LLMs, a fake retriever and fake sandboxes."""

import asyncio
import json
from pathlib import Path

from teamboard.config import load_config
from teamboard.llm import LLMReply, ToolCall, ToolSpec
from teamboard.team import run_query

ROOT = Path(__file__).resolve().parents[1]

SCRIPTS = {
    "Bob": [
        ("search", {"query": "first crewed moon landing"}),
        ("bash", {"command": "echo 'Apollo 11, doc 42' >> notes.txt"}),
        ("post_message", {"content": "doc 42 says Apollo 11 landed first. I will finish."}),
        ("finish", {"explanation": "Apollo 11 landed in 1969 [42].", "exact_answer": "Apollo 11", "confidence": "90%"}),
    ],
    "Eric": [],  # only waits on the board: see FakeLLM.step
}


class FakeLLM:
    """Replays a script of tool calls; once the script is over, it keeps waiting for board posts."""

    def __init__(self, script):
        self.script = list(script)
        self.inputs = []

    def add_user(self, text):
        self.inputs.append(text)

    def add_tool_results(self, results):
        self.inputs += [output for _, output in results]

    async def step(self):
        name, args = self.script.pop(0) if self.script else ("read_messages", {"wait_seconds": 30})
        call = ToolCall(f"call-{len(self.inputs)}", name, args)
        return LLMReply(text="", tool_calls=[call], usage={"input_tokens": 1, "output_tokens": 1}, stop_reason="tool_use")


class FakeRetriever:
    tool_specs = [ToolSpec("search", "Search the corpus.", {"type": "object", "properties": {"query": {"type": "string"}}})]

    async def call(self, name, args):
        return '[{"docid": "42", "score": 9.1, "snippet": "Apollo 11 ..."}]', ["42"]


class FakeSandbox:
    def __init__(self, container, workspace, cfg, experiment):
        pass

    async def start(self):
        pass

    async def run(self, command):
        return "\n[exit code 0]"

    async def stop(self):
        pass


def test_first_finisher_ends_the_team(tmp_path):
    cfg = load_config(ROOT / "configs/default.yaml")
    (tmp_path / "system.md").write_text("{name}")  # the system prompt is just the agent's name
    cfg["team"].update(
        agents=["Bob", "Eric"],
        system_prompt=str(tmp_path / "system.md"),
        task_prompt=str(ROOT / "prompts/task.md"),
        time_limit_minutes=1,
    )
    cfg["llm"] = {"provider": "fake", "model": "fake-model"}
    llms = {}

    def make_fake_llm(llm_cfg, system_prompt, tool_specs):
        llms[system_prompt] = FakeLLM(SCRIPTS[system_prompt])
        return llms[system_prompt]

    result = asyncio.run(
        run_query(cfg, "q1", "Which mission landed on the moon first?", FakeRetriever(), tmp_path,
                  make_llm=make_fake_llm, make_sandbox=FakeSandbox)
    )

    assert result == json.loads((tmp_path / "results/q1.json").read_text())
    assert result["status"] == "completed"
    assert result["metadata"]["winner"] == "Bob"
    assert result["metadata"]["per_agent"]["Eric"]["status"] == "cancelled"
    assert result["result"][-1]["type"] == "output_text"
    assert "Exact Answer: Apollo 11" in result["result"][-1]["output"]
    assert result["retrieved_docids"] == ["42"]
    assert result["tool_call_counts"]["finish"] == 1
    # Eric learned Bob's finding only through the board.
    assert any("doc 42 says Apollo 11" in text for text in llms["Eric"].inputs)
    board = [json.loads(line) for line in (tmp_path / "traces/q1/board.jsonl").read_text().splitlines()]
    assert [(m["author"], m["id"]) for m in board] == [("Bob", 1)]

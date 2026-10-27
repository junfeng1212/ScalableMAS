"""Run one BrowseComp-Plus query with a team of agents that can only talk through the message board."""

import asyncio
import json
import logging
import os
import re
import shutil
import time
import uuid
from collections import Counter
from pathlib import Path

from teamboard.agent import Agent
from teamboard.board import MessageBoard
from teamboard.llm import make_llm
from teamboard.sandbox import DockerSandbox
from teamboard.tools import Toolbox

log = logging.getLogger(__name__)


class Team:
    """Holds the team answer: the first agent that calls finish wins."""

    def __init__(self, label: str):
        self.label = label
        self.winner = None
        self.answer = None

    def submit(self, name: str, answer: str) -> None:
        if self.winner is None:
            self.winner, self.answer = name, answer
            exact_answer = answer.split("\nExact Answer: ")[-1].splitlines()[0]
            log.info("[%s] %s finished first: %s", self.label, name, exact_answer[:200])


async def run_query(cfg, query_id, question, retriever, run_dir: Path, make_llm=make_llm, make_sandbox=DockerSandbox) -> dict:
    trace_dir = run_dir / "traces" / query_id
    workspace_dir = run_dir / "workspaces" / query_id
    for directory in (trace_dir, workspace_dir):  # a resumed query starts from scratch
        shutil.rmtree(directory, ignore_errors=True)
    trace_dir.mkdir(parents=True)

    names = cfg["team"]["agents"]
    board = MessageBoard(trace_dir / "board.jsonl", label=query_id)
    team = Team(label=query_id)
    sandboxes = {
        name: make_sandbox(container_name(cfg["experiment"], query_id, name), workspace_dir / name, cfg["sandbox"], cfg["experiment"])
        for name in names
    }
    system_template = Path(cfg["team"]["system_prompt"]).read_text()
    task = Path(cfg["team"]["task_prompt"]).read_text().format(question=question)

    agents = []
    for name in names:
        toolbox = Toolbox(name, board, retriever, sandboxes[name], team, cfg["board"])
        teammates = ", ".join(other for other in names if other != name)
        system_prompt = system_template.format(name=name, teammates=teammates, num_agents=len(names))
        llm = make_llm(cfg["llm"], system_prompt, toolbox.specs)
        agents.append(Agent(name, llm, toolbox, cfg["team"]["max_steps"], trace_dir / f"{name}.jsonl"))

    started = time.monotonic()
    try:
        await asyncio.gather(*(sandbox.start() for sandbox in sandboxes.values()))
        statuses = await run_until_first_finish(agents, task, team, cfg["team"]["time_limit_minutes"] * 60)
    finally:
        await asyncio.gather(*(sandbox.stop() for sandbox in sandboxes.values()))

    result = build_result(cfg, query_id, agents, statuses, team, board, time.monotonic() - started)
    write_json_atomic(run_dir / "results" / f"{query_id}.json", result)
    return result


async def run_until_first_finish(agents, task: str, team: Team, time_limit: float) -> list[str]:
    """Runs all agents concurrently and cancels everyone as soon as one has finished or time is up."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + time_limit
    tasks = [asyncio.create_task(agent.run(task)) for agent in agents]
    pending = set(tasks)
    while pending and team.winner is None:
        done, pending = await asyncio.wait(pending, timeout=deadline - loop.time(), return_when=asyncio.FIRST_COMPLETED)
        if not done:  # time limit reached
            break
    for unfinished in pending:
        unfinished.cancel()
    outcomes = await asyncio.gather(*tasks, return_exceptions=True)
    return [describe_outcome(outcome) for outcome in outcomes]


def describe_outcome(outcome) -> str:
    if isinstance(outcome, asyncio.CancelledError):
        return "cancelled"
    if isinstance(outcome, Exception):
        return f"error: {type(outcome).__name__}: {outcome}"
    return outcome


def build_result(cfg, query_id, agents, statuses, team: Team, board: MessageBoard, elapsed: float) -> dict:
    """A run file in the BrowseComp-Plus format, plus per-agent details under `metadata`."""
    if team.winner:
        status = "completed"
    elif any(s.startswith("error") for s in statuses):
        status = "error"  # an infrastructure failure: run.py retries these on resume
    else:
        status = "incomplete"

    per_agent = {
        agent.name: {
            "status": "winner" if agent.name == team.winner else agent_status,
            "steps": agent.steps,
            "tool_call_counts": dict(agent.toolbox.call_counts),
            "retrieved_docids": sorted(agent.toolbox.retrieved_docids),
            "usage": dict(agent.usage),
        }
        for agent, agent_status in zip(agents, statuses)
    }
    return {
        "query_id": query_id,
        "tool_call_counts": dict(sum((agent.toolbox.call_counts for agent in agents), Counter())),
        "status": status,
        "retrieved_docids": sorted(set().union(*(agent.toolbox.retrieved_docids for agent in agents))),
        "usage": dict(sum((agent.usage for agent in agents), Counter())),
        "metadata": {
            "model": cfg["llm"]["model"],
            "provider": cfg["llm"]["provider"],
            "experiment": cfg["experiment"],
            "agents": [agent.name for agent in agents],
            "winner": team.winner,
            "elapsed_seconds": round(elapsed, 1),
            "num_board_messages": len(board.messages),
            "per_agent": per_agent,
        },
        # The judge reads the final answer from the last item of `result`.
        "result": [{"type": "output_text", "tool_name": None, "arguments": None, "output": team.answer or ""}],
    }


def container_name(experiment: str, query_id: str, agent: str) -> str:
    name = f"tb-{experiment}-{query_id}-{agent}-{uuid.uuid4().hex[:6]}"
    return re.sub(r"[^a-zA-Z0-9_.-]", "-", name).lower()


def write_json_atomic(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    os.replace(tmp, path)

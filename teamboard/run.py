"""Run the agent team on BrowseComp-Plus queries.

    python -m teamboard.run --config configs/claude.yaml
"""

import argparse
import asyncio
import json
import logging
import subprocess
from pathlib import Path

import yaml

from teamboard.config import apply_env, load_config
from teamboard.retriever import Retriever
from teamboard.team import run_query

log = logging.getLogger("teamboard")


def load_queries(cfg: dict) -> list[tuple[str, str]]:
    """(query_id, question) pairs from the BrowseComp-Plus queries.tsv, filtered by the config."""
    browsecomp = cfg["browsecomp"]
    with open(browsecomp["queries_tsv"]) as f:
        queries = [tuple(line.rstrip("\n").split("\t", 1)) for line in f if line.strip()]
    if browsecomp["query_ids"]:
        wanted = {str(query_id) for query_id in browsecomp["query_ids"]}
        queries = [query for query in queries if query[0] in wanted]
    if browsecomp["max_queries"]:
        queries = queries[: browsecomp["max_queries"]]
    return queries


def needs_run(result_path: Path) -> bool:
    """Resume: skip finished queries, but retry the ones that failed because of an infrastructure error."""
    return not result_path.exists() or json.loads(result_path.read_text())["status"] == "error"


def hide_api_keys(cfg):
    """The config as saved next to the results: every `api_key` written in the YAML is replaced."""
    if isinstance(cfg, dict):
        return {key: "<hidden>" if key == "api_key" else hide_api_keys(value) for key, value in cfg.items()}
    return cfg


def remove_leftover_containers(experiment: str) -> None:
    """Containers of a previous run of this experiment that was killed before it could clean up."""
    listing = subprocess.run(
        ["docker", "ps", "-aq", "--filter", f"label=teamboard.exp={experiment}"],
        capture_output=True, text=True, check=True,
    )
    if listing.stdout.split():
        subprocess.run(["docker", "rm", "-f", *listing.stdout.split()], capture_output=True)


async def run_all(cfg: dict, run_dir: Path) -> None:
    queries = [q for q in load_queries(cfg) if needs_run(run_dir / "results" / f"{q[0]}.json")]
    log.info("%d queries to run -> %s", len(queries), run_dir)
    limit = asyncio.Semaphore(cfg["browsecomp"]["max_concurrent_queries"])

    retriever = Retriever(cfg["retriever"]["url"])
    await retriever.load_tool_specs()
    log.info("retriever tools: %s", [spec.name for spec in retriever.tool_specs])

    async def run_one(query_id: str, question: str) -> None:
        async with limit:
            result = await run_query(cfg, query_id, question, retriever, run_dir)
        meta = result["metadata"]
        log.info("query %s: %s, winner=%s, %.0fs, %d board posts",
                 query_id, result["status"], meta["winner"], meta["elapsed_seconds"], meta["num_board_messages"])

    await asyncio.gather(*(run_one(query_id, question) for query_id, question in queries))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(message)s", datefmt="%H:%M:%S")
    log.setLevel(logging.INFO)

    cfg = load_config(args.config)
    apply_env(cfg)
    run_dir = Path(cfg["output_dir"]) / cfg["experiment"]
    (run_dir / "results").mkdir(parents=True, exist_ok=True)
    (run_dir / "config.yaml").write_text(yaml.safe_dump(hide_api_keys(cfg), sort_keys=False, allow_unicode=True))

    remove_leftover_containers(cfg["experiment"])
    asyncio.run(run_all(cfg, run_dir))


if __name__ == "__main__":
    main()

"""Side-by-side report for experiments that ran on the same queries (used by scripts/compare20.sh).

    python -m teamboard.compare --configs configs/compare20_team.yaml configs/compare20_solo.yaml

For each config it reads the run results (runs/<experiment>/results/) and the API judge's verdicts
(<api_evaluation.eval_dir>/<experiment>/results/), and writes comparisons/<exp1>_vs_<exp2>.md.
A query that was not run or not judged counts as wrong.
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from teamboard.config import load_config


def read_json(path: Path):
    return json.loads(path.read_text()) if path.exists() else None


def load_setting(config_path: str) -> dict:
    cfg = load_config(config_path)
    experiment = cfg["experiment"]
    results_dir = Path(cfg["output_dir"], experiment, "results")
    verdicts_dir = Path(cfg["api_evaluation"]["eval_dir"], experiment, "results")
    queries = {}
    for query_id in map(str, cfg["browsecomp"]["query_ids"]):
        verdict = read_json(verdicts_dir / f"{query_id}_eval.json")
        queries[query_id] = {
            "result": read_json(results_dir / f"{query_id}.json"),
            # None = not judged. Unfinished runs get a verdict without "correct" from the judge script: wrong.
            "correct": verdict["judge_result"].get("correct") is True if verdict else None,
        }
    return {
        "name": experiment,
        "agents": len(cfg["team"]["agents"]),
        "judge": cfg["api_evaluation"]["args"]["model"],
        "queries": queries,
    }


def average(values: list) -> float:
    return sum(values) / len(values) if values else 0.0


def summary_row(setting: dict) -> str:
    queries = setting["queries"].values()
    results = [q["result"] for q in queries if q["result"]]
    total = len(setting["queries"])
    correct = sum(q["correct"] is True for q in queries)
    completed = sum(r["status"] == "completed" for r in results)
    seconds = average([r["metadata"]["elapsed_seconds"] for r in results])
    searches = average([r["tool_call_counts"].get("search", 0) for r in results])
    tokens = average([r["usage"].get("input_tokens", 0) + r["usage"].get("output_tokens", 0) for r in results])
    posts = average([r["metadata"]["num_board_messages"] for r in results])
    return (f"| {setting['name']} | {setting['agents']} | {correct}/{total} ({100 * correct / total:.1f}%) "
            f"| {completed}/{total} | {seconds:.0f} | {searches:.1f} | {tokens / 1000:.0f}k | {posts:.1f} |")


def query_cell(query: dict) -> str:
    """✓ / ✗ from the judge (plus the run status if it did not finish), with the search calls in brackets."""
    result = query["result"]
    if result is None:
        return "not run"
    mark = {True: "✓", False: "✗", None: "not judged"}[query["correct"]]
    if result["status"] != "completed":
        mark += f" {result['status']}"
    return f"{mark} ({result['tool_call_counts'].get('search', 0)})"


def build_report(settings: list[dict]) -> str:
    query_ids = list(settings[0]["queries"])
    names = [s["name"] for s in settings]
    lines = [
        f"# {' vs '.join(names)}",
        "",
        f"{len(query_ids)} BrowseComp-Plus queries, judge: {settings[0]['judge']}. "
        "Not run / not judged counts as wrong. Search calls are summed over a team's agents.",
        "",
        "| setting | agents | correct | completed | avg time (s) | avg search calls | avg tokens (in+out) | avg board posts |",
        "|---|---|---|---|---|---|---|---|",
        *[summary_row(s) for s in settings],
        "",
    ]

    patterns = Counter(
        "".join("✓" if s["queries"][query_id]["correct"] else "✗" for s in settings) for query_id in query_ids
    )
    lines += [
        f"Correctness patterns (order: {', '.join(names)}): "
        + " · ".join(f"{pattern} {count}" for pattern, count in sorted(patterns.items())),
        "",
        "| query | " + " | ".join(names) + " |",
        "|---" * (len(names) + 1) + "|",
        *[f"| {query_id} | " + " | ".join(query_cell(s["queries"][query_id]) for s in settings) + " |"
          for query_id in query_ids],
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--configs", nargs="+", required=True)
    args = parser.parse_args()

    settings = [load_setting(path) for path in args.configs]
    report = build_report(settings)
    out_path = Path("comparisons", "_vs_".join(s["name"] for s in settings) + ".md")
    out_path.parent.mkdir(exist_ok=True)
    out_path.write_text(report)
    print(report)
    print(f"saved to {out_path}")


if __name__ == "__main__":
    main()

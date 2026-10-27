"""Start a helper process with its settings taken from the YAML config.

    python -m teamboard.launch retriever --config configs/default.yaml   # BrowseComp-Plus retrieval server
    python -m teamboard.launch vllm      --config configs/vllm_qwen3.yaml # local model server
    python -m teamboard.launch evaluate  --config configs/claude.yaml     # BrowseComp-Plus LLM-judge evaluation
    python -m teamboard.launch evaluate_api --config configs/deepseek.yaml # the same, judged by an API model

The retriever and the judge run from the BrowseComp-Plus environment (BrowseComp-Plus/.venv);
vLLM runs from `vllm_serve.executable`.
"""

import argparse
import os
from pathlib import Path

from teamboard.config import apply_env, load_config


def to_cli_flags(options: dict) -> list[str]:
    """{"index-path": "x", "normalize": True} -> ["--index-path", "x", "--normalize"]"""
    flags = []
    for key, value in options.items():
        if value is True:
            flags.append(f"--{key}")
        elif value is not False and value is not None:
            flags += [f"--{key}", str(value)]
    return flags


def retriever_command(cfg: dict, venv: Path) -> tuple[list[str], dict]:
    retriever = cfg["retriever"]
    argv = [str(venv / "bin/python"), "searcher/mcp_server.py",
            "--transport", "streamable-http", "--port", str(retriever["port"]),
            *to_cli_flags(retriever["searcher_args"])]
    if retriever["get_document"]:
        argv.append("--get-document")
    return argv, {"JAVA_HOME": retriever["java_home"]}


def vllm_command(cfg: dict, venv: Path) -> tuple[list[str], dict]:
    serve = cfg["vllm_serve"]
    env = {key: str(value) for key, value in serve.get("env", {}).items()}
    return [serve["executable"], "serve", serve["model"], *to_cli_flags(serve["args"])], env


def evaluate_command(cfg: dict, venv: Path) -> tuple[list[str], dict]:
    results_dir = Path(cfg["output_dir"], cfg["experiment"], "results").resolve()
    argv = [str(venv / "bin/python"), "scripts_evaluation/evaluate_run.py",
            "--input_dir", str(results_dir),
            "--eval_dir", str(Path(cfg["evaluation"]["eval_dir"]).resolve()),
            *to_cli_flags(cfg["evaluation"]["args"])]
    return argv, {key: str(value) for key, value in cfg["evaluation"].get("env", {}).items()}


def evaluate_api_command(cfg: dict, venv: Path) -> tuple[list[str], dict]:
    """The same evaluation, but judged by an API model (evaluate_with_openai.py, OpenAI Responses format)."""
    judge = cfg["api_evaluation"]
    results_dir = Path(cfg["output_dir"], cfg["experiment"], "results").resolve()
    argv = [str(venv / "bin/python"), "scripts_evaluation/evaluate_with_openai.py",
            "--input_dir", str(results_dir),
            "--eval_dir", str(Path(judge["eval_dir"]).resolve()),
            *to_cli_flags(judge["args"])]
    # The script builds openai.OpenAI(api_key=$OPENAI_API_KEY); the SDK takes the endpoint from $OPENAI_BASE_URL.
    return argv, {"OPENAI_API_KEY": judge["api_key"], "OPENAI_BASE_URL": judge["base_url"]}


COMMANDS = {
    "retriever": retriever_command,
    "vllm": vllm_command,
    "evaluate": evaluate_command,
    "evaluate_api": evaluate_api_command,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=COMMANDS)
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    cfg = load_config(args.config)
    apply_env(cfg)
    repo_dir = Path(cfg["browsecomp"]["repo_dir"]).resolve()
    argv, extra_env = COMMANDS[args.command](cfg, repo_dir / ".venv")

    # Run from the BrowseComp-Plus root so its relative paths (indexes/, data/, topics-qrels/) resolve.
    os.chdir(repo_dir)
    print("$", " ".join(argv), flush=True)
    os.execve(argv[0], argv, {**os.environ, **extra_env})


if __name__ == "__main__":
    main()

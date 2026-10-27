#!/usr/bin/env bash
# Judge the finished queries of a run with an API model instead of the local Qwen3-32B (no GPU needed).
# Uses BrowseComp-Plus's evaluate_with_openai.py with the `api_evaluation` section of the config
# (default: DeepSeek-Flash judge for runs/team4_bm25_deepseek-flash). Already-judged queries are skipped.
# Usage: bash scripts/evaluate_api.sh [config]   (default: configs/deepseek.yaml)
set -euo pipefail
cd "$(dirname "$0")/.."
exec /mnt/data2/users/puning.yang/miniconda3/envs/teamboard/bin/python -m teamboard.launch evaluate_api --config "${1:-configs/deepseek.yaml}"

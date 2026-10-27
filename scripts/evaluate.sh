#!/usr/bin/env bash
# Judge a finished run with BrowseComp-Plus's evaluate_run.py (Qwen3-32B on both GPUs: stop serve_vllm.sh first).
# Usage: bash scripts/evaluate.sh [config]   (default: configs/claude.yaml)
set -euo pipefail
cd "$(dirname "$0")/.."
exec /mnt/data2/users/puning.yang/miniconda3/envs/teamboard/bin/python -m teamboard.launch evaluate --config "${1:-configs/claude.yaml}"

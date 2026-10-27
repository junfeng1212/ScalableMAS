#!/usr/bin/env bash
# Terminal 2 (local models only): vLLM OpenAI-compatible server.
# Usage: bash scripts/serve_vllm.sh [config]   (default: configs/vllm_qwen3.yaml)
set -euo pipefail
cd "$(dirname "$0")/.."
exec /mnt/data2/users/puning.yang/miniconda3/envs/teamboard/bin/python -m teamboard.launch vllm --config "${1:-configs/vllm_qwen3.yaml}"

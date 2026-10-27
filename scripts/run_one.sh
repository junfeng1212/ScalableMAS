#!/usr/bin/env bash
# Run the agent team on ONE BrowseComp-Plus query with the local vLLM model (configs/vllm_qwen3_one.yaml).
# Needs the retrieval server (serve_retriever.sh) and the vLLM server (serve_vllm.sh) to be running.
# Usage: bash scripts/run_one.sh [config]   (default: configs/vllm_qwen3_one.yaml)
set -euo pipefail
cd "$(dirname "$0")/.."
exec /mnt/data2/users/puning.yang/miniconda3/envs/teamboard/bin/python -m teamboard.run --config "${1:-configs/deepseek.yaml}"

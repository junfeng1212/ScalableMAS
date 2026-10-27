#!/usr/bin/env bash
# Single-agent baseline: ONE DeepSeek agent, no message board, on query 773 (configs/deepseek_solo_one.yaml).
# Needs the retrieval server (serve_retriever.sh) to be running.
# Usage: bash scripts/run_solo_one.sh [config]   (default: configs/deepseek_solo_one.yaml;
#        the local-model version is configs/vllm_qwen3_solo_one.yaml)
set -euo pipefail
cd "$(dirname "$0")/.."
exec /mnt/data2/users/puning.yang/miniconda3/envs/teamboard/bin/python -m teamboard.run --config "${1:-configs/deepseek_solo_one.yaml}"

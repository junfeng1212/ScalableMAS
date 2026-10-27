#!/usr/bin/env bash
# Terminal 1: BrowseComp-Plus retrieval server (search tool over MCP).
# Usage: bash scripts/serve_retriever.sh [config]   (default: configs/default.yaml)
set -euo pipefail
cd "$(dirname "$0")/.."
exec /mnt/data2/users/puning.yang/miniconda3/envs/teamboard/bin/python -m teamboard.launch retriever --config "${1:-configs/default.yaml}"

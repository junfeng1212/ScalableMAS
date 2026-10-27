#!/usr/bin/env bash
# Run the agent team on BrowseComp-Plus (needs the retrieval server, and the vLLM server for local models).
# Usage: bash scripts/run.sh [config]   (default: configs/claude.yaml)
set -euo pipefail
cd "$(dirname "$0")/.."
exec /mnt/data2/users/puning.yang/miniconda3/envs/teamboard/bin/python -m teamboard.run --config "${1:-configs/claude.yaml}"

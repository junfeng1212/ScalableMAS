#!/usr/bin/env bash
# Unit tests (no LLM, Docker or retriever needed).
set -euo pipefail
cd "$(dirname "$0")/.."
exec /mnt/data2/users/puning.yang/miniconda3/envs/teamboard/bin/python -m pytest -q tests

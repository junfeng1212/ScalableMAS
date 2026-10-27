#!/usr/bin/env bash
# Comparison experiment: a team (3 DeepSeek-Flash agents + message board) vs a single DeepSeek-Flash agent
# on the same 20 BrowseComp-Plus queries (configs/compare20_team.yaml, configs/compare20_solo.yaml).
# Needs the retrieval server (serve_retriever.sh). Finished queries are skipped and failed ones retried,
# so simply run it again to resume. Report: comparisons/cmp20_team3_deepseek-flash_vs_cmp20_solo_deepseek-flash.md
set -euo pipefail
cd "$(dirname "$0")/.."
PY=/mnt/data2/users/puning.yang/miniconda3/envs/teamboard/bin/python
TEAM=configs/compare20_team.yaml
SOLO=configs/compare20_solo.yaml

# 1) Both settings solve the same 20 queries.
"$PY" -m teamboard.run --config "$TEAM"
"$PY" -m teamboard.run --config "$SOLO"

# 2) The same DeepSeek-Flash judge grades both runs.
"$PY" -m teamboard.launch evaluate_api --config "$TEAM"
"$PY" -m teamboard.launch evaluate_api --config "$SOLO"

# 3) Side-by-side report.
"$PY" -m teamboard.compare --configs "$TEAM" "$SOLO"

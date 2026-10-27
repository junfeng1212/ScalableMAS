#!/usr/bin/env bash
# One-time setup: environments, BrowseComp-Plus data + BM25 index, sandbox image.
# Usage: bash scripts/setup.sh   (the dataset download may need `huggingface-cli login` first)
set -euo pipefail
cd "$(dirname "$0")/.."

CONDA=/mnt/data2/users/puning.yang/miniconda3/bin/conda
ENV=/mnt/data2/users/puning.yang/miniconda3/envs/teamboard
export HF_HOME=/mnt/data2/users/puning.yang/huggingface_cache

# 1) Team runner env. openjdk 21 is only used by the BM25 retrieval server (retriever.java_home in the YAML).
"$CONDA" create -y -n teamboard -c conda-forge python=3.11 openjdk=21
"$ENV/bin/python" -m pip install -r requirements.txt
ls "$ENV/lib/jvm/lib/server/libjvm.so"   # must exist: configs/default.yaml points JAVA_HOME at $ENV/lib/jvm

# 2) BrowseComp-Plus env: retrieval server, vLLM and the Qwen3-32B judge.
(cd BrowseComp-Plus && uv sync)
# Only needed for the FAISS / Qwen3-Embedding retriever:
# (cd BrowseComp-Plus && uv pip install --no-build-isolation flash-attn)

# 3) Queries, answers and the BM25 index.
(cd BrowseComp-Plus && .venv/bin/python scripts_build_index/decrypt_dataset.py \
    --output data/browsecomp_plus_decrypted.jsonl --generate-tsv topics-qrels/queries.tsv)
(cd BrowseComp-Plus && .venv/bin/huggingface-cli download Tevatron/browsecomp-plus-indexes \
    --repo-type=dataset --include="bm25/*" --local-dir ./indexes)
# Qwen3-Embedding-8B index for the FAISS retriever:
# (cd BrowseComp-Plus && .venv/bin/huggingface-cli download Tevatron/browsecomp-plus-indexes \
#     --repo-type=dataset --include="qwen3-embedding-8b/*" --local-dir ./indexes)

# 4) Image of the agents' private containers.
docker pull python:3.11-slim

# 5) Local models only: vLLM >= 0.17 for Qwen3.8 (qwen3_5 architecture), used by configs/vllm_qwen3.yaml.
#    0.19 is the newest vLLM whose default wheels (torch 2.10, CUDA 12.8) still run on this machine's
#    NVIDIA driver 550; vLLM >= 0.20 ships CUDA 13 wheels, which need driver >= 580.
"$CONDA" create -y -n vllm python=3.12
/mnt/data2/users/puning.yang/miniconda3/envs/vllm/bin/python -m pip install "vllm==0.19.0"

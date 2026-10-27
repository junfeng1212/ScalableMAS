# TeamBoard

多个 Agent（默认 Bob、Eric、Ken、Bill）**同时、异步**地解同一道 BrowseComp-Plus 题。每个 Agent 有自己独立的 Docker 容器（`--network none`），
彼此之间**唯一**的交流方式是一个公共 message board。**第一个调用 `finish` 的 Agent 的答案就是团队答案**，其余 Agent 随即停止。

```
team runner (teamboard env, asyncio)
 ├─ MessageBoard          post_message / read_messages(wait_seconds)   ← 唯一的共享状态
 ├─ Bob / Eric / Ken / Bill   各自的 LLM 循环 + 各自的容器（bash）
 └─ Retriever             BrowseComp-Plus 的 MCP 检索服务（search，k=5，512 token snippet）
```

## 运行顺序
```bash
bash scripts/setup.sh                                   # 一次性：环境、数据集、BM25 索引、沙箱镜像
bash scripts/serve_retriever.sh                         # 终端 1：检索服务（:8080）
bash scripts/serve_vllm.sh configs/vllm_qwen3.yaml      # 终端 2：仅本地模型需要（:8000）
bash scripts/run_one.sh                                 # 先只跑一道题调试（configs/vllm_qwen3_one.yaml）
bash scripts/run_solo_one.sh                            # 单 Agent、无留言板跑同一道题，作对照（默认 configs/deepseek_solo_one.yaml，题目 773）
bash scripts/run.sh configs/vllm_qwen3.yaml #claude.yaml                 # 跑实验（openai.yaml / vllm_qwen3.yaml 同理）
bash scripts/evaluate.sh configs/claude.yaml            # Qwen3-32B 评测（占满两张卡，先停掉 vLLM）
bash scripts/evaluate_api.sh configs/deepseek.yaml      # 改用 API 模型当评委（默认 deepseek-flash，不占 GPU）
bash scripts/compare20.sh                               # 对比实验：3 人团队 vs 单 Agent（deepseek-flash，同 20 题），报告在 comparisons/
bash scripts/test.sh                                    # 单元测试
```
API key 在预设的 `llm` 块里配置：`api_key: sk-...`（直接写 key），或 `api_key_env: DEEPSEEK_API_KEY`（填环境变量名）。
都不写时用 SDK 默认的环境变量（`ANTHROPIC_API_KEY` / `OPENAI_API_KEY`）。运行时保存的 `runs/<experiment>/config.yaml` 里 key 会显示为 `<hidden>`。

## 配置
- `configs/default.yaml`：团队、message board、沙箱、检索、评测等所有公共设置。
- `configs/{claude,openai,vllm_qwen3}.yaml`：`base: default.yaml` 加上各自的 `llm` 块。`llm.request` 会原样传给对应 API。
- 先试跑：在预设里设置 `browsecomp.max_queries: 3`。

## 输出
```
runs/<experiment>/results/<qid>.json        BrowseComp-Plus run 格式（团队答案 + metadata.per_agent）
runs/<experiment>/traces/<qid>/board.txt    留言板记录（可直接阅读；board.jsonl 是同样内容的 JSON 版）
runs/<experiment>/traces/<qid>/<Agent>.jsonl 每个 Agent 每一步的推理、工具调用和输出
runs/<experiment>/workspaces/<qid>/<Agent>/ 每个 Agent 容器里的 /workspace
evals/<experiment>/results/                 评测结果（evaluation_summary.json）
```
重跑同一个 config 时，会跳过已有结果的题目（`status: error` 的题会重跑）。

清理异常退出后残留的容器：`docker rm -f $(docker ps -aq --filter label=teamboard.exp=<experiment>)`
（`run.sh` 启动时也会自动清理本实验的残留容器）。

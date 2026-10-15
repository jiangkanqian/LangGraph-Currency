# LangGraph Currency · Kagent BYO + Zadig

基于 Kagent **v0.9.10** 官方 Currency 示例整理的独立 Python 项目，用于验证：

```text
Git Commit → 检查/测试 → Docker → Harbor → Agent CR → Kagent → A2A 验证
```

源码基线与许可见 [UPSTREAM.md](UPSTREAM.md) 和 [LICENSE](LICENSE)。
`vendor/` 保留该版本的 `kagent-core` 和 `kagent-langgraph`，避免误装同名包的其他版本；
全部 Python 依赖由 `uv.lock` 固定。无需克隆整个 Kagent 仓库。

## 目录

```text
currency/           LangGraph Agent、汇率工具、A2A 入口
vendor/             固定版本的 Kagent 适配层
tests/              离线工具、应用发现与冒烟结果校验测试
deploy/{dev,staging,prod}/agent.yaml
scripts/            CI、构建推送、发布回滚、A2A 冒烟
docs/zadig.md       Zadig 任务配置及多环境发布步骤
.github/workflows/ci.yml  Linux 测试、镜像构建和容器发现验证
```

## 本地安装和测试

需要 Python 3.12 和 uv 0.13.1；uv 可以自动下载 Python。

```bash
pip install uv==0.13.1
uv sync --locked
uv run ruff check currency scripts tests
uv run pytest
```

单元测试不访问模型、Kagent 或外部汇率 API。Linux/Zadig 可直接运行 `bash scripts/ci.sh`。

## 配置与运行

复制 `.env.example` 到本地 `.env`，填入实际配置，然后：

```bash
uv run --env-file .env currency
```

| 变量 | 用途 |
| --- | --- |
| `OPENAI_MODEL` | vLLM 实际公开的模型 ID，须与 `/v1/models` 一致 |
| `OPENAI_BASE_URL` | OpenAI 兼容服务地址，通常以 `/v1` 结尾 |
| `OPENAI_API_KEY` | 模型密钥；无认证服务也需提供非空占位值 |
| `KAGENT_URL` | 本地运行时指向可达的 Kagent Controller 地址 |
| `KAGENT_NAME` / `KAGENT_NAMESPACE` | Agent 身份；Kubernetes 中由 Kagent 配置 |
| `AGENT_URL` | 对外 Agent Card URL；默认 `http://localhost:8080/`，跨服务发现时配置实际地址 |
| `EXCHANGE_RATE_BASE_URL` | 可选，默认 `https://api.frankfurter.app` |

该版本保留 Kagent 的任务存储和 checkpointer，因此完整 A2A 对话需要可达的 Kagent Controller。
只有 `/health` 与 Agent Card 发现可以脱离 Controller/模型验证。
vLLM 必须支持当前模型的 tool calling；OpenAI 接口可达不等于工具调用可用，需在集群联调确认。
默认不启用 LangSmith/OTel 导出，需要时单独配置。

## 镜像

```bash
docker build -t langgraph-currency:local .
docker run --rm --env-file .env -p 8080:8080 langgraph-currency:local
```

容器内的 `localhost` 指向容器自身，不能直接沿用宿主机端口转发地址；Docker Desktop 可按需使用
`host.docker.internal`。镜像使用非 root 用户，健康检查不依赖 curl。

```bash
uv run python scripts/smoke.py --url http://localhost:8080 --discovery-only
uv run python scripts/smoke.py --url http://localhost:8080
```

第二条调用模型和汇率工具，检查 A2A 返回成功且包含文本；它不是语义评估，
不能据此宣称工具必定调用或答案正确。正式发布需结合 trace 和业务评估设置门禁。

## 部署与下一阶段

参见 [Zadig 配置指南](docs/zadig.md)。三个模板默认使用已有 `kagent` namespace 下的独立 Agent 名称与 Secret，
便于第一阶段验证；这不是完整的安全/网络环境隔离。生产应采用独立集群或经验证的 namespace 隔离。

模板中的模型地址、镜像仓库均为占位符。真实凭据放 Kubernetes Secret / Zadig 凭据，不提交 Git。
当前交付包含多环境发布脚本和镜像回滚；蓝绿/灰度的网关流量切换留待现网网关方案明确后接入。
Zadig 只修改 Agent CR，由 Kagent 管理 Deployment，不直接修改其 Pod/Deployment。

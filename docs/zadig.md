# Zadig 接入指南

本仓库提供可在 Zadig 自定义任务中运行的命令，不是假定可直接导入的 Zadig 工作流 YAML。
具体 UI 字段随现网 Zadig 版本确认。先打通 dev，再晋级 staging 和 prod。

## 前置配置

1. 接入本 GitHub 仓库，配置 Push/MR 触发；构建必须使用触发事件的精确 commit。
2. 配置 Harbor 凭据；构建执行器需要 Docker（或将构建命令换为受支持的 BuildKit）。
3. 测试执行器提供 uv 0.13.1/Python 3.12，发布执行器另需 kubectl 和目标集群凭据。
4. 发布账号仅授予目标 namespace 中必要的 Agent 读取/创建/patch 权限和 Deployment 读取权限。
5. 在目标 namespace 预先配置模型 Secret，名称分别为 `currency-dev-model`、
   `currency-staging-model`、`currency-prod-model`，键为 `OPENAI_API_KEY`。
   使用你们已有 Secret 管理机制；不要把密钥写入 Git、构建命令或日志。
6. 私有镜像拉取凭据通过现网 Kagent 支持的配置配置；用实际 CRD 核实字段。

## CI 工作流

| 顺序 | 任务 | 命令/配置 |
| --- | --- | --- |
| 1 | Checkout | 获取触发 commit |
| 2 | Lint + Unit | `bash scripts/ci.sh`，收集 `reports/junit.xml` |
| 3 | Image | 设置 `IMAGE_REPO=registry.example.com/agents/langgraph-currency`，登录仓库后运行 `bash scripts/build.sh` |
| 4 | Scan | `trivy image --exit-code 1 --severity HIGH,CRITICAL "$IMAGE"` |
| 5 | Artifact | 保存完整 image 引用、commit SHA、扫描报告 |

`build.sh` 以 `git rev-parse HEAD` 作为完整 tag，输出 `reports/image.txt`。
任务之间通过 Zadig 输出变量/制品传递镜像引用，不要假定环境变量自动继承。
Harbor 设置 tag 不可变；更严格的晋级可使用 push 后得到的 `repo@sha256:...`。
扫描失败停止后续部署。

## dev 发布与验证

将 `IMAGE` 设置为 CI 的产物，模型变量使用目标环境配置：

```bash
export GIT_COMMIT="$(git rev-parse HEAD)"
export OPENAI_MODEL='your-served-model-id'
export OPENAI_BASE_URL='http://your-model-service:8000/v1'
uv sync --locked
uv run python scripts/release.py deploy --env dev --image "$IMAGE"
uv run python scripts/smoke.py --url "$AGENT_SERVICE_URL"
```

`AGENT_SERVICE_URL` 为 Agent 的实际 Service URL，发布执行器需能访问它；通过
`kubectl get svc -n kagent` 和资源 owner/labels 确认，不要把 Kagent UI URL 当作 Agent A2A URL。
需要对外发现时在环境模板添加 `AGENT_URL`，设置为实际调用入口。

发布脚本先执行 server-side dry-run，备份旧 Agent JSON 到 `.release/`，再 apply CR；
通过 owner UID 找到 Deployment，检查新镜像、observedGeneration 和副本状态，避免旧 Ready 被误判。
它不修改 Deployment。发布超时或冒烟失败会返回非零；应在 Zadig 中中止晋级。
同环境禁止并发发布，避免镜像/备份互相覆盖。
`.release/` 是本地忽略文件，按内部敏感制品策略保存，不能上传到公开 GitHub。

## staging / prod 晋级与回滚

同一镜像只构建一次，修改 `--env staging` / `--env prod` 并使用相应模型配置。
prod 前设置人工审批、业务评估门禁。不要每个环境重新构建。

记录旧镜像引用后，可执行镜像回滚：

```bash
uv run python scripts/release.py rollback --env dev --image "$PREVIOUS_IMAGE"
uv run python scripts/smoke.py --url "$AGENT_SERVICE_URL"
```

回滚保留当前模型/工具配置，只回退镜像；若需要配置一起回退，从对应 Git commit 的模板发布并使用
相应环境配置。首次创建没有旧镜像，不自动删除 Agent。失败后不要把失败发布标记为成功。

## 后续蓝绿/灰度

本次不自动配置网关。后续创建独立 blue/green Agent CR，候选验证通过后由现网网关切流。
需先确定 Service 发现、会话粘性、长任务排空、流量权重、指标门禁与回滚操作。
模型/工具调用质量需独立评估；HTTP 200 和 Pod Ready 不足以作为业务发布成功标准。

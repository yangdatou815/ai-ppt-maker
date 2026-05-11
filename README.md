# ai-ppt-maker

> 把粘贴的文字 / 上传的 Markdown / Word / 图片 / 表格，一键变成**风格高大上、可下载二次编辑的 .pptx 宣讲稿**。本地部署、走本地 Ollama，不外发资料。

> 当前里程碑：**M3-1 模板系统进行中**（v0.5.0 已发布）—— 文本→pptx 全链路、图片/表格自适应排版、Roadmap 视图、运行时调试开关、Windows 一键安装均已上线；M3-1 三套 master.pptx 母版已接入渲染器，模板预览缩略图待做。完整进度见 [Roadmap](backend/roadmap.yaml) 或前端 Roadmap 标页。

## 三种安装方式

### A. Windows 一键安装（零基础推荐）

下载 `scripts\install.bat`（仓库 `scripts/` 目录下），双击运行：

```
scripts\install.bat
```

它会用 winget 自动装 Python 3.11 / Node.js LTS / Git / Ollama，git clone 项目，调用 `scripts/deploy.bat` 完成 venv + 前端构建 + 拉模型，最后自动启动。安装日志写到脚本同目录下的 `install.log`。

> 提示：脚本兼容两种用法 —— ① 在 git clone 后双击 `scripts\install.bat` 直接复用本地源码；② 单独把这个文件下到任意空目录双击，它会自动 `git clone` 到 `%USERPROFILE%\ai-ppt-maker`。

环境变量可定制：

| 变量 | 默认 | 用途 |
|---|---|---|
| `APM_INSTALL_DIR` | `%USERPROFILE%\ai-ppt-maker` | 安装目录 |
| `APM_REPO_URL` | _未设_ | git 远端 URL（自托管时必填） |
| `APM_LLM_MODEL` | `qwen2.5:7b-instruct` | 拉取的模型 |
| `APM_AUTO_PULL` | `1` | 是否自动 pull 模型 |
| `APM_AUTO_START` | `1` | 安装后是否自动 start |

日常启动 / 停止：双击 `scripts\start.bat` / `scripts\stop.bat`。卸载：`scripts\cleanup.bat`（支持 `/dry-run` `/with-model` `/with-ollama` `/purge`）。

### B. Linux / macOS 脚本安装

```bash
git clone <repo> ai-ppt-maker && cd ai-ppt-maker
./scripts/deploy.sh        # venv + npm build + ollama pull
./scripts/start.sh         # 启动后自动开浏览器
./scripts/stop.sh          # 关停
./scripts/cleanup.sh       # 卸载（支持 --dry-run --purge 等）
```

### C. Docker Compose

```bash
cp .env.example .env
docker compose up --build
# 浏览器: http://localhost:5173
```

### D. 开发模式（前后端分别热重载）

```bash
./scripts/dev.sh   # 同时拉起后端 uvicorn --reload + 前端 vite dev
```

## 文档

- [PRD.md](PRD.md) —— 产品需求文档
- [docs/architecture.md](docs/architecture.md) —— 技术详细设计
- [docs/design-refs/](docs/design-refs) —— 三套模板视觉基准
- [CHANGELOG.md](CHANGELOG.md) —— 版本变更记录（[Keep a Changelog](https://keepachangelog.com/en/1.1.0/)）
- [.github/copilot-instructions.md](.github/copilot-instructions.md) —— 编码规范

## 里程碑

详见 [PRD §10](PRD.md#10-milestones)。当前位于 **M1（骨架可跑）**。

## 开发规范（DoD）

提交前必须本地通过 `bash scripts/dod.sh` —— 与 CI 同源命令。CI 还会跑 `python scripts/build_scripts.py --check` 校验 `scripts/install.bat` / `scripts/deploy.bat` / `scripts/cleanup.bat` 与模板源同步。

## 持续集成

`.workflow/master-pipeline.yml` 是 Gitee Go 2.x 流水线（`build_stage` ruff + drift；`test_stage` pytest + coverage 70% gate），main 分支 push 自动触发。前端构建（vitest + vite build）暂未纳入，因为 Node 插件的 2.x schema 还没拿到样本 —— 仍要靠本地 `bash scripts/dod.sh` 守住。

## 排错：打开 DEBUG 日志

默认 `LOG_LEVEL=INFO`。需要定位问题时不必整体调高，可只对单一子系统开 DEBUG：

```bash
# 只把 outline 链路（LLM client / repair / fallback / orchestrator）调到 DEBUG
LOG_LEVEL=INFO \
LOG_LEVEL_OVERRIDES="app.outline=DEBUG,app.api.outline=DEBUG" \
python -m uvicorn app.main:app --host 127.0.0.1 --port 8088
```

可选级别：`DEBUG` / `INFO` / `WARNING` / `ERROR` / `CRITICAL`。多对 override 用逗号分隔；写错的级别会安全降级为 `INFO`，不会让服务起不来。常用排错入口：

| 问题 | 推荐 override |
|---|---|
| LLM 输出 JSON 解析失败 | `app.outline.repair=DEBUG,app.api.outline=DEBUG`（会打印 LLM 原始输出前 500 字符） |
| Ollama 连接 / 慢 | `app.outline.llm_client=DEBUG,httpx=DEBUG` |
| Fallback 触发分析 | `app.outline.fallback=DEBUG` |
| HTTP 请求面 | `uvicorn.access=DEBUG` |

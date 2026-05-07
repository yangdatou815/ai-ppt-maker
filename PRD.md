# Product Requirements Document (PRD)

## ai-ppt-maker MVP

## 1. Executive Summary

ai-ppt-maker 是一个本地部署的 Web 应用，目标是把用户提供的**原始素材**（大段文字、图片、表格、Markdown / Word 文档）一键转换成一份**风格高大上、可直接下载二次编辑的 .pptx 宣讲稿**。

它不是 Canva / Gamma 这类云端在线编辑工具的复刻，也不是单纯的 Markdown-to-Slides 渲染器。核心价值是：

- **理解内容** —— 用本地 LLM（Ollama）把长文本切分成"封面 / 章节页 / 正文页 / 数据页 / 结尾"等结构化大纲。
- **专业排版** —— 套用 3 套精选商业模板（深色商务、极简白、科技蓝），自动处理标题层级、要点提炼、图表占位。
- **本地可控** —— FastAPI + 前端 + Ollama 全部跑在本机/局域网，docker-compose 一键起，不外发任何企业资料。
- **结果可编辑** —— 输出 python-pptx 生成的标准 .pptx，PowerPoint / WPS / Keynote 都能继续改。

MVP 目标：一个会议室里的高管或者创业者，把一份 3000 字的产品发布稿粘进来，10 秒内拿到一份 15 页左右、可以直接上台讲的 .pptx。

## 2. Mission

### Mission Statement

让"内容专家"不必成为"排版专家"，也能产出投资人 / 高管 / 客户愿意认真看完的宣讲 PPT。

### Core Principles

- Content first, decoration second —— 模板服务于信息，而不是相反。
- Local & private by default —— 默认走本地 Ollama，敏感稿不出企业网。
- Editable artifact —— 输出永远是标准 .pptx，不绑定任何渲染器。
- Premium-feeling defaults —— 任何一套默认模板都"敢拿去客户面前"。
- One-shot, then refine —— 用户先一键拿到完整稿，再回到 PPT 软件里精修。

## 3. Target Users

### Primary Personas

1. 企业宣讲者（产品发布 / 内部汇报）
   - 已经写好了发布稿 / 汇报材料的文字版，缺一份能上台的视觉化 PPT。
   - 在意品牌感、配色统一、专业度。

2. 创业者 / 投资路演（BP 制作者）
   - 手上有一份商业计划书的文字稿或 Word 文档。
   - 需要快速产出 10–20 页风格统一的路演 deck，再去精修。

### Technical Comfort Level

- 熟练使用 PowerPoint / WPS / Keynote。
- 能在浏览器里粘贴文本、上传文件、点下载即可，不需要写 Markdown / 不需要懂 LLM。
- 部署侧由一名工程师用 docker-compose 起服务即可。

### User Needs and Pain Points

- "写得出内容，排不出版" —— 不会调对齐、配色、字号层级。
- "网上的 AI PPT 工具要把稿子发到云上" —— 企业稿、BP 稿不敢传。
- "Markdown-to-slides 出来太程序员" —— 缺商业感、没有封面 / 章节过渡。
- "改一版要重新生成所有页" —— 希望输出可以在 PowerPoint 里继续改。

## 4. Scope

### 4.1 In Scope (MVP)

- 单页 Web 界面：左侧输入区（文本 / 文件 / 图片 / 表格），右侧模板选择 + 生成按钮 + 预览缩略图。
- 输入形式
  - 直接粘贴纯文本（必选，最小可用路径）。
  - 上传图片（jpg/png），由用户标注"插到哪个章节附近"或交给 AI 自动放置。
  - 上传表格（CSV / Markdown table / Excel 单 sheet），生成"数据页"。
  - 上传 Markdown 或 Word（.md / .docx）整篇解析。
- 内容理解（本地 Ollama）
  - 自动生成大纲（封面标题 / 副标题 / 章节列表 / 每页要点）。
  - 把长段落压缩成 3–5 条要点（bullet）。
  - 生成每页讲者备注（speaker notes）。
- 模板系统
  - 3 套内置模板：`executive-dark`（深色商务）、`minimal-light`（极简白）、`tech-blue`（科技蓝）。
  - 一种"AI 自动选模板"模式：根据输入内容主题自动挑一套。
- 输出
  - 标准 .pptx 文件，使用 python-pptx 生成，保留母版 / 占位符，便于二次编辑。
  - 包含封面页、目录页、章节分隔页、正文页（含 bullets / 图片 / 表格）、结尾"谢谢"页。
- 部署
  - docker-compose：`backend`（FastAPI）+ `frontend`（静态构建产物）+ 复用宿主机已装的 Ollama。
  - 全本地可跑，不强依赖外网。

### 4.2 Out of Scope (MVP)

- 多用户登录 / 团队协作 / 计费。
- 在线"所见即所得"幻灯片编辑（输出后请用 PowerPoint 改）。
- 动画、转场、视频嵌入。
- HTML 在线播放（reveal.js / Slidev）—— 仅在 v2 考虑。
- PDF 导出 —— 仅在 v2 考虑（用户可在 PowerPoint 里另存）。
- 用户自带 PPT 母版作为模板 —— v2。
- 多语言 UI（MVP 中文为主，模板内容跟随输入语言；输入语言自动检测，中英文都支持生成）。

## 5. Functional Requirements

### 5.1 Input Module

- FR-1.1 文本输入框支持 ≥ 20000 字粘贴。
- FR-1.2 支持上传 .md / .docx 文件（≤ 10 MB），后端解析为统一中间结构（章节树）。
- FR-1.3 支持上传图片（≤ 10 张，单张 ≤ 5 MB，jpg/png/webp）。
- FR-1.4 支持上传 .csv / .xlsx（单 sheet，≤ 1000 行）作为数据页素材。
- FR-1.5 输入区提供"清空 / 示例填充"快捷按钮，示例数据用于首次体验。

### 5.2 Outline Generation

- FR-2.1 调用本地 Ollama 模型，把输入素材转成结构化 JSON 大纲：
  ```
  { title, subtitle, sections: [ { heading, bullets[], suggested_visual } ] }
  ```
- FR-2.2 大纲生成必须可重试，且对 LLM 异常做兜底（返回基于纯规则的简易大纲）。
- FR-2.3 用户可在生成前编辑大纲（v1.1，MVP 可只读展示 + 重新生成）。

### 5.3 Template & Layout

- FR-3.1 提供 3 套模板，每套至少包含：cover / toc / section-divider / content-bullets / content-image / content-table / closing 7 种版式。
- FR-3.2 模板以 .pptx 母版文件 + 一份 layout-mapping.yaml 描述（版式名 → slide_layout index、占位符索引）。
- FR-3.3 "AI 自动选模板"基于关键词 / 主题分类（如"金融、科技、教育"）映射到模板。
- FR-3.4 模板新增不需要改后端代码，只需放入 `backend/templates/<name>/` 并提供 mapping。

### 5.4 PPT Generation

- FR-4.1 后端用 python-pptx 加载模板母版，按大纲逐页插入。
- FR-4.2 每页包含 speaker notes。
- FR-4.3 图片自适应：按版式占位符尺寸等比缩放、居中。
- FR-4.4 表格：超出页面时自动分页或缩小字号（按规则，先缩字号后分页）。
- FR-4.5 文件命名：`<safe-title>-<yyyymmdd-hhmm>.pptx`。

### 5.5 Web UX

- FR-5.1 单页流程：输入 → 选模板 → 生成 → 下载。生成中展示进度（大纲 / 排版 / 打包三阶段）。
- FR-5.2 下载前提供 5 张缩略图预览（后端用 LibreOffice 或 unoconv 渲染前 5 页 PNG）。
- FR-5.3 错误提示明确区分"输入不合法 / LLM 不可用 / 模板缺失 / 内部错误"。

### 5.6 API

- FR-6.1 `POST /api/outline` —— 输入素材 → 大纲 JSON。
- FR-6.2 `POST /api/generate` —— 大纲 + 模板名 → 任务 id。
- FR-6.3 `GET /api/jobs/{id}` —— 任务状态与下载链接。
- FR-6.4 `GET /api/templates` —— 模板列表与示例缩略图。

## 6. User Stories

UC-1 粘贴文本生成发布稿
> 作为产品经理，我把一份 3000 字的产品发布通稿粘进来，选择`executive-dark`，10 秒内拿到 15 页左右的 .pptx，能直接在公司大屏上演示。

UC-2 上传 Word 生成路演 BP
> 作为创业者，我上传一份 8000 字的 .docx 商业计划书，选"AI 自动选模板"，拿到 18 页左右的路演 deck，封面 / 目录 / 团队 / 市场 / 产品 / 数据 / 融资 章节齐全。

UC-3 文本 + 图片混合输入
> 作为市场经理，我粘贴稿子并上传 5 张产品照片，AI 自动把图片插入相关章节的"图文页"中，不会出现拉伸 / 错位。

UC-4 表格转数据页
> 作为分析师，我上传一个销售额季度表，生成一页带表格的"数据页"，字号合适、表头加粗、模板配色统一。

UC-5 重新生成
> 作为用户，对当前生成结果不满意，我点"重新生成"或换一套模板，无需重新输入素材。

UC-6 离线 / 内网使用
> 作为企业用户，整套服务跑在内网机器上，不向外发送任何数据，Ollama 模型已预先 pull 到本地。

## 7. Non-Functional Requirements

- NFR-1 性能：3000 字输入，端到端生成 ≤ 30 秒（本地 Ollama，7B 模型，消费级 GPU 或 CPU 大内存机）。
- NFR-2 可用性：首次进入页面 → 看到示例 → 一键生成示例 PPT，全程 ≤ 3 次点击。
- NFR-3 可移植：docker-compose up 即可起，宿主机只需要 Docker + 已运行的 Ollama。
- NFR-4 安全：所有上传文件保存在本地临时目录，任务结束 24 小时内自动清理。
- NFR-5 可观测：后端结构化日志（job_id、耗时分阶段、LLM 调用次数 / token 数）。
- NFR-6 可扩展：新增模板 / 新增输入解析器（如 .pdf）只需新增模块，不改主流程。

## 8. Technical Architecture (Proposed)

```
+------------------+        +-----------------------+        +----------------+
|   Frontend (Vue) |  --->  |  Backend (FastAPI)    |  --->  |  Ollama (本地)  |
|  - 输入 / 模板选择 |        |  - /api/outline       |        |  qwen2.5 / llama|
|  - 进度 / 预览     |        |  - /api/generate      |        +----------------+
|  - 下载            |        |  - /api/jobs/{id}     |
+------------------+        |  - /api/templates     |
                            |                       |
                            |  modules:             |
                            |   parsers/  (md,docx, |
                            |              csv,xlsx)|
                            |   outline/  (LLM)     |
                            |   render/   (pptx)    |
                            |   preview/  (libreoff)|
                            |   templates/<name>/   |
                            +-----------------------+
```

参考开源项目（实现思路 / 模板灵感）：

- **python-pptx** —— pptx 生成核心库。
- **Slidev / reveal.js 主题** —— 提取配色与版式美学，反向迁移到 pptx 母版。
- **Marp / pandoc** —— Markdown / docx 解析参考。
- **PresentationGen / SlidesAI 类项目** —— 大纲 prompt 与版式映射的工程化思路。

（具体许可证与可借鉴范围在工程立项时逐项核对，PRD 阶段仅作参考，不直接复制代码。）

## 9. Tech Stack

- Backend: Python 3.11、FastAPI、python-pptx、python-docx、openpyxl、Pillow、httpx（调 Ollama）。
- Frontend: Vue 3 + Vite + TypeScript（与你 hotpulse / pm-copilot 风格保持一致）。
- LLM: 本地 Ollama，默认 `qwen2.5:7b-instruct`（中文宣讲场景表现好），可在 `.env` 切换。
- Preview: LibreOffice headless（容器内）渲染前 5 页 PNG。
- Packaging: docker-compose（backend + frontend nginx + 复用宿主机 Ollama via `host.docker.internal`）。

## 10. Milestones

- M1 — 骨架可跑（约一周内）
  - FastAPI + Vue 工程脚手架；`/api/templates` 返回 3 套模板；前端能展示。
- M2 — 文本 → pptx 端到端
  - 纯文本输入 → Ollama 大纲 → 1 套模板 → 下载 .pptx；含 speaker notes。
- M3 — 三套模板 + AI 自动选模板
  - 补齐另外 2 套；引入主题分类逻辑。
- M4 — 多模态输入
  - .md / .docx / 图片 / 表格 解析与排版。
- M5 — 体验打磨
  - 缩略图预览、进度条、错误分级、示例数据、docker-compose 一键起。

每个 milestone 完成时按 project-delivery-playbook 走 DoD：单测 / E2E / lint / 文档同步 / RELEASE_NOTES 更新。

## 11. Success Metrics

- 首次使用 → 拿到第一份 pptx 的时间 ≤ 5 分钟（含读 README）。
- 在 3 个真实场景（产品发布稿 / BP / 内部汇报）中，生成结果"无需排版返工即可直接讲" 的比例 ≥ 50%。
- 端到端生成耗时 P50 ≤ 20s、P95 ≤ 45s（3000 字 + 7B 本地模型）。
- docker-compose 在一台干净 Ubuntu 22.04 上 ≤ 10 分钟跑通示例。

## 12. Risks & Open Questions

- R-1 本地 7B 模型在结构化 JSON 输出上的稳定性 —— 需要严格 prompt + JSON 修复兜底。
- R-2 python-pptx 对复杂版式（图文混排、表格分页）的能力边界 —— 早期就要做技术预研。
- R-3 LibreOffice headless 渲染速度 / 字体缺失 —— 容器内需预装中文字体（思源黑体等）。
- R-4 "高大上" 是主观词 —— 需要在 M3 前定 3 套模板的视觉基准（截图归档进 docs/）。
- D-1（已定）输入语言自动检测，中英文都生成；UI 文案 MVP 仅中文。
- D-2（已定）页数不设硬上限，由 LLM 根据内容长度自行决定（前端可显示生成页数）。
- D-3（已定）MVP 模板视觉先借鉴开源主题（Slidev / reveal.js / Beautiful.AI 截图灵感），不请设计师；视觉基准截图归档进 `docs/design-refs/`。

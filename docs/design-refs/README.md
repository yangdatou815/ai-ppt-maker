# Template Design References

本目录是 ai-ppt-maker 三套内置模板的**视觉基准说明**。它不是设计稿，而是工程实现的"对照表"——后续在 `backend/templates/<name>/` 里做 .pptx 母版、layout-mapping.yaml、配色变量时，都以本目录为准。

## 设计哲学

- **内容服务优先**：所有装饰元素（线条、色块、图标）必须为信息层级让路，不能喧宾夺主。
- **一页一主张**：每页只承载一个核心观点，bullets ≤ 5 条。
- **留白即专业**：版心四边留白 ≥ 7%（短边），不允许把内容贴边。
- **三色法则**：每套模板主色 ≤ 2 种 + 中性色（黑/白/灰）+ 1 个强调色，禁止多色彩虹堆叠。
- **字体两级**：标题字体 + 正文字体最多两套，标题 / 副标题 / 正文 / 注释四级字号即可。

## 三套模板速查

| 模板 | 适用场景 | 主色调 | 标题字体 | 正文字体 | 灵感来源 |
|---|---|---|---|---|---|
| `executive-dark` | 高管汇报、产品发布 | 深墨蓝 + 金 | 思源宋体 Heavy | 思源黑体 Regular | Apple Keynote 黑色封面、Bloomberg 终端配色 |
| `minimal-light` | 路演 BP、咨询提案 | 米白 + 炭灰 | Inter / 思源黑体 Bold | Inter / 思源黑体 Regular | Beautiful.AI 极简主题、Stripe Press |
| `tech-blue` | 技术汇报、SaaS 发布 | 科技蓝 + 青 | Inter / 思源黑体 ExtraBold | JetBrains Mono（数据）+ 思源黑体 | Slidev `seriph` / `default`、Vercel / Linear 官网 |

## 通用规范

### 版式集合（每套模板必须实现的 7 种 layout）

1. `cover` —— 封面：大标题、副标题、作者/日期/Logo。
2. `toc` —— 目录：3–6 章节列表，编号 + 章节名 + 一句话简述。
3. `section-divider` —— 章节过渡：超大编号 + 章节名 + 装饰线/色块。
4. `content-bullets` —— 文本要点页：H2 标题 + 3–5 条 bullets，可带短小说明。
5. `content-image` —— 图文页：左文右图 / 上文下图 两种变体，AI 自动选。
6. `content-table` —— 数据页：表格 + 简短解读（caption）。
7. `closing` —— 结尾页："Thank You" / "Q&A" + 联系方式。

### 字号基线（16:9，1280×720 单位：pt）

| 元素 | 字号 | 行距 |
|---|---|---|
| 封面主标题 | 54 | 1.15 |
| 封面副标题 | 24 | 1.3 |
| 章节过渡大编号 | 120 | 1.0 |
| 章节过渡章节名 | 36 | 1.2 |
| 页面 H2 标题 | 32 | 1.2 |
| 正文 bullet | 20 | 1.4 |
| 注释 / caption | 14 | 1.4 |
| 表头 / 表体 | 16 / 14 | 1.3 |

如内容超出，按 5.4 节 FR-4.4 规则：先缩字号 ≤ 2 档，再分页，绝不溢出。

### 占位符约定（layout-mapping.yaml）

每套模板 `layout-mapping.yaml` 至少声明：

```yaml
layouts:
  cover:        { index: 0, placeholders: { title: 0, subtitle: 1, footer: 10 } }
  toc:          { index: 1, placeholders: { title: 0, body: 1 } }
  section-divider: { index: 2, placeholders: { number: 10, title: 0 } }
  content-bullets: { index: 3, placeholders: { title: 0, body: 1 } }
  content-image:   { index: 4, placeholders: { title: 0, body: 1, image: 13 } }
  content-table:   { index: 5, placeholders: { title: 0, body: 1, caption: 14 } }
  closing:         { index: 6, placeholders: { title: 0, subtitle: 1 } }
theme:
  primary:   "#0B1F3A"
  accent:    "#C9A24E"
  neutral:   "#F4F1EA"
  text:      "#0B0B0B"
  text-mute: "#6B6B6B"
fonts:
  heading: "Source Han Serif CN"
  body:    "Source Han Sans CN"
  mono:    "JetBrains Mono"
```

### 字体回退策略

容器内必须预装：思源宋体（Source Han Serif CN）、思源黑体（Source Han Sans CN）、Inter、JetBrains Mono。
缺失时按以下顺序回退：

- 标题：模板首选 → 思源黑体 Bold → 系统 sans-serif。
- 正文：模板首选 → 思源黑体 Regular → 系统 sans-serif。
- 等宽：JetBrains Mono → 系统 monospace。

## "高大上"判定基线（用于 PR review / 设计走查）

- 视觉走查时，至少满足以下 6 条才算合格：
  1. 任意单页截图独立放出，不出现"程序员审美"标签（无突兀的 ASCII / 调试色 / 默认 PowerPoint 主题色）。
  2. 封面单独放出，能直接用于公司外部正式场合。
  3. 章节过渡页气势足够，不像普通正文页缩小版。
  4. 数据页（表格）可读性 > 装饰性，斑马纹 / 表头分割明确。
  5. 图文页中图片不被拉伸 / 不被裁掉关键内容。
  6. 在投影仪环境（亮度低、对比度差）下文字可读。

## 文件清单

- [executive-dark.md](executive-dark.md)
- [minimal-light.md](minimal-light.md)
- [tech-blue.md](tech-blue.md)

每个文件包含：调色板（含 hex）、字体细节、各版式 ASCII 草图、灵感参考链接、明确的 do / don't。

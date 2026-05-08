# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

Categories used (in order, omit empty ones):
`Added` · `Changed` · `Deprecated` · `Removed` · `Fixed` · `Security`.

## [Unreleased]

## [0.5.0] — 2026-05-08

Operational polish — installer hardening, project visibility, distribution.
No backend or renderer behaviour changes.

### Added
- **Project Roadmap view** (`M5-3`).
  - `frontend/src/views/RoadmapView.vue` renders the full
    Phase → Milestone → Item tree from `backend/roadmap.yaml`, JIRA-backlog
    style. Rows are colour-coded by status (`done` green, `in-progress`
    amber, `planned` red) with a status badge per item.
  - Drives the project rear-view-mirror: every commit that flips item
    status updates the page automatically (Hard Rule #11).
- **Asymptotic-then-linear progress bar** for outline + pptx generation.
  - `frontend/src/components/ProgressBar.vue`: linear advance up to 95 %
    over `EXPECTED_MS`, then holds; jumps to 100 % when the request
    resolves. Avoids the "stuck at 100 %" feel of pure linear bars and
    the "barely moves" feel of exponential ease-out.
- **Runtime debug toggle + live SSE log streaming** (`M5-3`).
  - `backend/app/api/debug.py`: `GET /api/debug/state`,
    `POST /api/debug/state`, `GET /api/debug/stream` (SSE).
  - `frontend/src/components/DebugDrawer.vue`: collapsible drawer with
    a kill-switch and a tail-streaming console.
- **Professional Windows installer icon + shortcuts.**
  - `assets/app.ico` — multi-resolution (16/32/48/64/128/256) icon with
    warm gradient background, white slide-deck glyph, gold AI sparkle.
  - `assets/_make_icon.py` — Pillow-based generator, easy to re-skin.
  - `install.bat` post-install creates three `.lnk` shortcuts pointing
    to `start.bat` / `install.bat` with the icon (Desktop + repo root).
- **Self-bootstrapping winget** in `install.bat`.
  - `_common.bat :install_winget` downloads the latest
    `Microsoft.DesktopAppInstaller.msixbundle` from the GitHub releases
    API via PowerShell + TLS 1.2, installs via `Add-AppxPackage`.
  - Triggered when winget is absent or detected as v1.0–v1.4 (heuristic
    for "too old to have working sources").
  - Download shows live progress: `curl.exe --progress-bar` first, then
    PowerShell BITS, then `Invoke-WebRequest` as final fallback.

### Changed
- **`install.bat` moved to `scripts/`** alongside the other batch files.
  Template auto-detects "running from `scripts/`" vs "running standalone
  in clone root", so behaviour is unchanged for both layouts.
- **`install.bat` ANSI colour UI** — green ok, yellow warn, red fail,
  cyan info. ESC captured via the `prompt $E` trick; conhost VT enabled
  via `HKCU\Console\VirtualTerminalLevel = 1`.
- **Aggressive PATH probing** for Node / Python / Git / Ollama after a
  winget install. New `:locate_*` helpers in `_common.bat` use static
  probes plus `where /R` recursive search under WinGet packages,
  `Program Files`, and `LocalAppData\Programs`. First hit prepends the
  parent directory to PATH and logs the find.

### Fixed
- **Don't trust `winget`'s exit code.** Old winget (v1.2 in some Win11
  installs) returns 0 from `winget install` even when the source
  database is corrupt and nothing was installed. The script now
  validates by re-locating the binary and, on miss, runs
  `winget source reset --force` + `winget source update` and retries
  once before bailing with an honest manual-install message.



M2 part 3 — image/table layouts + editorial UI redesign.
M2 milestone closes here.

### Added
- **M2-3 — image / table layout dispatch in the renderer.**
  - `backend/app/render/pptx_renderer.py`: `_pick_layout(section)` picks
    one of `content-bullets` / `content-image` / `content-table`. Explicit
    `section.layout_hint` wins; otherwise we infer from which payload is
    populated (`image` → image, `table` → table, else bullets). Mismatched
    hints (e.g. `content-table` with no `table`) degrade to bullets
    instead of raising.
  - `_image_section_slide`: bullets on the left half (5.6"), embedded image
    on the right (5.9 × 4.0"). When the file is missing, unreadable, or
    fails python-pptx's image probe, falls back to a placeholder rectangle
    with the caption / file_id rendered centred — never aborts the slide.
  - `_table_section_slide`: native pptx table with themed header row
    (filled `theme.primary`, bold `theme.heading_font` in `theme.text`),
    body rows in `theme.body_font` `theme.primary`. Caps at 14 data rows
    and emits a `… N more rows truncated` note.
  - `render_outline()` gains a kw-only `uploads_dir: Path | None`. `None`
    keeps the old behaviour (every image renders as a placeholder), so
    existing tests / outline-only previews don't break.
  - **Path-traversal guard**: image file_id resolution rejects anything
    that doesn't `relative_to(uploads_dir)`. A malicious outline carrying
    `file_id: "../../etc/passwd"` cannot exfiltrate or embed files outside
    the workspace.
- **`POST /api/upload` — image upload for slide embed.**
  - `backend/app/api/upload.py`: streams the upload in 1 MiB chunks and
    enforces `Settings.max_upload_mb` *during* the read so an oversized
    body never lands fully in memory before being rejected.
  - Whitelisted MIME types: `image/png`, `image/jpeg`, `image/gif`,
    `image/webp`. SVG / TIFF deliberately excluded (would need
    server-side rasterisation we don't run).
  - Stored as `<workspace_dir>/uploads/<uuid><ext>`; returns
    `{ file_id, bytes, content_type }`. Empty body → `400`, oversized →
    `413`, unsupported type → `415`.
  - Tests: 4 new integration cases (`tests/integration/test_upload_api.py`).
- **Frontend M2-3 — per-section image/table attachments.**
  - `frontend/src/api/client.ts`: tightens `OutlineSection.image` /
    `.table` types from `unknown` to typed `ImageRef` / `TableData`; new
    `uploadImage(file)` helper (multipart POST) and
    `parseTableInput(text, caption?)` (TSV with comma fallback, first
    non-blank line as headers, blanks stripped).
  - `frontend/src/components/OutlineForm.vue`: every section in the result
    preview now exposes `+ 添加图片` (file picker → `/api/upload` →
    attaches `ImageRef` and sets `layout_hint = 'content-image'`) and
    `+ 添加表格` (modal editor parses pasted TSV/CSV → attaches
    `TableData` and sets `layout_hint = 'content-table'`). Existing
    attachments shown as chips with edit / remove links.
  - 5 new vitest cases on `parseTableInput` + 2 new component cases on
    image-upload and table-edit flows. 18 frontend tests pass total.
- **Renderer test suite expanded.** 7 new unit tests in
  `tests/unit/test_pptx_renderer.py`: `_pick_layout` dispatch (×3), table
  rendering with native pptx table shape (×2), image happy path with a
  hand-rolled minimal-PNG fixture, missing-file placeholder, path-
  traversal rejection. 59 backend tests pass total, 92 % coverage, ruff
  clean.

### Changed
- **Editorial / artistic-minimal frontend redesign.** `frontend/src/styles.css`
  rewritten end-to-end. No template / component logic touched — only
  CSS — so existing tests continue to pass.
  - System-font-only stack (offline-friendly): native serif italic for
    display (Iowan / Baskerville / Times / Georgia + CJK fallback), Inter /
    system-ui for UI text, ui-monospace for tracked uppercase micro-labels.
  - Mono palette: warm off-white paper (`#f6f4ee`) + ink (`#111`). State
    signals (ok / warn / err) in deep, muted tones; no decorative colour.
  - No rounded corners (`border-radius: 0` throughout), no shadows, no
    gradients. Hierarchy via hairline 1 px rules at
    `rgba(17,17,17,0.12)` and generous whitespace (96–128 px between
    major sections).
  - Outline-preview section numbers now rendered as 48 px italic serif
    numerals bleeding into a 96 px left gutter (chapter marks, not UI
    bullets). Bullets themselves use em-dash markers; emphasis bullets
    get a black dash, mute ones grey.
  - Buttons reframed as flat blocks with mono uppercase tracked labels;
    hover inverts (paper-on-ink → ink-on-paper). Selected template card
    flips to ink background with paper text — full inversion rather than a
    coloured ring.

### Security
- Image embed path traversal closed (see M2-3 above): outlines cannot
  escape `uploads_dir`. Negative test in
  `test_render_image_section_rejects_path_traversal`.
- Upload size cap enforced *during* stream read, not after — prevents an
  attacker from DoS-ing memory by sending a multi-GB body that we'd then
  reject post-buffer.

## [0.3.0] — 2026-05-07

M2 part 2 — render → editable .pptx download. Bridges the outline
pipeline to the user's hard drive.

### Fixed
- **CI silent dependency on `eval_type_backport`.** Pydantic v2 evaluates
  PEP 604 union annotations (`str | None`) at class-build time, which on
  Python 3.9 (our minimum) raises `TypeError: Unable to evaluate type
  annotation 'str | None'` unless `eval_type_backport` is installed. Local
  `pytest` passed because some dev tool's transitive deps had pulled it in;
  Gitee Go's clean CI environment did not. Added
  `eval_type_backport>=0.2; python_version < '3.10'` to
  `backend/pyproject.toml` so any 3.9 install gets it explicitly.

### Changed
- **Gitee Go pipelines back online — `.workflow/master-pipeline.yml` rewritten
  for Gitee Go 2.x schema** (verified saving + triggering on 2026-05-07).
  Key schema differences from the old 1.x docs we'd been writing against:
  - `displayName` must be ASCII (`[A-Za-z0-9_-]`); 中文/空格 rejected with
    「当前流水线名称不符合规范」.
  - Step plugin fields (`pythonVersion` / `commands`) sit directly under
    `step:`, **not** nested under `inputs:` like some 2.x examples imply.
  - Every stage requires `strategy: naturally` + `trigger: auto`.
  - Every step requires `artifacts:`, `caches:`, `notify:` lists (empty OK)
    and `strategy.retry: '0'`.
  - Top-level `triggers.push.branches` uses `prefix:` (prefix match), not
    `include:` / `exclude:` from the 1.x docs.
  - `build@nodejs` step intentionally absent for now — Node plugin's real
    schema not yet captured; will add once we sample one from the
    graphical editor.

  Old docs at `.workflow.disabled/` retired; that directory removed in
  this commit.

### Added
- **M2-2 — outline → editable .pptx download is live.** End-to-end flow now
  works in the browser: pick template → paste content → 「生成大纲」 →
  「生成 PPT 并下载」. Previously the second button was missing because
  `/api/generate` was a 501 stub.
  - `backend/app/render/pptx_renderer.py` (new): programmatic-master
    renderer using `python-pptx 1.0.2`, no real `master.pptx` required.
    Builds a 16:9 deck — cover slide (theme `primary` background + accent
    rule + title/subtitle/footer), one section slide per `OutlineDoc`
    section (`01 / 05` gutter in `accent`, heading in `primary`, bullets
    bold-emphasised when `bullet.emphasis=true`, speaker notes routed to
    the slide's notes pane), and a closing slide. Theme tokens parsed
    defensively from `templates/<name>/layout-mapping.yaml`; garbage hex
    falls back to a sane default rather than 500-ing the request.
  - `backend/app/api/generate.py`: `POST /api/generate` accepts
    `{ outline: OutlineDoc, template: str }`, streams the .pptx bytes back
    with the right MIME type, an RFC 5987 `Content-Disposition` (so CJK
    titles survive the latin-1 header encoding), and `X-Render-Elapsed-Ms`
    / `X-Render-Template` debug headers. Unknown template → 404; malformed
    outline → 422; render error → 500 with detail.
  - `frontend/src/components/OutlineForm.vue`: new "生成 PPT 并下载" button
    in the result footer. Disabled until both an outline result and a
    selected template exist; explicit `请先选择模板` hint when the latter
    is missing. POSTs to `/api/generate`, receives a `Blob`, and triggers
    a real download via `URL.createObjectURL` + a hidden `<a download>`
    (with delayed `revokeObjectURL` for Safari).
  - `frontend/src/api/client.ts`: `generatePptx()` + `triggerBlobDownload()`
    helpers; the latter is exported separately so it can be unit-tested
    without touching the network.
  - Tests: 4 new backend integration cases (`test_generate_api.py`) covering
    happy path, 404, 422, and all 3 shipped templates; 4 new renderer unit
    cases (`test_pptx_renderer.py`); 2 new vitest cases for the button
    (disabled-without-template and full click-to-download with mocked fetch
    + URL.createObjectURL).
- Frontend M2 outline UI: textarea + source-type/language selectors + live
  elapsed timer, posts to `/api/outline` and renders the resulting outline
  with section numbering, emphasis bullets, and a fallback / LLM badge so
  the operator can tell instantly which path produced the result.
  - `frontend/src/components/OutlineForm.vue`: char-count guard against the
    20 000-char limit; "载入示例" preset; tick-driven elapsed display while
    awaiting the response.
  - `frontend/src/api/client.ts`: typed `OutlineResponse` / `OutlineDoc` /
    `OutlineSection` / `Bullet` + `createOutline()` wrapper that surfaces
    backend `detail` text on `4xx`/`5xx`.
  - `frontend/src/App.vue`: rebuilt to compose `TemplatePicker` and
    `OutlineForm`; on mount calls `/api/healthz` and shows backend version
    + active model. Now also forwards the selected template name to
    `OutlineForm` via the new `:template` prop so the generate button can
    reach it without extra plumbing.

### Removed
- `POST /api/generate` 501 stub and its `test_generate_stub_501` regression
  test, both replaced by the real implementation above.

### Fixed
- **Silent-fallback bug #2 — corporate proxy intercepts loopback Ollama calls.**
  When the launching shell had `http_proxy` set but no `NO_PROXY`, the
  backend's `httpx.Client` routed every request — including
  `http://127.0.0.1:11434/api/chat` — through the proxy, which returned
  `403 Forbidden` for the internal IP. The pipeline silently flipped to
  the rule-based fallback even though Ollama was healthy locally. Fixed by
  passing `trust_env=False` to the LLM client's `httpx.Client`: Ollama is
  always a direct connection by design (loopback for bare-metal,
  `host.docker.internal` for docker-compose, private LAN for remote-GPU
  setups), so reading proxy env vars there only ever creates this trap.
  Diagnostic for next time: `tr '\0' '\n' < /proc/<pid>/environ | grep -i
  proxy` shows what the running process actually inherited.
- `OutlineDoc.cover_meta` previously rejected `null` values, causing
  perfectly good LLM output to fall through to the rule-based fallback
  (the "Fallback (LLM 不可用)" badge appeared in the UI even when Ollama
  responded successfully). qwen2.5 routinely emits
  `cover_meta: { "date": null, "company": null }` for fields it doesn't
  know. Schema now drops `null` values pre-validation and coerces the rest
  to string. Verified against the same HotPulse sample: previously
  `used_fallback=true` with a Pydantic validation error in logs, now
  `used_fallback=false` with 5 LLM-generated sections.
- `app/outline/prompts.py` system prompt now explicitly tells the model to
  OMIT optional keys rather than emit `null`, reducing the rate at which
  the salvage path is needed.
- Frontend M2 outline UI: textarea + source-type/language selectors + live
  elapsed timer, posts to `/api/outline` and renders the resulting outline
  with section numbering, emphasis bullets, and a fallback / LLM badge so
  the operator can tell instantly which path produced the result.
  - `frontend/src/components/OutlineForm.vue`: char-count guard against the
    20 000-char limit; "载入示例" preset; tick-driven elapsed display while
    awaiting the response.
  - `frontend/src/api/client.ts`: typed `OutlineResponse` / `OutlineDoc` /
    `OutlineSection` / `Bullet` + `createOutline()` wrapper that surfaces
    backend `detail` text on `4xx`/`5xx`.
  - `frontend/src/App.vue`: rebuilt to compose `TemplatePicker` and
    `OutlineForm`; on mount calls `/api/healthz` and shows backend version
    + active model.
  - 6 new vitest cases in `frontend/tests/OutlineForm.test.ts` (empty-state
    submit guard, oversize guard, success path, fallback badge, error path,
    sample loader).
- Centralised logging setup ([`backend/app/logging_setup.py`](backend/app/logging_setup.py))
  with per-module level overrides — the operator-facing log switch.
  - Root level via `LOG_LEVEL` env (`DEBUG`/`INFO`/`WARNING`/`ERROR`/`CRITICAL`).
  - Per-logger overrides via `LOG_LEVEL_OVERRIDES` env, e.g.
    `LOG_LEVEL_OVERRIDES=app.outline=DEBUG,httpx=WARNING`.
  - Pinned format `%(asctime)s %(levelname)-7s %(name)s :: %(message)s` for
    grep/awk friendliness; uvicorn loggers realigned to the same level.
  - Idempotent: safe under uvicorn `--reload` and pytest re-imports.
  - 8 new unit tests in `tests/unit/test_logging_setup.py`.
- DEBUG-level diagnostics on the outline pipeline so operators can pinpoint
  failures without changing source:
  - `app.outline.llm_client`: URL/model/timeout, prompt char counts,
    eval_count, eval_duration_ms, response char count.
  - `app.outline.repair`: which repair strategy succeeded; on failure logs
    last error and input length.
  - `app.outline.fallback`: detected language, raw vs kept section counts.
  - `app.api.outline`: request shape on entry; first 500 chars of unusable
    LLM output before falling back.
- README: new "排错：打开 DEBUG 日志" section with a per-symptom override
  table.
- `.env.example`: documents `LOG_LEVEL_OVERRIDES`.

### Changed
- `app/main.py` no longer hard-codes `INFO`; calls `setup_logging(settings.log_level)`
  so the `LOG_LEVEL` env var actually takes effect (it was wired to config but
  ignored at runtime).

## [0.2.0] — 2026-05-07

M2 part 1 — outline pipeline.

### Added
- `POST /api/outline` real implementation: local Ollama (`/api/chat`,
  `format=json`) → JSON repair → rule-based fallback.
  - `app/outline/llm_client.py`: single retry, strict timeout, returns
    `LlmResponse(raw_content, model, eval_count, eval_duration_ns)`.
  - `app/outline/prompts.py`: system prompt locks the `OutlineDoc` schema;
    user content wrapped in `<user_content>...</user_content>` to harden
    against prompt injection (architecture TD-2 / §5).
  - `app/outline/repair.py`: progressive repair (strip code fence, extract
    first balanced `{}`, drop trailing commas, multi-strategy merge).
  - `app/outline/fallback.py`: when the LLM is unreachable or its output
    fails validation, build an `OutlineDoc` from Markdown headings or
    paragraph splits (CJK / ASCII auto-detected).
- Response now carries `used_fallback`, `used_model`, `elapsed_ms` for
  observability (architecture §7).
- Input guardrails: 20 000-char content cap (FR-1.1) → `413`; empty body →
  `422`.
- Tests: `tests/unit/test_repair.py` (7), `tests/unit/test_fallback.py` (4),
  `tests/integration/test_outline_api.py` (7). Covers happy path, fenced
  JSON, garbage output, LLM down, oversize, empty, schema mismatch.
- E2E trial verified: real Ollama (`qwen2.5:7b-instruct-q4_K_M`, CPU)
  produced 5-section outline in 43.6 s with `used_fallback=false`.

### Changed
- The M1 `501` stub assertion (`test_outline_stub_501`) is replaced with
  `test_outline_falls_back_when_llm_down`, asserting `200 + used_fallback=true`
  via an injected failing client. Behaviour-first, not endpoint-shape-first.

## [0.1.0] — 2026-05-06

First runnable skeleton.

### Added
- PRD ([PRD.md](PRD.md)), visual baselines
  ([docs/design-refs/](docs/design-refs/)), technical design
  ([docs/architecture.md](docs/architecture.md)).
- Backend FastAPI skeleton: `/api/templates`, `/api/outline`, `/api/generate`,
  `/api/jobs/{id}` routes; first two return real data, the latter two are
  reserved for v0.2.
- Three template `layout-mapping.yaml` skeletons (real `master.pptx` deferred):
  `executive-dark`, `minimal-light`, `tech-blue`.
- Frontend Vue 3 + Vite + TypeScript scaffold; landing page fetches the
  template list and renders cards.
- Single-port serve: backend uvicorn mounts `frontend/dist` and SPA-fallbacks
  unmatched paths to `index.html`.
- `docker-compose.yml`: backend + frontend (nginx); reaches host Ollama via
  `host.docker.internal`.
- Cross-platform deployment scripts (pattern ported from `meeting_summary`):
  - Windows: root `install.bat` (single-file, winget bootstraps Python / Node /
    Git / Ollama) + `scripts/{deploy,start,stop,cleanup}.bat`.
  - POSIX: `scripts/{deploy,start,stop,cleanup}.sh`.
  - Shared library: `scripts/_common.bat` + `scripts/_ui.sh` +
    `scripts/build_scripts.py` (CRLF enforcement, `--check` drift gate).
- DoD script (`scripts/dod.sh`) and GitHub Actions CI (unit, lint, drift,
  `build_scripts.py --check`).
- Repository hygiene: `.gitattributes` (LF default, `*.bat` CRLF),
  `.gitignore`, `.env.example`, `.github/copilot-instructions.md`.

### Known Limitations
- `POST /api/generate` is still a `501` stub — no `.pptx` rendering yet (M2-2).
- No outline editor, no thumbnail preview, no multimodal input
  (M3 / M4 milestones).

<!--
Comparison links — fill in once the project is pushed to a Git remote.

[Unreleased]: https://gitee.com/<owner>/ai-ppt-maker/compare/v0.2.0...HEAD
[0.2.0]: https://gitee.com/<owner>/ai-ppt-maker/compare/v0.1.0...v0.2.0
[0.1.0]: https://gitee.com/<owner>/ai-ppt-maker/releases/tag/v0.1.0
-->

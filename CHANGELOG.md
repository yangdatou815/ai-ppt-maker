# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

Categories used (in order, omit empty ones):
`Added` · `Changed` · `Deprecated` · `Removed` · `Fixed` · `Security`.

## [Unreleased]

### Changed
- **Gitee Go pipelines temporarily disabled.** Renamed `.workflow/` →
  `.workflow.disabled/`. The hand-written branch / pr / master YAMLs match
  the Gitee Go 1.x reference but the 2026 console rejects them with
  「流水线配置有误」 and several of Gitee's official YAML-schema docs now
  return 404, so we can't fix in-place. Files kept for reference + diff
  basis once the pipelines are reconfigured via Gitee Go's graphical
  editor; restart steps documented in `.workflow.disabled/README.md`. DoD
  commands (`bash scripts/dod.sh`, `python scripts/build_scripts.py
  --check`) remain unchanged and still pass locally.

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

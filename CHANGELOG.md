# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning 2.0.0](https://semver.org/spec/v2.0.0.html).

Categories used (in order, omit empty ones):
`Added` · `Changed` · `Deprecated` · `Removed` · `Fixed` · `Security`.

## [Unreleased]

### Added
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

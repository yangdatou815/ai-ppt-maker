export interface TemplateInfo {
  name: string
  display_name: string
  description: string
  tags: string[]
  theme: Record<string, string>
  fonts: Record<string, string>
  has_master: boolean
  thumbnail_url: string | null
}

export interface Bullet {
  text: string
  note: string | null
  emphasis: boolean
}

export interface ImageRef {
  file_id: string
  caption: string | null
}

export interface TableData {
  headers: string[]
  rows: string[][]
  caption: string | null
}

export type LayoutHint = 'content-bullets' | 'content-image' | 'content-table' | null

export interface OutlineSection {
  heading: string
  bullets: Bullet[]
  image: ImageRef | null
  table: TableData | null
  speaker_notes: string | null
  layout_hint: LayoutHint
}

export interface OutlineDoc {
  title: string
  subtitle: string | null
  language: string
  sections: OutlineSection[]
  cover_meta?: Record<string, string>
}

export interface OutlineResponse {
  outline: OutlineDoc
  used_fallback: boolean
  used_model: string | null
  elapsed_ms: number
}

const BASE = import.meta.env.VITE_API_BASE ?? '/api'

export async function listTemplates(): Promise<TemplateInfo[]> {
  const r = await fetch(`${BASE}/templates`)
  if (!r.ok) throw new Error(`GET /templates failed: ${r.status}`)
  return r.json()
}

export async function healthz(): Promise<{ ok: boolean; version: string; model: string }> {
  const r = await fetch(`${BASE}/healthz`)
  if (!r.ok) throw new Error(`GET /healthz failed: ${r.status}`)
  return r.json()
}

export async function createOutline(args: {
  content: string
  source_type?: string
  language?: 'auto' | 'zh' | 'en'
}): Promise<OutlineResponse> {
  const r = await fetch(`${BASE}/outline`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      source_type: args.source_type ?? 'text',
      content: args.content,
      language: args.language ?? 'auto',
    }),
  })
  if (!r.ok) {
    let detail = ''
    try {
      detail = (await r.json()).detail ?? ''
    } catch {
      /* ignore */
    }
    throw new Error(`POST /outline failed: ${r.status}${detail ? ' — ' + detail : ''}`)
  }
  return r.json()
}

export interface ClassifyTemplateResponse {
  template: string
  confidence: number
  reason: string
  used_fallback: boolean
  used_model: string | null
  elapsed_ms: number
}

// --- Async job types ---
export interface JobProgress {
  stage: string
  detail: string
  percent: number
}

export interface JobStatus {
  id: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  progress: JobProgress
  error: string | null
  created_at: number
  completed_at: number | null
}

export async function createOutlineAsync(args: {
  content: string
  source_type?: string
  language?: 'auto' | 'zh' | 'en'
}): Promise<{ job_id: string }> {
  const r = await fetch(`${BASE}/outline/async`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      source_type: args.source_type ?? 'text',
      content: args.content,
      language: args.language ?? 'auto',
    }),
  })
  if (!r.ok) {
    let detail = ''
    try {
      detail = (await r.json()).detail ?? ''
    } catch {
      /* ignore */
    }
    throw new Error(`POST /outline/async failed: ${r.status}${detail ? ' — ' + detail : ''}`)
  }
  return r.json()
}

export async function pollJob(jobId: string): Promise<JobStatus> {
  const r = await fetch(`${BASE}/jobs/${jobId}`)
  if (!r.ok) throw new Error(`GET /jobs/${jobId} failed: ${r.status}`)
  return r.json()
}

export async function getJobResult(jobId: string): Promise<OutlineResponse> {
  const r = await fetch(`${BASE}/jobs/${jobId}/result`)
  if (!r.ok) throw new Error(`GET /jobs/${jobId}/result failed: ${r.status}`)
  return r.json()
}

export async function classifyTemplate(args: {
  content: string
  language?: 'auto' | 'zh' | 'en'
}): Promise<ClassifyTemplateResponse> {
  const r = await fetch(`${BASE}/classify-template`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      content: args.content,
      language: args.language ?? 'auto',
    }),
  })
  if (!r.ok) {
    let detail = ''
    try {
      detail = (await r.json()).detail ?? ''
    } catch {
      /* ignore */
    }
    throw new Error(
      `POST /classify-template failed: ${r.status}${detail ? ' — ' + detail : ''}`,
    )
  }
  return r.json()
}

export interface GeneratePptxResult {
  blob: Blob
  filename: string
  template: string
  elapsedMs: number
}

export async function generatePptx(args: {
  outline: OutlineDoc
  template: string
}): Promise<GeneratePptxResult> {
  const r = await fetch(`${BASE}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ outline: args.outline, template: args.template }),
  })
  if (!r.ok) {
    let detail = ''
    try {
      detail = (await r.json()).detail ?? ''
    } catch {
      /* ignore */
    }
    throw new Error(`POST /generate failed: ${r.status}${detail ? ' — ' + detail : ''}`)
  }
  const blob = await r.blob()
  const cd = r.headers.get('Content-Disposition') ?? ''
  const m = /filename="?([^";]+)"?/.exec(cd)
  const filename = m ? m[1] : `${args.template}.pptx`
  const elapsed = Number(r.headers.get('X-Render-Elapsed-Ms') ?? '0') || 0
  return { blob, filename, template: args.template, elapsedMs: elapsed }
}

/** Trigger a browser download for an in-memory blob. Pulled out for testing. */
export function triggerBlobDownload(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  // Revoke on next tick — Safari needs the URL to still be alive when click() runs.
  setTimeout(() => URL.revokeObjectURL(url), 0)
}

export interface UploadResult {
  file_id: string
  bytes: number
  content_type: string
}

export async function uploadImage(file: File): Promise<UploadResult> {
  const fd = new FormData()
  fd.append('file', file)
  const r = await fetch(`${BASE}/upload`, { method: 'POST', body: fd })
  if (!r.ok) {
    let detail = ''
    try {
      detail = (await r.json()).detail ?? ''
    } catch {
      /* ignore */
    }
    throw new Error(`POST /upload failed: ${r.status}${detail ? ' — ' + detail : ''}`)
  }
  return r.json()
}

/**
 * Parse a tab- or comma-separated block into a TableData. First non-blank
 * line is treated as the header row. Empty input → null. Tabs win over
 * commas if both appear (tabs are clipboard-from-Excel friendly).
 */
export function parseTableInput(text: string, caption: string | null = null): TableData | null {
  const lines = text
    .split(/\r?\n/)
    .map((l) => l.trim())
    .filter((l) => l.length > 0)
  if (lines.length === 0) return null
  const sep = lines[0].includes('\t') ? '\t' : ','
  const split = (l: string) => l.split(sep).map((c) => c.trim())
  const headers = split(lines[0])
  const rows = lines.slice(1).map(split)
  return { headers, rows, caption }
}

// ---------------------------------------------------------------------------
// Debug toggle + log streaming
// ---------------------------------------------------------------------------

export interface DebugState {
  enabled: boolean
  level: string
  buffered: number
}

export interface LogLine {
  ts: number
  level: string
  name: string
  msg: string
}

export async function getDebugState(): Promise<DebugState> {
  const r = await fetch(`${BASE}/debug`)
  if (!r.ok) throw new Error(`GET /debug failed: ${r.status}`)
  return r.json()
}

export async function setDebugState(enabled: boolean): Promise<DebugState> {
  const r = await fetch(`${BASE}/debug`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled }),
  })
  if (!r.ok) throw new Error(`POST /debug failed: ${r.status}`)
  return r.json()
}

/**
 * Open a Server-Sent Events subscription to the live log stream.
 * Returns the EventSource so the caller can `.close()` on unmount.
 * `onLine` is invoked for each parseable record; junk lines are ignored.
 */
export function openLogStream(onLine: (l: LogLine) => void): EventSource {
  const es = new EventSource(`${BASE}/debug/logs/stream`)
  es.onmessage = (ev) => {
    try {
      const obj = JSON.parse(ev.data) as LogLine
      onLine(obj)
    } catch {
      /* ignore malformed frame */
    }
  }
  return es
}

// ---------------------------------------------------------------------------
// Roadmap (project bird's-eye view)
// ---------------------------------------------------------------------------

export type RoadmapStatus = 'done' | 'in-progress' | 'planned'

export interface RoadmapItem {
  name: string
  status: RoadmapStatus
}

export interface RoadmapMilestone {
  id: string
  name: string
  summary: string | null
  items: RoadmapItem[]
}

export interface RoadmapPhase {
  id: string
  name: string
  summary: string | null
  milestones: RoadmapMilestone[]
}

export interface RoadmapStats {
  total: number
  done: number
  in_progress: number
  planned: number
  done_pct: number
}

export interface RoadmapDoc {
  phases: RoadmapPhase[]
  stats: RoadmapStats
}

export async function getRoadmap(): Promise<RoadmapDoc> {
  const r = await fetch(`${BASE}/roadmap`)
  if (!r.ok) throw new Error(`GET /roadmap failed: ${r.status}`)
  return r.json()
}

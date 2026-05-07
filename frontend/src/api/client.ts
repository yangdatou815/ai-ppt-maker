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

export interface OutlineSection {
  heading: string
  bullets: Bullet[]
  image: unknown | null
  table: unknown | null
  speaker_notes: string | null
  layout_hint: string | null
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

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

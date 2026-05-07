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

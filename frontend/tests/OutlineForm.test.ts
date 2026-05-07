import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import OutlineForm from '../src/components/OutlineForm.vue'
import type { OutlineResponse } from '../src/api/client'

const FAKE_OK: OutlineResponse = {
  outline: {
    title: 'Demo',
    subtitle: null,
    language: 'zh',
    sections: [
      {
        heading: '段一',
        bullets: [
          { text: '要点 A', note: null, emphasis: true },
          { text: '要点 B', note: '补充', emphasis: false },
        ],
        image: null,
        table: null,
        speaker_notes: '主持人备注',
        layout_hint: 'content-bullets',
      },
    ],
  },
  used_fallback: false,
  used_model: 'qwen2.5:7b-instruct',
  elapsed_ms: 1234,
}

const originalFetch = global.fetch

beforeEach(() => {
  vi.useRealTimers()
})

afterEach(() => {
  global.fetch = originalFetch
  vi.restoreAllMocks()
})

describe('OutlineForm', () => {
  it('disables submit when content is empty', () => {
    const w = mount(OutlineForm)
    const btn = w.find('button.primary')
    expect((btn.element as HTMLButtonElement).disabled).toBe(true)
  })

  it('flags content over 20k chars and disables submit', async () => {
    const w = mount(OutlineForm)
    await w.find('textarea').setValue('a'.repeat(20_001))
    expect(w.find('.char-count').classes()).toContain('over')
    expect((w.find('button.primary').element as HTMLButtonElement).disabled).toBe(true)
  })

  it('calls /api/outline and renders the result', async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      json: async () => FAKE_OK,
    })) as unknown as typeof fetch
    global.fetch = fetchMock

    const w = mount(OutlineForm)
    await w.find('textarea').setValue('hello world')
    await w.find('button.primary').trigger('click')
    await flushPromises()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    const [url, init] = (fetchMock as unknown as ReturnType<typeof vi.fn>).mock.calls[0]
    expect(url).toContain('/outline')
    const body = JSON.parse((init as RequestInit).body as string)
    expect(body.content).toBe('hello world')
    expect(body.source_type).toBe('text')
    expect(body.language).toBe('auto')

    expect(w.text()).toContain('Demo')
    expect(w.text()).toContain('段一')
    expect(w.text()).toContain('LLM 生成')
    expect(w.text()).toContain('qwen2.5:7b-instruct')
  })

  it('shows fallback badge when used_fallback=true', async () => {
    const fb: OutlineResponse = { ...FAKE_OK, used_fallback: true, used_model: null }
    global.fetch = vi.fn(async () => ({
      ok: true,
      json: async () => fb,
    })) as unknown as typeof fetch

    const w = mount(OutlineForm)
    await w.find('textarea').setValue('x')
    await w.find('button.primary').trigger('click')
    await flushPromises()

    const badge = w.find('.badge')
    expect(badge.classes()).toContain('fallback')
    expect(badge.text()).toContain('Fallback')
  })

  it('renders error message when API fails', async () => {
    global.fetch = vi.fn(async () => ({
      ok: false,
      status: 413,
      json: async () => ({ detail: 'too long' }),
    })) as unknown as typeof fetch

    const w = mount(OutlineForm)
    await w.find('textarea').setValue('x')
    await w.find('button.primary').trigger('click')
    await flushPromises()

    expect(w.find('.err').exists()).toBe(true)
    expect(w.find('.err').text()).toContain('413')
    expect(w.find('.err').text()).toContain('too long')
  })

  it('load-sample button populates textarea', async () => {
    const w = mount(OutlineForm)
    await w.find('button.link').trigger('click')
    const ta = w.find('textarea').element as HTMLTextAreaElement
    expect(ta.value).toContain('HotPulse')
  })
})

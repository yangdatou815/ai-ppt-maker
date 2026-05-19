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

const JOB_ID = 'test-job-123'

/** Build a fetch mock that handles the async outline flow. */
function mockAsyncOutlineFetch(outlineResult: OutlineResponse = FAKE_OK) {
  return vi.fn(async (url: string) => {
    const u = String(url)
    if (u.includes('/outline/async')) {
      return { ok: true, json: async () => ({ job_id: JOB_ID }) } as unknown as Response
    }
    if (u.includes(`/jobs/${JOB_ID}/result`)) {
      return {
        ok: true,
        json: async () => ({
          outline: outlineResult.outline,
          used_fallback: outlineResult.used_fallback,
          used_model: outlineResult.used_model,
        }),
      } as unknown as Response
    }
    if (u.includes(`/jobs/${JOB_ID}`)) {
      return {
        ok: true,
        json: async () => ({
          id: JOB_ID,
          status: 'completed',
          progress: { stage: 'done', detail: '', percent: 100 },
          error: null,
          created_at: 0,
          completed_at: 1,
        }),
      } as unknown as Response
    }
    return { ok: false, status: 404, json: async () => ({}) } as unknown as Response
  }) as unknown as typeof fetch
}

const originalFetch = global.fetch

beforeEach(() => {
  vi.useFakeTimers()
})

afterEach(() => {
  global.fetch = originalFetch
  vi.restoreAllMocks()
  vi.useRealTimers()
})

/** Advance timers and flush all pending promises (needed for polling loops). */
async function advanceAndFlush(ms = 600) {
  vi.advanceTimersByTime(ms)
  await flushPromises()
  vi.advanceTimersByTime(ms)
  await flushPromises()
}

describe('OutlineForm', () => {
  it('disables submit when content is empty', () => {
    const w = mount(OutlineForm)
    const btn = w.find('button.primary')
    expect((btn.element as HTMLButtonElement).disabled).toBe(true)
  })

  it('flags content over 50k chars and disables submit', async () => {
    const w = mount(OutlineForm)
    await w.find('textarea').setValue('a'.repeat(50_001))
    expect(w.find('.char-count').classes()).toContain('over')
    expect((w.find('button.primary').element as HTMLButtonElement).disabled).toBe(true)
  })

  it('calls /api/outline/async and renders the result', async () => {
    const fetchMock = mockAsyncOutlineFetch()
    global.fetch = fetchMock

    const w = mount(OutlineForm)
    await w.find('textarea').setValue('hello world')
    await w.find('button.primary').trigger('click')
    await advanceAndFlush()

    expect(fetchMock).toHaveBeenCalled()
    const urls = (fetchMock as unknown as ReturnType<typeof vi.fn>).mock.calls.map(
      (c: unknown[]) => String(c[0]),
    )
    expect(urls.some((u: string) => u.includes('/outline/async'))).toBe(true)

    const outlineCall = (fetchMock as unknown as ReturnType<typeof vi.fn>).mock.calls.find(
      (c: unknown[]) => String(c[0]).includes('/outline/async'),
    )!
    const body = JSON.parse((outlineCall[1] as RequestInit).body as string)
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
    global.fetch = mockAsyncOutlineFetch(fb)

    const w = mount(OutlineForm)
    await w.find('textarea').setValue('x')
    await w.find('button.primary').trigger('click')
    await advanceAndFlush()

    const badge = w.find('.badge')
    expect(badge.classes()).toContain('fallback')
    expect(badge.text()).toContain('Fallback')
  })

  it('renders error message when API fails', async () => {
    global.fetch = vi.fn(async (url: string) => {
      const u = String(url)
      if (u.includes('/outline/async')) {
        return { ok: true, json: async () => ({ job_id: JOB_ID }) } as unknown as Response
      }
      if (u.includes(`/jobs/${JOB_ID}`)) {
        return {
          ok: true,
          json: async () => ({
            id: JOB_ID,
            status: 'failed',
            progress: { stage: 'error', detail: '', percent: 0 },
            error: '生成失败',
            created_at: 0,
            completed_at: 1,
          }),
        } as unknown as Response
      }
      return { ok: false, status: 404, json: async () => ({}) } as unknown as Response
    }) as unknown as typeof fetch

    const w = mount(OutlineForm)
    await w.find('textarea').setValue('x')
    await w.find('button.primary').trigger('click')
    await advanceAndFlush()

    expect(w.find('.err').exists()).toBe(true)
    expect(w.find('.err').text()).toContain('生成失败')
  })

  it('load-sample button populates textarea', async () => {
    const w = mount(OutlineForm)
    await w.find('button.link').trigger('click')
    const ta = w.find('textarea').element as HTMLTextAreaElement
    expect(ta.value).toContain('HotPulse')
  })

  it('hides the generate button when no template is selected', async () => {
    global.fetch = mockAsyncOutlineFetch()

    const w = mount(OutlineForm, { props: { template: null } })
    await w.find('textarea').setValue('x')
    await w.find('button.primary').trigger('click')
    await advanceAndFlush()

    const buttons = w.findAll('.result-actions button.primary')
    expect(buttons).toHaveLength(1)
    expect((buttons[0].element as HTMLButtonElement).disabled).toBe(true)
    expect(w.find('.result-actions .hint').text()).toContain('请先选择模板')
  })

  it('clicking generate POSTs /api/generate and triggers a download', async () => {
    const fakeBlob = new Blob([new Uint8Array([0x50, 0x4b, 0x03, 0x04])], {
      type: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    })
    const fetchMock = vi.fn(async (url: string) => {
      const u = String(url)
      if (u.includes('/outline/async')) {
        return { ok: true, json: async () => ({ job_id: JOB_ID }) } as unknown as Response
      }
      if (u.includes(`/jobs/${JOB_ID}/result`)) {
        return {
          ok: true,
          json: async () => ({
            outline: FAKE_OK.outline,
            used_fallback: false,
            used_model: 'qwen2.5:7b-instruct',
          }),
        } as unknown as Response
      }
      if (u.includes(`/jobs/${JOB_ID}`)) {
        return {
          ok: true,
          json: async () => ({
            id: JOB_ID,
            status: 'completed',
            progress: { stage: 'done', detail: '', percent: 100 },
            error: null,
            created_at: 0,
            completed_at: 1,
          }),
        } as unknown as Response
      }
      if (u.includes('/generate')) {
        return {
          ok: true,
          blob: async () => fakeBlob,
          headers: {
            get: (k: string) => {
              if (k === 'Content-Disposition') return 'attachment; filename="Demo.pptx"'
              if (k === 'X-Render-Elapsed-Ms') return '42'
              return null
            },
          },
        } as unknown as Response
      }
      return { ok: false, status: 404, json: async () => ({}) } as unknown as Response
    }) as unknown as typeof fetch
    global.fetch = fetchMock

    const createUrl = vi
      .fn()
      .mockReturnValue('blob:fake') as unknown as typeof URL.createObjectURL
    const revokeUrl = vi.fn() as unknown as typeof URL.revokeObjectURL
    URL.createObjectURL = createUrl
    URL.revokeObjectURL = revokeUrl
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {})

    const w = mount(OutlineForm, { props: { template: 'executive-dark' } })
    await w.find('textarea').setValue('hello')
    await w.find('button.primary').trigger('click')
    await advanceAndFlush()

    const genBtn = w.find('.result-actions button.primary')
    expect((genBtn.element as HTMLButtonElement).disabled).toBe(false)
    await genBtn.trigger('click')
    vi.advanceTimersByTime(200)
    await flushPromises()

    const calls = (fetchMock as unknown as ReturnType<typeof vi.fn>).mock.calls
    const genCall = calls.find((c: unknown[]) => String(c[0]).includes('/generate'))
    expect(genCall).toBeTruthy()
    const body = JSON.parse((genCall![1] as RequestInit).body as string)
    expect(body.template).toBe('executive-dark')
    expect(body.outline.title).toBe('Demo')

    expect(createUrl).toHaveBeenCalledWith(fakeBlob)
    expect(clickSpy).toHaveBeenCalled()
    expect(w.find('.result-actions .ok').text()).toContain('Demo.pptx')

    vi.advanceTimersByTime(1)
    await flushPromises()
    expect(revokeUrl).toHaveBeenCalled()
  })

  it('M2-3: uploads an image and attaches it to the section', async () => {
    const fetchMock = vi.fn(async (url: string) => {
      const u = String(url)
      if (u.includes('/outline/async')) {
        return { ok: true, json: async () => ({ job_id: JOB_ID }) } as unknown as Response
      }
      if (u.includes(`/jobs/${JOB_ID}/result`)) {
        return {
          ok: true,
          json: async () => ({
            outline: FAKE_OK.outline,
            used_fallback: false,
            used_model: 'qwen2.5:7b-instruct',
          }),
        } as unknown as Response
      }
      if (u.includes(`/jobs/${JOB_ID}`)) {
        return {
          ok: true,
          json: async () => ({
            id: JOB_ID,
            status: 'completed',
            progress: { stage: 'done', detail: '', percent: 100 },
            error: null,
            created_at: 0,
            completed_at: 1,
          }),
        } as unknown as Response
      }
      if (u.includes('/upload')) {
        return {
          ok: true,
          json: async () => ({ file_id: 'abc.png', bytes: 42, content_type: 'image/png' }),
        } as unknown as Response
      }
      return { ok: false, status: 404, json: async () => ({}) } as unknown as Response
    }) as unknown as typeof fetch
    global.fetch = fetchMock

    const w = mount(OutlineForm, { props: { template: 'executive-dark' } })
    await w.find('textarea').setValue('hello')
    await w.find('button.primary').trigger('click')
    await advanceAndFlush()

    const fileInput = w.find('input[type="file"]')
    expect(fileInput.exists()).toBe(true)

    const fakeFile = new File([new Uint8Array([1, 2, 3])], 'shot.png', { type: 'image/png' })
    Object.defineProperty(fileInput.element, 'files', { value: [fakeFile], configurable: true })
    await fileInput.trigger('change')
    await flushPromises()

    const calls = (fetchMock as unknown as ReturnType<typeof vi.fn>).mock.calls
    const uploadCall = calls.find((c: unknown[]) => String(c[0]).includes('/upload'))
    expect(uploadCall).toBeTruthy()
    expect((uploadCall![1] as RequestInit).body).toBeInstanceOf(FormData)

    expect(w.find('.att-chip.att-image').exists()).toBe(true)
    expect(w.find('.att-chip.att-image').text()).toContain('shot.png')
  })

  it('M2-3: opens table editor, parses TSV, attaches table', async () => {
    global.fetch = mockAsyncOutlineFetch()

    const w = mount(OutlineForm, { props: { template: 'executive-dark' } })
    await w.find('textarea').setValue('hello')
    await w.find('button.primary').trigger('click')
    await advanceAndFlush()

    const addBtns = w.findAll('button.att-btn')
    const tableBtn = addBtns.find((b) => b.text().includes('添加表格'))
    expect(tableBtn).toBeTruthy()
    await tableBtn!.trigger('click')

    expect(w.find('.table-editor').exists()).toBe(true)
    await w
      .find('.table-editor textarea')
      .setValue('Q\tRev\nQ1\t10\nQ2\t20')
    await w.find('.table-editor input[type="text"]').setValue('quarterly')
    await w.find('.table-editor button.primary').trigger('click')

    expect(w.find('.table-editor').exists()).toBe(false)
    expect(w.find('.att-chip.att-table').exists()).toBe(true)
    expect(w.find('.att-chip.att-table').text()).toContain('2 列')
    expect(w.find('.att-chip.att-table').text()).toContain('2 行')
  })

  it('M3-2: AI auto-pick calls /api/classify-template and emits suggestion', async () => {
    const fetchMock = vi.fn(async (url: string) => ({
      ok: true,
      json: async () => ({
        template: 'tech-blue',
        confidence: 0.92,
        reason: 'Talks about API design and architecture.',
        used_fallback: false,
        used_model: 'qwen2.5:7b-instruct',
        elapsed_ms: 800,
      }),
    })) as unknown as typeof fetch
    global.fetch = fetchMock

    const w = mount(OutlineForm)
    await w.find('textarea').setValue('REST API design and architecture')
    const autoPick = w.findAll('button.link')[1]
    expect(autoPick.text()).toContain('AI 选模板')
    await autoPick.trigger('click')
    await flushPromises()

    const calls = (fetchMock as unknown as ReturnType<typeof vi.fn>).mock.calls
    expect(calls).toHaveLength(1)
    expect(String(calls[0][0])).toContain('/classify-template')
    const body = JSON.parse((calls[0][1] as RequestInit).body as string)
    expect(body.content).toBe('REST API design and architecture')

    expect(w.find('[data-testid="classify-pill"]').exists()).toBe(true)
    expect(w.find('[data-testid="classify-pill"]').text()).toContain('tech-blue')
    expect(w.find('[data-testid="classify-pill"]').text()).toContain('92%')
    expect(w.emitted('template-suggested')?.[0]).toEqual(['tech-blue'])
  })

  it('M3-2: AI auto-pick shows fallback badge when used_fallback=true', async () => {
    global.fetch = vi.fn(async () => ({
      ok: true,
      json: async () => ({
        template: 'minimal-light',
        confidence: 0.2,
        reason: 'No domain keywords matched.',
        used_fallback: true,
        used_model: null,
        elapsed_ms: 5,
      }),
    })) as unknown as typeof fetch

    const w = mount(OutlineForm)
    await w.find('textarea').setValue('hello')
    await w.findAll('button.link')[1].trigger('click')
    await flushPromises()

    expect(w.find('.classify-pill .badge-fallback').exists()).toBe(true)
  })
})

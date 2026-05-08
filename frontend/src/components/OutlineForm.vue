<script setup lang="ts">
import { computed, ref } from 'vue'
import {
  createOutline,
  generatePptx,
  parseTableInput,
  triggerBlobDownload,
  uploadImage,
  type OutlineResponse,
  type OutlineSection,
} from '../api/client'

const props = withDefaults(
  defineProps<{
    /** Currently selected template name from the picker. */
    template?: string | null
  }>(),
  { template: null },
)

const content = ref('')
const language = ref<'auto' | 'zh' | 'en'>('auto')
const sourceType = ref<'text' | 'markdown'>('text')

const loading = ref(false)
const error = ref<string | null>(null)
const result = ref<OutlineResponse | null>(null)

const generating = ref(false)
const genError = ref<string | null>(null)
const genStatus = ref<string | null>(null)

const startedAt = ref<number | null>(null)
const tickMs = ref(0)
let tickHandle: ReturnType<typeof setInterval> | null = null

const charCount = computed(() => content.value.length)
const overLimit = computed(() => charCount.value > 20_000)
const canSubmit = computed(
  () => !loading.value && content.value.trim().length > 0 && !overLimit.value,
)

const elapsedDisplay = computed(() => {
  if (loading.value && startedAt.value !== null) {
    return `${(tickMs.value / 1000).toFixed(1)} s`
  }
  if (result.value) {
    return `${(result.value.elapsed_ms / 1000).toFixed(2)} s`
  }
  return ''
})

function startTicker() {
  startedAt.value = performance.now()
  tickMs.value = 0
  tickHandle = setInterval(() => {
    if (startedAt.value !== null) tickMs.value = performance.now() - startedAt.value
  }, 100)
}

function stopTicker() {
  if (tickHandle !== null) {
    clearInterval(tickHandle)
    tickHandle = null
  }
  startedAt.value = null
}

async function submit() {
  if (!canSubmit.value) return
  loading.value = true
  error.value = null
  result.value = null
  startTicker()
  try {
    const r = await createOutline({
      content: content.value,
      source_type: sourceType.value,
      language: language.value,
    })
    result.value = r
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    loading.value = false
    stopTicker()
  }
}

const SAMPLE = `# HotPulse 发布会

我们的产品 HotPulse 是一个面向中小团队的实时业务监控平台。它支持多数据源接入、自定义看板、智能告警和移动端推送。

本次发布会将面向投资人和早期客户，介绍产品定位、核心能力、技术架构和未来路线图。`

function loadSample() {
  content.value = SAMPLE
}

const canGenerate = computed(
  () => !!result.value && !!props.template && !generating.value,
)

async function generate() {
  if (!canGenerate.value || !result.value || !props.template) return
  generating.value = true
  genError.value = null
  genStatus.value = null
  try {
    const r = await generatePptx({
      outline: result.value.outline,
      template: props.template,
    })
    triggerBlobDownload(r.blob, r.filename)
    genStatus.value = `已下载 ${r.filename} · 模板 ${r.template} · ${r.elapsedMs} ms`
  } catch (e: unknown) {
    genError.value = e instanceof Error ? e.message : String(e)
  } finally {
    generating.value = false
  }
}

// ---- M2-3: per-section image / table attachments --------------------------

const attachError = ref<string | null>(null)
const attachBusyIndex = ref<number | null>(null)
const tableEditingIndex = ref<number | null>(null)
const tableInput = ref('')
const tableCaption = ref('')

function _section(i: number): OutlineSection | null {
  return result.value?.outline.sections[i] ?? null
}

async function pickImageFor(i: number, ev: Event) {
  attachError.value = null
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  // Reset so the same file can be re-picked after an error.
  input.value = ''
  if (!file) return
  const s = _section(i)
  if (!s) return
  attachBusyIndex.value = i
  try {
    const up = await uploadImage(file)
    s.image = { file_id: up.file_id, caption: file.name }
    s.layout_hint = 'content-image'
  } catch (e: unknown) {
    attachError.value = e instanceof Error ? e.message : String(e)
  } finally {
    attachBusyIndex.value = null
  }
}

function removeImage(i: number) {
  const s = _section(i)
  if (!s) return
  s.image = null
  if (s.layout_hint === 'content-image') s.layout_hint = null
}

function openTableEditor(i: number) {
  attachError.value = null
  const s = _section(i)
  if (!s) return
  tableEditingIndex.value = i
  if (s.table) {
    tableInput.value = [s.table.headers, ...s.table.rows]
      .map((r) => r.join('\t'))
      .join('\n')
    tableCaption.value = s.table.caption ?? ''
  } else {
    tableInput.value = ''
    tableCaption.value = ''
  }
}

function cancelTableEditor() {
  tableEditingIndex.value = null
  tableInput.value = ''
  tableCaption.value = ''
}

function saveTable() {
  const i = tableEditingIndex.value
  if (i === null) return
  const s = _section(i)
  if (!s) return
  const parsed = parseTableInput(tableInput.value, tableCaption.value.trim() || null)
  if (parsed === null) {
    attachError.value = '表格内容为空'
    return
  }
  s.table = parsed
  s.layout_hint = 'content-table'
  cancelTableEditor()
}

function removeTable(i: number) {
  const s = _section(i)
  if (!s) return
  s.table = null
  if (s.layout_hint === 'content-table') s.layout_hint = null
}
</script>

<template>
  <section class="outline-form">
    <div class="form-header">
      <h2>大纲生成</h2>
      <button type="button" class="link" @click="loadSample" :disabled="loading">
        载入示例
      </button>
    </div>

    <label class="field">
      <span class="label-text">内容（粘贴文字 / Markdown，最长 20 000 字）</span>
      <textarea
        v-model="content"
        rows="10"
        :disabled="loading"
        placeholder="把要讲的内容粘进来，可以是一段段落、Markdown 标题，或带列表的笔记…"
      />
      <span class="char-count" :class="{ over: overLimit }">
        {{ charCount.toLocaleString() }} / 20,000
      </span>
    </label>

    <div class="row">
      <label class="field-inline">
        <span>来源</span>
        <select v-model="sourceType" :disabled="loading">
          <option value="text">纯文本</option>
          <option value="markdown">Markdown</option>
        </select>
      </label>

      <label class="field-inline">
        <span>语言</span>
        <select v-model="language" :disabled="loading">
          <option value="auto">自动检测</option>
          <option value="zh">中文</option>
          <option value="en">English</option>
        </select>
      </label>

      <button class="primary" :disabled="!canSubmit" @click="submit">
        <span v-if="!loading">生成大纲</span>
        <span v-else>生成中… {{ elapsedDisplay }}</span>
      </button>
    </div>

    <div v-if="error" class="err" role="alert">{{ error }}</div>

    <article v-if="result" class="result">
      <header class="result-meta">
        <span class="badge" :class="{ fallback: result.used_fallback }">
          {{ result.used_fallback ? 'Fallback (LLM 不可用)' : 'LLM 生成' }}
        </span>
        <span v-if="result.used_model" class="meta">model: {{ result.used_model }}</span>
        <span class="meta">耗时: {{ elapsedDisplay }}</span>
        <span class="meta">语言: {{ result.outline.language }}</span>
        <span class="meta">{{ result.outline.sections.length }} 段</span>
      </header>

      <h3 class="title">{{ result.outline.title }}</h3>
      <p v-if="result.outline.subtitle" class="subtitle">{{ result.outline.subtitle }}</p>

      <ol class="sections">
        <li v-for="(s, i) in result.outline.sections" :key="i" class="section">
          <h4>{{ s.heading }}</h4>
          <ul v-if="s.bullets.length" class="bullets">
            <li
              v-for="(b, j) in s.bullets"
              :key="j"
              :class="{ emphasis: b.emphasis }"
            >
              {{ b.text }}
              <em v-if="b.note" class="bullet-note">— {{ b.note }}</em>
            </li>
          </ul>
          <p v-if="s.speaker_notes" class="notes">备注：{{ s.speaker_notes }}</p>

          <div class="attachments">
            <div v-if="s.image" class="att-chip att-image">
              <span>📎 图片：{{ s.image.caption || s.image.file_id }}</span>
              <button type="button" class="link-mini" @click="removeImage(i)">移除</button>
            </div>
            <div v-if="s.table" class="att-chip att-table">
              <span>📊 表格：{{ s.table.headers.length }} 列 × {{ s.table.rows.length }} 行</span>
              <button type="button" class="link-mini" @click="openTableEditor(i)">编辑</button>
              <button type="button" class="link-mini" @click="removeTable(i)">移除</button>
            </div>
            <div class="att-actions">
              <label class="att-btn">
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/gif,image/webp"
                  hidden
                  :disabled="attachBusyIndex === i"
                  @change="(e) => pickImageFor(i, e)"
                />
                <span v-if="attachBusyIndex === i">上传中…</span>
                <span v-else>{{ s.image ? '替换图片' : '+ 添加图片' }}</span>
              </label>
              <button
                v-if="!s.table"
                type="button"
                class="att-btn"
                @click="openTableEditor(i)"
              >+ 添加表格</button>
            </div>
          </div>
        </li>
      </ol>

      <div v-if="attachError" class="err" role="alert">{{ attachError }}</div>

      <div v-if="tableEditingIndex !== null" class="table-editor" role="dialog">
        <h4>编辑表格 · 第 {{ tableEditingIndex + 1 }} 段</h4>
        <p class="hint">每行一条记录，列之间用 Tab 或逗号分隔；第一行作为表头。</p>
        <textarea v-model="tableInput" rows="8" placeholder="季度&#9;收入&#10;Q1&#9;100&#10;Q2&#9;120" />
        <input v-model="tableCaption" type="text" placeholder="表格标题（可选）" />
        <div class="row">
          <button type="button" class="primary" @click="saveTable">保存表格</button>
          <button type="button" class="link" @click="cancelTableEditor">取消</button>
        </div>
      </div>

      <footer class="result-actions">
        <button
          type="button"
          class="primary"
          :disabled="!canGenerate"
          @click="generate"
          :title="!props.template ? '请先在上方选择一个模板' : ''"
        >
          <span v-if="!generating">生成 PPT 并下载</span>
          <span v-else>正在生成…</span>
        </button>
        <span v-if="!props.template" class="hint">请先选择模板</span>
        <span v-if="genStatus" class="ok" role="status">{{ genStatus }}</span>
        <span v-if="genError" class="err" role="alert">{{ genError }}</span>
      </footer>
    </article>
  </section>
</template>

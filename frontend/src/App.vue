<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { healthz, listTemplates, type TemplateInfo } from './api/client'
import OutlineForm from './components/OutlineForm.vue'
import TemplatePicker from './components/TemplatePicker.vue'

const templates = ref<TemplateInfo[]>([])
const selected = ref<string | null>(null)
const loadErr = ref<string | null>(null)
const health = ref<{ ok: boolean; version: string; model: string } | null>(null)

onMounted(async () => {
  try {
    const [tmpls, hz] = await Promise.all([listTemplates(), healthz()])
    templates.value = tmpls
    health.value = hz
    if (tmpls.length > 0) selected.value = tmpls[0].name
  } catch (e: unknown) {
    loadErr.value = e instanceof Error ? e.message : String(e)
  }
})
</script>

<template>
  <main>
    <header class="page-header">
      <h1>ai-ppt-maker</h1>
      <p class="lead">
        把粘贴的文字 / Markdown 一键变成「风格高大上、可下载二次编辑」的 .pptx 宣讲稿。
        本地部署，走本地 Ollama，不外发资料。
      </p>
      <p v-if="health" class="health">
        Backend ✓ <code>v{{ health.version }}</code> · model <code>{{ health.model }}</code>
      </p>
    </header>

    <section class="block">
      <h2>选择模板</h2>
      <p v-if="loadErr" class="err">{{ loadErr }}</p>
      <p v-else-if="templates.length === 0" class="empty">加载模板中…</p>
      <TemplatePicker
        v-else
        :templates="templates"
        :selected="selected"
        @select="(name: string) => (selected = name)"
      />
    </section>

    <OutlineForm class="block" :template="selected" />

    <footer>
      <span>© ai-ppt-maker · M2 outline preview</span>
    </footer>
  </main>
</template>

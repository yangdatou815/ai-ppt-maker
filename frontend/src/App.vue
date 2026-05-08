<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { healthz, listTemplates, type TemplateInfo } from './api/client'
import DebugDrawer from './components/DebugDrawer.vue'
import OutlineForm from './components/OutlineForm.vue'
import RoadmapView from './components/RoadmapView.vue'
import TemplatePicker from './components/TemplatePicker.vue'

const templates = ref<TemplateInfo[]>([])
const selected = ref<string | null>(null)
const loadErr = ref<string | null>(null)
const health = ref<{ ok: boolean; version: string; model: string } | null>(null)
const view = ref<'maker' | 'roadmap'>('maker')

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
  <DebugDrawer />
  <main>
    <header class="page-header">
      <div class="topbar">
        <h1>ai-ppt-maker</h1>
        <nav class="viewnav">
          <button type="button" :class="{ active: view === 'maker' }"
                  @click="view = 'maker'">Maker</button>
          <button type="button" :class="{ active: view === 'roadmap' }"
                  @click="view = 'roadmap'">Roadmap</button>
        </nav>
      </div>
      <p v-if="view === 'maker'" class="lead">
        把粘贴的文字 / Markdown 一键变成「风格高大上、可下载二次编辑」的 .pptx 宣讲稿。
        本地部署，走本地 Ollama，不外发资料。
      </p>
      <p v-if="health" class="health">
        Backend ✓ <code>v{{ health.version }}</code> · model <code>{{ health.model }}</code>
      </p>
    </header>

    <template v-if="view === 'maker'">
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
    </template>

    <RoadmapView v-else />

    <footer>
      <span>© ai-ppt-maker · M2 outline preview</span>
    </footer>
  </main>
</template>

<style scoped>
.topbar {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
}
.viewnav {
  display: flex;
  gap: 0;
  font-family: ui-monospace, 'SF Mono', Menlo, monospace;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
}
.viewnav button {
  background: none;
  border: 1px solid #111;
  border-right: none;
  padding: 6px 14px;
  cursor: pointer;
  color: #111;
  font: inherit;
  text-transform: inherit;
  letter-spacing: inherit;
}
.viewnav button:last-child { border-right: 1px solid #111; }
.viewnav button.active { background: #111; color: #f6f4ee; }
.viewnav button:not(.active):hover { background: rgba(0,0,0,0.05); }
</style>


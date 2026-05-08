<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { getRoadmap, type RoadmapDoc, type RoadmapPhase } from '../api/client'

const doc = ref<RoadmapDoc | null>(null)
const err = ref<string | null>(null)
// All collapsed = false (i.e. expanded) by default. Map keyed by phase.id.
const collapsed = ref<Record<string, boolean>>({})

onMounted(async () => {
  try {
    doc.value = await getRoadmap()
  } catch (e: unknown) {
    err.value = e instanceof Error ? e.message : String(e)
  }
})

function toggle(phase: RoadmapPhase) {
  collapsed.value[phase.id] = !collapsed.value[phase.id]
}

function statusGlyph(s: string): string {
  if (s === 'done') return '●'
  if (s === 'in-progress') return '◐'
  return '○'
}

function statusLabel(s: string): string {
  if (s === 'done') return '已完成'
  if (s === 'in-progress') return '进行中'
  return '计划中'
}
</script>

<template>
  <div class="roadmap-view">
    <p v-if="err" class="err">加载失败：{{ err }}</p>
    <p v-else-if="!doc" class="empty">加载路线图中…</p>

    <template v-else>
      <header class="rm-header">
        <h2>项目路线图</h2>
        <p class="rm-sub">
          来源：<code>backend/roadmap.yaml</code> · 共
          <strong>{{ doc.stats.total }}</strong> 项 ·
          已完成 <strong>{{ doc.stats.done }}</strong>
          ({{ doc.stats.done_pct }}%) ·
          进行中 <strong>{{ doc.stats.in_progress }}</strong> ·
          计划 <strong>{{ doc.stats.planned }}</strong>
        </p>

        <!-- Stacked progress bar -->
        <div class="rm-bar" role="progressbar" :aria-valuenow="doc.stats.done_pct"
             aria-valuemin="0" aria-valuemax="100">
          <div class="rm-bar-done"
               :style="{ width: (doc.stats.done / doc.stats.total * 100) + '%' }" />
          <div class="rm-bar-progress"
               :style="{ width: (doc.stats.in_progress / doc.stats.total * 100) + '%' }" />
        </div>
      </header>

      <ul class="rm-phases">
        <li v-for="phase in doc.phases" :key="phase.id" class="rm-phase">
          <button class="rm-phase-head" type="button" @click="toggle(phase)">
            <span class="rm-chevron">{{ collapsed[phase.id] ? '▸' : '▾' }}</span>
            <span class="rm-phase-id">{{ phase.id }}</span>
            <span class="rm-phase-name">{{ phase.name }}</span>
            <span v-if="phase.summary" class="rm-phase-summary">— {{ phase.summary }}</span>
          </button>

          <ul v-if="!collapsed[phase.id]" class="rm-milestones">
            <li v-for="ms in phase.milestones" :key="ms.id" class="rm-milestone">
              <div class="rm-ms-head">
                <span class="rm-ms-id">{{ ms.id }}</span>
                <span class="rm-ms-name">{{ ms.name }}</span>
                <span v-if="ms.summary" class="rm-ms-summary">— {{ ms.summary }}</span>
              </div>
              <ul class="rm-items">
                <li v-for="(item, i) in ms.items" :key="i" class="rm-item"
                    :class="`s-${item.status}`">
                  <span class="rm-glyph" :title="statusLabel(item.status)">
                    {{ statusGlyph(item.status) }}
                  </span>
                  <span class="rm-item-name">{{ item.name }}</span>
                  <span class="rm-item-tag">{{ statusLabel(item.status) }}</span>
                </li>
              </ul>
            </li>
          </ul>
        </li>
      </ul>
    </template>
  </div>
</template>

<style scoped>
.roadmap-view {
  font-family: 'Inter', system-ui, sans-serif;
  color: #111;
  max-width: 920px;
  margin: 0 auto;
  padding: 32px 0;
}

.err { color: #b00020; }
.empty { color: #888; font-style: italic; }

.rm-header {
  border-bottom: 1px solid #111;
  padding-bottom: 16px;
  margin-bottom: 24px;
}
.rm-header h2 {
  font-family: 'Iowan Old Style', 'Baskerville', 'Times New Roman', Georgia, serif;
  font-style: italic;
  font-size: 36px;
  font-weight: 400;
  margin: 0 0 8px;
  letter-spacing: -0.02em;
}
.rm-sub {
  font-family: ui-monospace, 'SF Mono', Menlo, monospace;
  font-size: 12px;
  color: #555;
  letter-spacing: 0.04em;
  margin: 0 0 16px;
}
.rm-sub strong { color: #111; font-weight: 600; }
.rm-sub code { background: rgba(0,0,0,0.05); padding: 1px 4px; }

.rm-bar {
  display: flex;
  height: 6px;
  background: #fdecec;
  width: 100%;
}
.rm-bar-done { background: #1b5e20; }
.rm-bar-progress { background: #b06000; }

.rm-phases { list-style: none; padding: 0; margin: 0; }
.rm-phase { margin-bottom: 24px; }

.rm-phase-head {
  display: flex;
  align-items: baseline;
  gap: 12px;
  width: 100%;
  background: none;
  border: none;
  border-bottom: 1px solid #ddd;
  padding: 8px 0;
  cursor: pointer;
  text-align: left;
  font: inherit;
  color: inherit;
}
.rm-phase-head:hover { background: rgba(0,0,0,0.02); }
.rm-chevron { font-family: ui-monospace, monospace; color: #888; width: 14px; }
.rm-phase-id {
  font-family: ui-monospace, monospace;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #888;
  min-width: 92px;
}
.rm-phase-name {
  font-family: 'Iowan Old Style', 'Baskerville', Georgia, serif;
  font-style: italic;
  font-size: 22px;
}
.rm-phase-summary { color: #666; font-size: 14px; }

.rm-milestones { list-style: none; padding: 8px 0 0 32px; margin: 0; }
.rm-milestone { margin: 16px 0; }

.rm-ms-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 4px 0;
  border-bottom: 1px dashed #d8d4c8;
}
.rm-ms-id {
  font-family: ui-monospace, monospace;
  font-size: 11px;
  letter-spacing: 0.1em;
  color: #555;
  min-width: 56px;
}
.rm-ms-name { font-weight: 600; font-size: 15px; }
.rm-ms-summary { color: #888; font-size: 13px; }

.rm-items { list-style: none; padding: 6px 0 0 24px; margin: 0; }
.rm-item {
  display: flex;
  align-items: baseline;
  gap: 12px;
  padding: 4px 0;
  font-size: 14px;
  line-height: 1.5;
}
.rm-glyph {
  font-family: ui-monospace, monospace;
  width: 16px;
  display: inline-block;
  text-align: center;
}
.rm-item-name { flex: 1; }
.rm-item-tag {
  font-family: ui-monospace, monospace;
  font-size: 10px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #888;
}

.rm-item.s-done {
  background: #e6f4ea;
  border-left: 3px solid #1b5e20;
  padding-left: 8px;
}
.rm-item.s-done .rm-glyph,
.rm-item.s-done .rm-item-name,
.rm-item.s-done .rm-item-tag { color: #1b5e20; }

.rm-item.s-in-progress {
  background: #fff4d6;
  border-left: 3px solid #b06000;
  padding-left: 8px;
}
.rm-item.s-in-progress .rm-glyph,
.rm-item.s-in-progress .rm-item-name,
.rm-item.s-in-progress .rm-item-tag { color: #8a4a00; }
.rm-item.s-in-progress .rm-item-name { font-weight: 500; }

.rm-item.s-planned {
  background: #fdecec;
  border-left: 3px solid #c62828;
  padding-left: 8px;
}
.rm-item.s-planned .rm-glyph,
.rm-item.s-planned .rm-item-name,
.rm-item.s-planned .rm-item-tag { color: #b71c1c; }
</style>

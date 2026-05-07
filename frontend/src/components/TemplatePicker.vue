<script setup lang="ts">
import type { TemplateInfo } from '../api/client'

defineProps<{
  templates: TemplateInfo[]
  selected: string | null
}>()

const emit = defineEmits<{ (e: 'select', name: string): void }>()

const SWATCH_KEYS = ['primary', 'primary-2', 'accent', 'background', 'neutral']

function swatches(theme: Record<string, string>): string[] {
  const seen = new Set<string>()
  const out: string[] = []
  for (const k of SWATCH_KEYS) {
    const v = theme[k]
    if (v && !seen.has(v)) {
      seen.add(v)
      out.push(v)
    }
    if (out.length >= 3) break
  }
  return out
}
</script>

<template>
  <div class="template-grid">
    <article
      v-for="t in templates"
      :key="t.name"
      class="tcard"
      :class="{ selected: selected === t.name }"
      @click="emit('select', t.name)"
    >
      <div class="swatches">
        <span
          v-for="c in swatches(t.theme)"
          :key="c"
          class="swatch"
          :style="{ background: c }"
        />
      </div>
      <h3>{{ t.display_name }}</h3>
      <p>{{ t.description }}</p>
      <div class="tags">
        <span v-for="tag in t.tags" :key="tag" class="tag">{{ tag }}</span>
      </div>
    </article>
  </div>
</template>

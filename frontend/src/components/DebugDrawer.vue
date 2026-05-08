<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  getDebugState,
  openLogStream,
  setDebugState,
  type LogLine,
} from '../api/client'

/**
 * Floating debug toggle + live log drawer.
 *
 * - Top-right corner of the page renders a small switch labelled DEBUG.
 *   Toggling it POSTs /api/debug to flip the backend log level between
 *   the configured baseline (default ERROR) and DEBUG.
 * - When ON, opens an EventSource on /api/debug/logs/stream and renders
 *   incoming records in a fixed-bottom drawer (color-coded by level).
 * - State syncs from /api/debug on mount so a page reload reflects what
 *   the backend currently is — debug stays on across F5.
 */

const enabled = ref(false)
const lines = ref<LogLine[]>([])
const drawerOpen = ref(false)
const busy = ref(false)
const error = ref<string | null>(null)
const filter = ref<string>('')

let es: EventSource | null = null
const MAX_LINES = 500

function appendLine(l: LogLine) {
  lines.value.push(l)
  if (lines.value.length > MAX_LINES) {
    lines.value.splice(0, lines.value.length - MAX_LINES)
  }
}

function openStream() {
  if (es) return
  es = openLogStream(appendLine)
  es.onerror = () => {
    // Browser will auto-reconnect; nothing actionable here.
  }
}

function closeStream() {
  if (es) {
    es.close()
    es = null
  }
}

async function toggle() {
  if (busy.value) return
  busy.value = true
  error.value = null
  try {
    const next = !enabled.value
    const s = await setDebugState(next)
    enabled.value = s.enabled
    if (s.enabled) {
      drawerOpen.value = true
      openStream()
    } else {
      closeStream()
      lines.value = []
    }
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  } finally {
    busy.value = false
  }
}

onMounted(async () => {
  try {
    const s = await getDebugState()
    enabled.value = s.enabled
    if (s.enabled) {
      drawerOpen.value = true
      openStream()
    }
  } catch (e: unknown) {
    error.value = e instanceof Error ? e.message : String(e)
  }
})

onBeforeUnmount(() => closeStream())

// Auto-scroll to the bottom on each new line, but only if the user is
// already pinned at the bottom (don't yank them up when they're scrolling
// back to read older lines).
const scroller = ref<HTMLElement | null>(null)
watch(
  () => lines.value.length,
  () => {
    const el = scroller.value
    if (!el) return
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 32
    if (atBottom) {
      requestAnimationFrame(() => {
        el.scrollTop = el.scrollHeight
      })
    }
  },
)

function fmtTime(ts: number): string {
  const d = new Date(ts * 1000)
  const pad = (n: number) => String(n).padStart(2, '0')
  return (
    pad(d.getHours()) +
    ':' +
    pad(d.getMinutes()) +
    ':' +
    pad(d.getSeconds()) +
    '.' +
    String(d.getMilliseconds()).padStart(3, '0')
  )
}

function levelClass(lv: string): string {
  return 'lvl lvl-' + lv.toLowerCase()
}
</script>

<template>
  <div class="debug-toggle">
    <label class="dswitch" :class="{ on: enabled }" :title="enabled ? '调试模式开启 — 性能稍差' : '关闭：仅 ERROR 日志'">
      <input
        type="checkbox"
        :checked="enabled"
        :disabled="busy"
        @change="toggle"
        aria-label="Toggle debug mode"
      />
      <span class="track"><span class="thumb" /></span>
      <span class="lbl">DEBUG</span>
    </label>
    <button
      v-if="enabled"
      type="button"
      class="drawer-tab"
      @click="drawerOpen = !drawerOpen"
    >
      {{ drawerOpen ? '收起日志' : `日志 (${lines.length})` }}
    </button>
    <span v-if="error" class="derr">{{ error }}</span>
  </div>

  <transition name="drawer">
    <aside v-if="enabled && drawerOpen" class="debug-drawer" role="log">
      <header class="ddh">
        <span class="ddh-title">/ live log · DEBUG</span>
        <input
          v-model="filter"
          type="text"
          placeholder="filter substring…"
          class="dfilter"
        />
        <button type="button" class="link-mini" @click="lines = []">clear</button>
        <button type="button" class="link-mini" @click="drawerOpen = false">×</button>
      </header>
      <div ref="scroller" class="ddbody">
        <p v-if="lines.length === 0" class="dempty">无日志。触发一个请求看看。</p>
        <template v-else>
          <p
            v-for="(l, i) in lines.filter((x) =>
              !filter.trim() || (x.msg + ' ' + x.name).toLowerCase().includes(filter.trim().toLowerCase()),
            )"
            :key="i"
            class="dline"
          >
            <span class="dts">{{ fmtTime(l.ts) }}</span>
            <span :class="levelClass(l.level)">{{ l.level }}</span>
            <span class="dname">{{ l.name }}</span>
            <span class="dmsg">{{ l.msg }}</span>
          </p>
        </template>
      </div>
    </aside>
  </transition>
</template>

<style scoped>
.debug-toggle {
  position: fixed;
  top: 16px;
  right: 24px;
  z-index: 100;
  display: flex;
  align-items: center;
  gap: 12px;
  font-family: var(--mono);
  font-size: 11px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--ink-mute);
}

.dswitch {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  user-select: none;
}
.dswitch input { position: absolute; opacity: 0; pointer-events: none; }
.track {
  width: 32px;
  height: 16px;
  border: 1px solid var(--hairline-strong);
  position: relative;
  background: var(--paper-2);
  transition: background 0.15s ease, border-color 0.15s ease;
}
.thumb {
  position: absolute;
  top: 1px;
  left: 1px;
  width: 12px;
  height: 12px;
  background: var(--ink-mute);
  transition: transform 0.15s ease, background 0.15s ease;
}
.dswitch.on .track { background: var(--ink); border-color: var(--ink); }
.dswitch.on .thumb { transform: translateX(16px); background: var(--paper); }
.dswitch.on .lbl { color: var(--ink); }

.drawer-tab {
  background: transparent;
  border: 1px solid var(--hairline);
  color: var(--ink);
  font-family: var(--mono);
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 6px 12px;
  cursor: pointer;
}
.drawer-tab:hover { background: var(--ink); color: var(--paper); border-color: var(--ink); }

.derr { color: var(--signal-err); }

.debug-drawer {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  height: 280px;
  background: #0d0d0d;
  color: #e6e6e6;
  border-top: 1px solid var(--ink);
  z-index: 99;
  display: flex;
  flex-direction: column;
  font-family: var(--mono);
  font-size: 12px;
}
.ddh {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  background: #161616;
}
.ddh-title {
  color: #b08646;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  font-size: 10px;
}
.dfilter {
  flex: 0 1 240px;
  background: #0d0d0d;
  color: #e6e6e6;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 0;
  padding: 4px 8px;
  font-family: var(--mono);
  font-size: 11px;
}
.dfilter:focus { outline: none; border-color: #b08646; }
.ddh .link-mini { color: rgba(255, 255, 255, 0.6); border-bottom-color: rgba(255, 255, 255, 0.2); margin-left: auto; }
.ddh .link-mini:last-of-type { margin-left: 8px; }
.ddh .link-mini:hover { color: #fff; border-bottom-color: #fff; }

.ddbody {
  flex: 1 1 auto;
  overflow-y: auto;
  padding: 8px 16px 16px;
  line-height: 1.45;
}
.dempty { color: rgba(255, 255, 255, 0.4); padding: 16px 0; }
.dline {
  margin: 0;
  padding: 1px 0;
  display: grid;
  grid-template-columns: 96px 64px 220px 1fr;
  gap: 12px;
  white-space: pre-wrap;
  word-break: break-all;
}
.dts { color: rgba(255, 255, 255, 0.5); }
.dname { color: rgba(255, 255, 255, 0.6); }
.dmsg { color: #e6e6e6; }
.lvl { font-weight: 600; }
.lvl-debug { color: #7aa6c5; }
.lvl-info { color: #6fbf6f; }
.lvl-warning { color: #d8a13a; }
.lvl-error { color: #e25848; }
.lvl-critical { color: #ff3b3b; }

.drawer-enter-active, .drawer-leave-active { transition: transform 0.2s ease; }
.drawer-enter-from, .drawer-leave-to { transform: translateY(100%); }
</style>

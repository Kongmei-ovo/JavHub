<template>
  <div class="ow" v-if="players.length">
    <button
      class="btn stream-download-btn ow-trigger"
      type="button"
      :title="label"
      @click.stop="toggle"
      :aria-expanded="open"
    >
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="18" height="18">
        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
        <polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/>
      </svg>
      <span>{{ label }}</span>
      <svg class="ow-caret" :class="{ up: open }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
        <polyline points="6 9 12 15 18 9"/>
      </svg>
    </button>
    <div v-if="open" class="ow-pop" @click.stop>
      <a
        v-for="p in players"
        :key="p.name"
        class="ow-item"
        :href="hrefFor(p)"
        target="_blank"
        rel="noopener"
        @click="onPick"
      >{{ p.name }}</a>
    </div>
  </div>
</template>

<script>
import { convertURL, playersForPlatform } from './externalPlayers.js'

export default {
  name: 'OpenWithMenu',
  props: {
    url: { type: String, default: '' }, // 直链(可相对,内部转绝对);走后端 302
    name: { type: String, default: '' },
    label: { type: String, default: '外部播放器' },
  },
  emits: ['launch'],
  data() {
    return { open: false }
  },
  computed: {
    players() {
      return this.url ? playersForPlatform() : []
    },
    absoluteUrl() {
      if (!this.url) return ''
      try {
        return new URL(this.url, window.location.origin).href
      } catch {
        return this.url
      }
    },
  },
  methods: {
    hrefFor(player) {
      return convertURL(player.scheme, {
        rawUrl: this.absoluteUrl,
        dUrl: this.absoluteUrl,
        name: this.name || '',
      })
    },
    toggle() {
      this.open = !this.open
      if (this.open) document.addEventListener('click', this.onAway)
      else document.removeEventListener('click', this.onAway)
    },
    onPick() {
      this.open = false
      document.removeEventListener('click', this.onAway)
      // 通知父级关掉网页播放器,否则外部播放器起来后两路声音一起响。
      // 用 setTimeout 让 <a> 的 scheme 唤起(默认跳转)先发生,再触发可能销毁本组件的关闭。
      setTimeout(() => this.$emit('launch'), 0)
    },
    onAway() {
      this.open = false
      document.removeEventListener('click', this.onAway)
    },
  },
  beforeUnmount() {
    document.removeEventListener('click', this.onAway)
  },
}
</script>

<style scoped>
.ow { position: relative; display: inline-flex; }
.ow-trigger { display: inline-flex; align-items: center; gap: 6px; }
.ow-caret { transition: transform var(--motion-fast); opacity: 0.7; }
.ow-caret.up { transform: rotate(180deg); }
.ow-pop {
  position: absolute;
  bottom: calc(100% + 8px);
  left: 0;
  min-width: 168px;
  display: flex;
  flex-direction: column;
  padding: var(--space-1);
  gap: 2px;
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-sheet);
  border: var(--stroke-pro) solid var(--glass-control-border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sheet);
  backdrop-filter: blur(var(--glass-blur-sheet)) saturate(var(--glass-saturate-surface));
  -webkit-backdrop-filter: blur(var(--glass-blur-sheet)) saturate(var(--glass-saturate-surface));
  z-index: var(--z-modal);
  animation: owIn 0.18s var(--ease-pro);
}
@keyframes owIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}
.ow-item {
  display: block;
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-control);
  color: var(--text-primary);
  font-size: var(--type-caption);
  text-decoration: none;
  white-space: nowrap;
  transition: transform var(--motion-standard), opacity var(--motion-fast);
}
.ow-item:hover { background: var(--surface-control-hover); }
.ow-item:active { transform: scale(0.98); }
</style>

<template>
  <div
    v-if="visible"
    class="vp-overlay"
    @click.self="$emit('close')"
    @keydown.esc="$emit('close')"
    tabindex="0"
  >
    <div class="vp-container">
      <button class="vp-close" type="button" @click="$emit('close')">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="20" height="20">
          <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
        </svg>
      </button>
      <div class="vp-player-wrap">
        <video ref="streamVideoEl" class="vp-video" controls autoplay playsinline></video>
      </div>
      <div class="vp-info">
        <span class="vp-title">{{ title }}</span>
      </div>
      <StreamSourcePicker
        v-if="sources.length || !scanDone"
        :sources="sources"
        :current="currentSource"
        :scan-done="scanDone"
        @switch="(s) => $emit('switch-source', s)"
      />
    </div>
  </div>
</template>

<script>
import StreamSourcePicker from './StreamSourcePicker.vue'

export default {
  name: 'HlsPlayerOverlay',
  components: { StreamSourcePicker },
  props: {
    visible: { type: Boolean, default: false },
    title: { type: String, default: '' },
    sources: { type: Array, default: () => [] },
    currentSource: { type: String, default: '' },
    scanDone: { type: Boolean, default: false },
  },
  emits: ['close', 'switch-source'],
  methods: {
    mediaElement() {
      return this.$refs.streamVideoEl
    },
  },
}
</script>

<style scoped>
.vp-overlay {
  --vp-control-bg: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  --vp-control-bg-hover: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  --vp-control-border: var(--glass-control-border);
  --vp-control-border-hover: var(--glass-control-border-hover);
  --vp-control-shadow: var(--glass-control-shadow);
  --vp-control-shadow-hover: var(--glass-control-shadow-hover);
  --vp-sheet-bg: var(--material-glass-sheet);
  --vp-sheet-border: var(--glass-control-border);
  --vp-player-blackout: var(--media-blackout);
  --vp-player-bg: var(--vp-player-blackout);
  position: fixed;
  inset: 0;
  z-index: var(--z-modal);
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface-scrim, var(--scrim));
  backdrop-filter: blur(var(--glass-blur-sheet)) saturate(var(--glass-saturate-surface));
  -webkit-backdrop-filter: blur(var(--glass-blur-sheet)) saturate(var(--glass-saturate-surface));
  animation: fadeIn 0.4s var(--ease-pro);
}
.vp-container { position: relative; width: 90vw; max-width: 1080px; display: flex; flex-direction: column; gap: 18px; }
.vp-close {
  position: absolute;
  top: -58px;
  right: 0;
  background: var(--vp-control-bg);
  border: var(--stroke-pro) solid var(--vp-control-border);
  border-radius: 50%;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--text-secondary);
  box-shadow: var(--vp-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  cursor: pointer;
  transition: transform var(--motion-standard), opacity var(--motion-fast);
}
.vp-close:hover {
  background: var(--vp-control-bg-hover);
  border-color: var(--vp-control-border-hover);
  box-shadow: var(--vp-control-shadow-hover);
  color: var(--text-primary);
  transform: rotate(90deg);
}
.vp-close:focus-visible {
  outline: none;
  box-shadow: var(--vp-control-shadow-hover), var(--focus-ring-wide);
}
.vp-close:active {
  transform: rotate(90deg) scale(0.96);
}
.vp-player-wrap { border-radius: 20px; overflow: hidden; box-shadow: var(--shadow-sheet); background: var(--vp-player-bg); border: var(--stroke-pro) solid var(--vp-sheet-border); }
.vp-video { display: block; width: 100%; border-radius: 20px; background: var(--vp-player-bg); }
.vp-info { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 8px 10px; background: var(--vp-control-bg); border: 1px solid var(--vp-control-border); border-radius: var(--radius-lg); box-shadow: var(--vp-control-shadow); backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control)); -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control)); }
.vp-title { min-width: 0; font-size: 14px; color: var(--text-secondary); font-weight: 600; letter-spacing: 0; font-family: var(--font-mono); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>

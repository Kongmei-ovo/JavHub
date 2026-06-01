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
        <div class="vp-speed-ctrl">
          <button
            v-for="speedOption in speedOptions"
            :key="speedOption"
            type="button"
            :class="['vp-speed-btn', { active: speed === speedOption }]"
            @click="$emit('speed', speedOption)"
          >{{ speedOption === 1 ? '1x' : speedOption + 'x' }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'HlsPlayerOverlay',
  props: {
    visible: { type: Boolean, default: false },
    title: { type: String, default: '' },
    speed: { type: Number, default: 1 },
  },
  emits: ['close', 'speed'],
  data() {
    return {
      speedOptions: [0.5, 0.75, 1, 1.25, 1.5, 2],
    }
  },
  methods: {
    mediaElement() {
      return this.$refs.streamVideoEl
    },
  },
}
</script>

<style scoped>
.vp-overlay {
  --vp-control-bg: var(--material-glass-control);
  --vp-control-bg-hover: var(--material-glass-control-hover);
  --vp-control-border: var(--glass-control-border);
  --vp-control-border-hover: var(--glass-control-border-hover);
  --vp-control-shadow: var(--glass-control-shadow);
  --vp-control-shadow-hover: var(--glass-control-shadow-hover);
  --vp-sheet-bg: var(--material-glass-sheet);
  --vp-sheet-border: var(--glass-control-border);
  --vp-player-bg: #000;
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
.vp-close { position: absolute; top: -58px; right: 0; background: var(--vp-control-bg); border: var(--stroke-pro) solid var(--vp-control-border); border-radius: 50%; width: 44px; height: 44px; display: flex; align-items: center; justify-content: center; color: var(--text-secondary); box-shadow: var(--vp-control-shadow); backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control)); -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control)); cursor: pointer; transition: background var(--motion-standard), color var(--motion-fast), transform var(--motion-standard), opacity var(--motion-fast); }
.vp-close:hover { background: var(--vp-control-bg-hover); border-color: var(--vp-control-border-hover); box-shadow: var(--vp-control-shadow-hover); color: var(--text-primary); transform: rotate(90deg); }
.vp-player-wrap { border-radius: 20px; overflow: hidden; box-shadow: var(--shadow-sheet); background: var(--vp-player-bg); border: var(--stroke-pro) solid var(--vp-sheet-border); }
.vp-video { display: block; width: 100%; border-radius: 20px; background: var(--vp-player-bg); }
.vp-info { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 8px 10px; background: var(--vp-control-bg); border: 1px solid var(--vp-control-border); border-radius: var(--radius-lg); box-shadow: var(--vp-control-shadow); backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control)); -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control)); }
.vp-title { min-width: 0; font-size: 14px; color: var(--text-secondary); font-weight: 600; letter-spacing: 0; font-family: var(--font-mono); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.vp-speed-ctrl { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; justify-content: flex-end; }
.vp-speed-btn { font-size: 13px; padding: 5px 14px; background: var(--vp-control-bg); border: var(--stroke-pro) solid var(--vp-control-border); border-radius: 40px; color: var(--text-secondary); box-shadow: var(--vp-control-shadow); backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control)); -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control)); cursor: pointer; transition: background var(--motion-standard), color var(--motion-fast), transform var(--motion-standard), opacity var(--motion-fast); }
.vp-speed-btn:hover { background: var(--vp-control-bg-hover); border-color: var(--vp-control-border-hover); box-shadow: var(--vp-control-shadow-hover); color: var(--text-primary); }
.vp-speed-btn.active { background: var(--glass-active-material); border-color: var(--glass-active-border); box-shadow: var(--glass-active-shadow); color: var(--text-primary); font-weight: 700; }
</style>

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
.vp-overlay { position: fixed; inset: 0; z-index: var(--z-modal); display: flex; align-items: center; justify-content: center; background: rgba(0, 0, 0, 0.7); backdrop-filter: blur(32px) saturate(180%); -webkit-backdrop-filter: blur(32px) saturate(180%); animation: fadeIn 0.4s var(--ease-pro); }
.vp-container { position: relative; width: 90vw; max-width: 1080px; display: flex; flex-direction: column; gap: 24px; }
.vp-close { position: absolute; top: -60px; right: 0; background: rgba(255,255,255,0.08); border: var(--stroke-pro) solid rgba(255,255,255,0.12); border-radius: 50%; width: 44px; height: 44px; display: flex; align-items: center; justify-content: center; color: rgba(255,255,255,0.7); cursor: pointer; transition: var(--transition-pro); }
.vp-close:hover { background: rgba(255,255,255,0.15); color: #fff; transform: rotate(90deg); }
.vp-player-wrap { border-radius: 20px; overflow: hidden; box-shadow: 0 40px 120px rgba(0,0,0,0.8); background: #000; border: var(--stroke-pro) solid rgba(255,255,255,0.1); }
.vp-video { display: block; width: 100%; border-radius: 20px; background: #000; }
.vp-info { display: flex; align-items: center; justify-content: space-between; padding: 0 8px; }
.vp-title { font-size: 14px; color: rgba(255,255,255,0.5); font-weight: 600; letter-spacing: 0.1em; text-transform: uppercase; font-family: var(--font-mono); }
.vp-speed-ctrl { display: flex; align-items: center; gap: 8px; }
.vp-speed-btn { font-size: 13px; padding: 5px 14px; background: rgba(255,255,255,0.07); border: var(--stroke-pro) solid rgba(255,255,255,0.1); border-radius: 40px; color: rgba(255,255,255,0.5); cursor: pointer; transition: var(--transition-pro); }
.vp-speed-btn:hover { background: rgba(255,255,255,0.12); color: rgba(255,255,255,0.9); border-color: rgba(255,255,255,0.2); }
.vp-speed-btn.active { background: var(--accent); border-color: var(--accent); color: var(--text-on-accent); font-weight: 700; }
</style>

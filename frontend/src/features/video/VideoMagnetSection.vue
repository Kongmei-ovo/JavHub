<template>
  <div v-if="magnets.length" class="modal-section">
    <h4 class="section-title">磁力链接</h4>
    <div class="magnets-list">
      <div v-for="(mag, idx) in magnets" :key="idx" class="magnet-item">
        <div class="magnet-info">
          <span v-if="mag.quality || mag.resolution" class="magnet-badge">{{ mag.quality || mag.resolution }}</span>
          <span v-if="mag.hd" class="magnet-badge hd">HD</span>
          <span v-if="mag.subtitle" class="magnet-badge sub">字幕</span>
          <span class="magnet-size">{{ mag.size }}</span>
        </div>
        <div class="magnet-actions">
          <button class="btn-copy" type="button" @click="$emit('copy', mag)" title="复制磁链">复制</button>
          <button class="btn-download" type="button" @click="$emit('download', mag)">下载</button>
        </div>
      </div>
    </div>
  </div>
  <div v-else-if="!videoLoaded" class="modal-section">
    <h4 class="section-title">磁力链接</h4>
    <div class="magnets-list">
      <div v-for="n in 2" :key="n" class="magnet-item skeleton" style="height: 44px"></div>
    </div>
  </div>
  <div v-else class="no-magnets">
    <span>暂无磁力链接</span>
  </div>
</template>

<script>
export default {
  name: 'VideoMagnetSection',
  props: {
    magnets: { type: Array, default: () => [] },
    videoLoaded: { type: Boolean, default: false },
  },
  emits: ['copy', 'download'],
}
</script>

<style scoped>
.modal-section { margin-top: 0; }
.section-title { font-size: 12px; font-weight: 700; margin-bottom: 20px; color: rgba(255, 255, 255, 0.5); text-transform: uppercase; letter-spacing: 0.12em; }
.magnets-list { display: flex; flex-direction: column; gap: 12px; }
.magnet-item { display: flex; justify-content: space-between; align-items: center; padding: 20px 24px; background: rgba(255, 255, 255, 0.04); border-radius: var(--radius-lg); border: 1px solid rgba(255, 255, 255, 0.08); transition: var(--transition-pro); }
.magnet-item:hover { border-color: rgba(255, 255, 255, 0.2); background: rgba(255, 255, 255, 0.08); }
.magnet-info { display: flex; align-items: center; gap: 12px; }
.magnet-badge { padding: 4px 10px; background: rgba(255, 255, 255, 0.1); color: #ffffff; border: 1px solid rgba(255, 255, 255, 0.15); font-size: 11px; font-weight: 700; border-radius: 6px; }
.magnet-badge.hd { background: rgba(50, 215, 75, 0.15); color: #32D74B; border-color: rgba(50, 215, 75, 0.3); }
.magnet-badge.sub { background: rgba(255, 159, 10, 0.15); color: #FF9F0A; border-color: rgba(255, 159, 10, 0.3); }
.magnet-size { font-size: 14px; color: rgba(255, 255, 255, 0.5); font-family: var(--font-mono); }
.magnet-actions { display: flex; gap: 12px; }
.btn-copy { background: transparent; border: 1px solid rgba(255, 255, 255, 0.2); padding: 8px 18px; border-radius: 40px; cursor: pointer; color: rgba(255, 255, 255, 0.8); font-size: 13px; transition: var(--transition-pro); }
.btn-copy:hover { border-color: white; color: white; background: rgba(255, 255, 255, 0.1); }
.btn-download { background: rgba(255, 255, 255, 0.9); color: #000; border: none; padding: 8px 24px; border-radius: 40px; cursor: pointer; font-size: 14px; font-weight: 600; transition: var(--transition-pro); }
.btn-download:hover { background: #fff; transform: translateY(-2px); box-shadow: 0 8px 20px rgba(255, 255, 255, 0.2); }
.no-magnets { text-align: center; padding: 32px; color: rgba(255, 255, 255, 0.3); font-size: 15px; border: 1px dashed rgba(255, 255, 255, 0.1); border-radius: var(--radius-lg); }
.skeleton { background: rgba(255, 255, 255, 0.05); position: relative; overflow: hidden; border-radius: 8px; }
.skeleton::after { content: ""; position: absolute; inset: 0; background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.05), transparent); transform: translateX(-100%); animation: shimmer 2s infinite; }
@keyframes shimmer { 100% { transform: translateX(100%); } }
</style>

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
.section-title { font-size: var(--type-caption); font-weight: 650; line-height: 1.3; margin-bottom: 14px; color: var(--modal-text-muted, var(--text-muted)); letter-spacing: 0; }
.magnets-list { display: flex; flex-direction: column; gap: 10px; }
.magnet-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  padding: 16px 18px;
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  border-radius: var(--radius-lg);
  border: 1px solid var(--glass-control-border);
  transition: transform var(--motion-standard), background var(--motion-standard), border-color var(--motion-standard), box-shadow var(--motion-standard);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}
.magnet-item:hover {
  border-color: var(--glass-control-border-hover);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  transform: translateY(-1px);
  box-shadow: var(--glass-control-shadow-hover);
}
.magnet-item:focus-within {
  border-color: var(--glass-control-border-hover);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  transform: translateY(-1px);
  box-shadow: var(--glass-control-shadow-hover), 0 0 0 3px rgba(var(--accent-rgb), 0.12);
}
.magnet-info { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; min-width: 0; }
.magnet-badge { padding: 4px 10px; background: var(--surface-specular-edge), var(--surface-noise), var(--badge-info-bg); color: var(--badge-info-text); border: 1px solid var(--badge-info-border); font-size: var(--type-micro); font-weight: 650; border-radius: var(--radius-sm); }
.magnet-badge.hd { background: var(--surface-specular-edge), var(--surface-noise), var(--badge-success-bg); color: var(--badge-success-text); border-color: var(--badge-success-border); }
.magnet-badge.sub { background: var(--surface-specular-edge), var(--surface-noise), var(--badge-warning-bg); color: var(--badge-warning-text); border-color: var(--badge-warning-border); }
.magnet-size { font-size: var(--type-body); color: var(--text-muted); font-family: var(--font-mono); font-variant-numeric: tabular-nums; }
.magnet-actions { display: flex; gap: 8px; flex-shrink: 0; }
.btn-copy,
.btn-download {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: var(--compact-toolbar-height);
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  border: 1px solid var(--glass-control-border);
  padding: 8px 18px;
  border-radius: var(--radius-control);
  cursor: pointer;
  color: var(--text-primary);
  font-size: var(--type-control);
  font-weight: 600;
  transition: transform var(--motion-standard), background var(--motion-standard), border-color var(--motion-standard), box-shadow var(--motion-standard);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}
.btn-copy:hover,
.btn-download:hover {
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  border-color: var(--glass-control-border-hover);
  transform: translateY(-1px);
  box-shadow: var(--glass-control-shadow-hover);
}
.btn-copy:focus-visible {
  outline: none;
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  border-color: var(--glass-control-border-hover);
  transform: translateY(-1px);
  box-shadow: var(--glass-control-shadow-hover), 0 0 0 3px rgba(var(--accent-rgb), 0.12);
}
.btn-copy:active,
.btn-download:active { transform: translateY(0) scale(0.98); }
.btn-download {
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--glass-active-material);
  border-color: var(--glass-active-border);
}
.btn-download:hover {
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--glass-active-material);
}
.btn-download:focus-visible {
  outline: none;
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--glass-active-material);
  border-color: var(--glass-active-border);
  transform: translateY(-1px);
  box-shadow: var(--glass-active-shadow), 0 0 0 3px rgba(var(--accent-rgb), 0.14);
}
.no-magnets {
  text-align: center;
  padding: 28px;
  color: var(--text-muted);
  font-size: var(--type-body);
  border: 1px dashed var(--glass-control-border);
  border-radius: var(--radius-lg);
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}
.skeleton { background: var(--skeleton-base); position: relative; overflow: hidden; border-radius: var(--radius-lg); cursor: default; pointer-events: none; }
.skeleton::after { content: ""; position: absolute; inset: 0; background: linear-gradient(90deg, transparent, var(--skeleton-highlight), transparent); transform: translateX(-100%); animation: shimmer 2s infinite; opacity: 0.42; }
@keyframes shimmer { 100% { transform: translateX(100%); } }

@media (max-width: 768px) {
  .section-title { margin-bottom: 12px; }
  .magnet-item {
    flex-direction: column;
    align-items: stretch;
    padding: 14px;
  }
  .magnet-actions {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .btn-copy,
  .btn-download {
    width: 100%;
    padding-inline: 12px;
  }
}
</style>

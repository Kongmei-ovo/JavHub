<template>
  <div class="file-grid">
    <div
      v-for="file in files"
      :key="file.file_id"
      class="file-cell"
      :class="{ selected: isSelected(file.file_id) }"
      @click="$emit('open', file)"
    >
      <label class="pick" @click.stop>
        <input type="checkbox" :checked="isSelected(file.file_id)" @change="$emit('toggle', file.file_id)" />
      </label>
      <div class="file-ico" :class="kindOf(file)">
        <img
          v-if="kindOf(file) === 'image'"
          :src="thumbUrl(file)"
          alt=""
          loading="lazy"
          decoding="async"
          @error="onThumbError"
        />
        <span v-else class="ico-glyph">{{ glyph(file) }}</span>
        <span v-if="file.duration" class="dur">{{ formatDuration(file.duration) }}</span>
      </div>
      <div class="file-name" :title="file.name">{{ file.name }}</div>
      <div class="file-meta">{{ file.is_dir ? '文件夹' : formatSize(file.size) }}</div>
    </div>
  </div>
</template>

<script>
import api from '../../api'
import { kindOf, glyph, formatSize, formatDuration } from './driveFormat'

export default {
  name: 'DriveGrid',
  props: {
    files: { type: Array, required: true },
    selected: { type: Array, default: () => [] },
  },
  emits: ['open', 'toggle'],
  methods: {
    kindOf,
    glyph,
    formatSize,
    formatDuration,
    isSelected(id) {
      return this.selected.includes(id)
    },
    thumbUrl(file) {
      return api.open115ImageUrl(file.pick_code, file.extension)
    },
    onThumbError(e) {
      const el = e?.target
      if (el) el.style.visibility = 'hidden'
    },
  },
}
</script>

<style scoped>
.file-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 12px; }
.file-cell { position: relative; background: var(--surface-card); border: 1px solid var(--border); border-radius: var(--radius-card); padding: 12px; cursor: pointer; transition: transform var(--motion-fast, .15s); display: flex; flex-direction: column; gap: 6px; }
.file-cell:hover { background: var(--surface-card-hover); }
.file-cell.selected { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent); }
.pick { position: absolute; top: 8px; left: 8px; z-index: 2; opacity: 0; transition: opacity var(--motion-fast, .15s); }
.file-cell:hover .pick, .file-cell.selected .pick { opacity: 1; }
.pick input { width: 16px; height: 16px; accent-color: var(--accent); cursor: pointer; }

.file-ico { position: relative; aspect-ratio: 1 / 1; border-radius: var(--radius-md); background: var(--surface-control); display: flex; align-items: center; justify-content: center; overflow: hidden; }
.file-ico img { width: 100%; height: 100%; object-fit: cover; }
.ico-glyph { font-size: 38px; line-height: 1; }
.dur { position: absolute; right: 5px; bottom: 5px; background: var(--media-caption-scrim-strong); color: var(--text-on-accent-solid); font-size: var(--type-micro); padding: 1px 5px; border-radius: 4px; }

.file-name { font-size: var(--type-control); color: var(--text-primary); line-height: 1.3; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.file-meta { font-size: var(--type-micro); color: var(--text-muted); }
</style>

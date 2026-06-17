<template>
  <div class="file-list" role="table">
    <div class="list-head" role="row">
      <span class="col-pick" role="columnheader"></span>
      <button class="col-name th" :class="sortClass('name')" type="button" role="columnheader" @click="$emit('sort', 'name')">
        名称<span class="sort-caret">{{ caret('name') }}</span>
      </button>
      <button class="col-size th" :class="sortClass('size')" type="button" role="columnheader" @click="$emit('sort', 'size')">
        大小<span class="sort-caret">{{ caret('size') }}</span>
      </button>
      <button class="col-type th" :class="sortClass('type')" type="button" role="columnheader" @click="$emit('sort', 'type')">
        类型<span class="sort-caret">{{ caret('type') }}</span>
      </button>
      <button class="col-time th" :class="sortClass('time')" type="button" role="columnheader" @click="$emit('sort', 'time')">
        修改时间<span class="sort-caret">{{ caret('time') }}</span>
      </button>
    </div>

    <div
      v-for="file in files"
      :key="file.file_id"
      class="list-row"
      :class="{ selected: isSelected(file.file_id) }"
      role="row"
      @click="$emit('open', file)"
    >
      <label class="col-pick" @click.stop>
        <input type="checkbox" :checked="isSelected(file.file_id)" @change="$emit('toggle', file.file_id)" />
      </label>
      <div class="col-name cell-name">
        <span class="row-glyph">{{ glyph(file) }}</span>
        <span class="row-name" :title="file.name">{{ file.name }}</span>
      </div>
      <div class="col-size cell-dim">{{ file.is_dir ? '—' : formatSize(file.size) }}</div>
      <div class="col-type cell-dim">{{ typeLabel(file) }}</div>
      <div class="col-time cell-dim">{{ formatDate(file.mtime) }}</div>
    </div>
  </div>
</template>

<script>
import { glyph, formatSize, formatDate, typeLabel } from './driveFormat'

export default {
  name: 'DriveList',
  props: {
    files: { type: Array, required: true },
    selected: { type: Array, default: () => [] },
    sortKey: { type: String, default: '' },
    sortAsc: { type: Boolean, default: true },
  },
  emits: ['open', 'toggle', 'sort'],
  methods: {
    glyph,
    formatSize,
    formatDate,
    typeLabel,
    isSelected(id) {
      return this.selected.includes(id)
    },
    sortClass(key) {
      return { active: this.sortKey === key }
    },
    caret(key) {
      if (this.sortKey !== key) return ''
      return this.sortAsc ? '▲' : '▼'
    },
  },
}
</script>

<style scoped>
.file-list { display: flex; flex-direction: column; border: 1px solid var(--border); border-radius: var(--radius-card); overflow: hidden; background: var(--surface-card); }

.list-head, .list-row {
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr) 96px 96px 156px;
  align-items: center;
  gap: 8px;
  padding: 0 12px;
}
.list-head { height: 38px; border-bottom: 1px solid var(--border); background: var(--surface-control); }
.th { display: inline-flex; align-items: center; gap: 4px; background: none; border: none; padding: 0; height: 100%; color: var(--text-muted); font-size: var(--type-caption); font-weight: 600; cursor: pointer; text-align: left; }
.th:hover { color: var(--text-primary); }
.th.active { color: var(--text-primary); }
.sort-caret { font-size: var(--type-micro); }

.list-row { min-height: 40px; cursor: pointer; border-bottom: 1px solid var(--hairline); transition: background var(--motion-fast, .15s); }
.list-row:last-child { border-bottom: none; }
.list-row:hover { background: var(--surface-card-hover); }
.list-row.selected { background: var(--surface-card-hover); box-shadow: inset 2px 0 0 var(--accent); }

.col-pick { display: flex; align-items: center; }
.col-pick input { width: 16px; height: 16px; accent-color: var(--accent); cursor: pointer; }
.cell-name { display: flex; align-items: center; gap: 8px; min-width: 0; }
.row-glyph { flex: 0 0 auto; font-size: var(--type-card-title); }
.row-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: var(--type-control); color: var(--text-primary); }
.cell-dim { font-size: var(--type-caption); color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

@media (max-width: 768px) {
  .list-head, .list-row { grid-template-columns: 32px minmax(0, 1fr) 70px; }
  .col-type, .col-time { display: none; }
}
</style>

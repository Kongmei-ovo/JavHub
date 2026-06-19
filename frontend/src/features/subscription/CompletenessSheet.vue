<template>
  <teleport to="body">
    <transition name="sheet">
      <div v-if="sub" class="sheet-overlay" @click.self="$emit('close')">
        <div class="sheet completeness-sheet" @click.stop>
          <div class="sheet-top-bar"><div class="sheet-top-actions"><button class="top-action-btn" type="button" @click="$emit('close')">关闭</button></div></div>
          <div class="since-last-head">
            <span class="discover-kicker">收藏完整度</span>
            <h2>{{ name }}</h2>
            <p v-if="loading">正在统计…</p>
            <p v-else>已收 {{ ownedFilms }} / {{ totalFilms }} 部 · {{ percent }}%<span class="completeness-note"> · 含补全发现的私拍/无码;跑补全后总数可能增加</span></p>
          </div>

          <div v-if="!loading && totalFilms > 0" class="completeness-body">
            <div class="completeness-bar" role="img" aria-label="完整度分布">
              <span v-for="seg in segments" :key="seg.key" class="completeness-seg" :class="seg.cls" :style="{ width: seg.pct + '%' }"></span>
            </div>
            <div class="completeness-legend">
              <span v-for="seg in segments" :key="seg.key" class="completeness-legend-item">
                <i class="completeness-dot" :class="seg.cls"></i>{{ seg.label }} {{ seg.count }}
              </span>
            </div>
            <div class="completeness-list">
              <div v-for="film in gapFilms" :key="film.canonical_number" class="completeness-item" :class="tierClass(film.status)">
                <div class="completeness-item-main">
                  <strong class="completeness-item-title">{{ film.title || film.display_code }}</strong>
                  <span class="completeness-item-meta">{{ film.display_code }}<template v-if="film.release_date"> · {{ film.release_date }}</template><template v-if="film.origin === 'supplement'"> · 私拍/补全</template></span>
                </div>
                <span class="completeness-badge" :class="tierClass(film.status)">{{ tierLabel(film.status) }}</span>
              </div>
              <div v-if="gapFilms.length === 0" class="completeness-item owned"><strong class="completeness-item-title">已全部收齐 🎉</strong><span class="completeness-item-meta">这位演员已编目的作品都在库里</span></div>
            </div>
          </div>
          <div v-else-if="!loading" class="completeness-body">
            <div class="completeness-item"><strong class="completeness-item-title">暂无可统计的作品</strong><span class="completeness-item-meta">目录里还没有这位演员的番号,或补全尚未运行</span></div>
          </div>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  sub: { type: Object, default: null },
  name: { type: String, default: '' },
  data: { type: Object, default: null },
  loading: { type: Boolean, default: false },
})
defineEmits(['close'])

const TIERS = [
  { key: 'owned', label: '已拥有', cls: 'owned' },
  { key: 'in_progress', label: '下载中', cls: 'progress' },
  { key: 'available', label: '可补(有磁力)', cls: 'available' },
  { key: 'needs_magnet', label: '无磁力·待手动', cls: 'nomagnet' },
]
const summary = computed(() => props.data?.summary || {})
const totalFilms = computed(() => Number(props.data?.total_films || 0))
const ownedFilms = computed(() => Number(props.data?.owned_films || 0))
const percent = computed(() => totalFilms.value > 0 ? Math.round((ownedFilms.value / totalFilms.value) * 100) : 0)
const segments = computed(() => {
  const total = totalFilms.value || 1
  return TIERS.map(tier => ({ ...tier, count: Number(summary.value[tier.key] || 0), pct: (Number(summary.value[tier.key] || 0) / total) * 100 }))
})
const gapFilms = computed(() => (props.data?.films || []).filter(f => f.status !== 'owned'))
function tierLabel(status) { return (TIERS.find(t => t.key === status) || {}).label || status }
function tierClass(status) { return (TIERS.find(t => t.key === status) || {}).cls || '' }
</script>

<style scoped>
.completeness-sheet { max-width: 640px; }
.since-last-head { padding: 20px 24px 12px; }
.since-last-head h2 { margin: 0; color: var(--text-primary); font-size: var(--type-section-title); }
.since-last-head p { margin: 8px 0 0; color: var(--text-secondary); font-size: var(--type-control); }
.completeness-note { color: var(--text-muted); font-weight: 500; }
.completeness-body { display: grid; gap: 14px; padding: 4px 20px 28px; }
.completeness-bar { display: flex; width: 100%; height: 14px; border-radius: 999px; overflow: hidden; background: var(--subscription-control-bg); box-shadow: var(--glass-inner-shadow); }
.completeness-seg { display: block; height: 100%; transition: width .3s ease; }
.completeness-seg.owned, .completeness-dot.owned { background: var(--success, #34c759); }
.completeness-seg.progress, .completeness-dot.progress { background: var(--accent, #0a84ff); }
.completeness-seg.available, .completeness-dot.available { background: var(--warning, #ff9f0a); }
.completeness-seg.nomagnet, .completeness-dot.nomagnet { background: var(--danger, #ff453a); }
.completeness-legend { display: flex; flex-wrap: wrap; gap: 12px; }
.completeness-legend-item { display: inline-flex; align-items: center; gap: 6px; color: var(--text-secondary); font-size: var(--type-caption); font-weight: 600; }
.completeness-dot { width: 10px; height: 10px; border-radius: 3px; }
.completeness-list { display: grid; gap: 8px; max-height: 52vh; overflow-y: auto; }
.completeness-item { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 10px 14px; border: 1px solid var(--subscription-control-border); border-radius: var(--radius-md); background: var(--subscription-control-bg); box-shadow: var(--subscription-control-shadow), var(--glass-inner-shadow); }
.completeness-item.nomagnet { border-color: color-mix(in srgb, var(--danger, #ff453a) 45%, transparent); }
.completeness-item-main { display: grid; gap: 3px; min-width: 0; }
.completeness-item-title { color: var(--text-primary); font-weight: 650; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.completeness-item-meta { color: var(--text-muted); font-size: var(--type-caption); }
.completeness-badge { flex: none; padding: 3px 9px; border-radius: 999px; font-size: var(--type-caption); font-weight: 700; color: #fff; }
.completeness-badge.progress { background: var(--accent, #0a84ff); }
.completeness-badge.available { background: var(--warning, #ff9f0a); }
.completeness-badge.nomagnet { background: var(--danger, #ff453a); }
.completeness-badge.owned { background: var(--success, #34c759); }
</style>

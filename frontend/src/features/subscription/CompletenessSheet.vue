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
            <template v-if="ownedList.length">
              <div class="completeness-subhead">已拥有 {{ ownedList.length }} 部 · 可从库中删除(删 115 整个文件夹)</div>
              <div class="completeness-list">
                <div v-for="film in ownedList" :key="film.canonical_number" class="completeness-item owned">
                  <div class="completeness-item-main">
                    <strong class="completeness-item-title">{{ film.title || film.display_code }}</strong>
                    <span class="completeness-item-meta">{{ film.display_code }}<template v-if="film.release_date"> · {{ film.release_date }}</template></span>
                  </div>
                  <button class="completeness-del" :class="{ confirming: confirming === film.canonical_number }" :disabled="deleting === film.canonical_number" type="button" @click="removeFilm(film)">
                    {{ deleting === film.canonical_number ? '删除中…' : (confirming === film.canonical_number ? '确认删除?' : '从库中删除') }}
                  </button>
                </div>
              </div>
            </template>

            <div v-if="gapList.length" class="completeness-subhead">缺口 {{ gapList.length }} 部<template v-if="gapList.length > visibleGaps.length"> · 列出前 {{ visibleGaps.length }} 部</template></div>
            <div v-if="gapList.length" class="completeness-list">
              <div v-for="film in visibleGaps" :key="film.canonical_number" class="completeness-item" :class="tierClass(film.status)">
                <div class="completeness-item-main">
                  <strong class="completeness-item-title">{{ film.title || film.display_code }}</strong>
                  <span class="completeness-item-meta">{{ film.display_code }}<template v-if="film.release_date"> · {{ film.release_date }}</template><template v-if="film.origin === 'supplement'"> · 私拍/补全</template></span>
                </div>
                <span class="completeness-badge" :class="tierClass(film.status)">{{ tierLabel(film.status) }}</span>
              </div>
            </div>
            <div v-if="gapList.length === 0" class="completeness-item owned"><strong class="completeness-item-title">已全部收齐 🎉</strong><span class="completeness-item-meta">这位演员已编目的作品都在库里</span></div>
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
import { computed, ref } from 'vue'
import api from '../../api'
import { ElMessage } from '../../utils/message.js'

const GAP_LIST_CAP = 200

const props = defineProps({
  sub: { type: Object, default: null },
  name: { type: String, default: '' },
  data: { type: Object, default: null },
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['close', 'refresh'])

const confirming = ref(null)
const deleting = ref(null)

async function removeFilm(film) {
  if (confirming.value !== film.canonical_number) { confirming.value = film.canonical_number; return }
  deleting.value = film.canonical_number
  try {
    await api.deleteMovieLibrary(film.canonical_number)
    ElMessage.success('已从库中删除')
    emit('refresh')
  } catch (error) {
    ElMessage.error('删除失败')
  } finally {
    deleting.value = null
    confirming.value = null
  }
}

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
const ownedList = computed(() => (props.data?.films || []).filter(f => f.status === 'owned'))
const gapList = computed(() => (props.data?.films || []).filter(f => f.status !== 'owned'))
const visibleGaps = computed(() => gapList.value.slice(0, GAP_LIST_CAP))
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
.completeness-subhead { color: var(--text-secondary); font-size: var(--type-caption); font-weight: 700; padding: 2px 2px 0; }
.completeness-list { display: grid; gap: 8px; max-height: 42vh; overflow-y: auto; }
.completeness-del { flex: none; min-height: 30px; padding: 0 12px; border: 1px solid color-mix(in srgb, var(--danger, #ff453a) 40%, transparent); border-radius: 999px; background: transparent; color: var(--danger, #ff453a); font-size: var(--type-caption); font-weight: 700; cursor: pointer; }
.completeness-del.confirming { background: var(--danger, #ff453a); color: #fff; }
.completeness-del:disabled { opacity: .6; cursor: default; }
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

<template>
  <section class="collection-list">
    <!-- toolbar: 筛选下拉 + 重新拉片单（收藏进度由上方 cmp-strip 表头展示，这里不重复） -->
    <div class="cl-toolbar">
      <div ref="filterRoot" class="cl-filter">
        <button
          type="button" class="filter-trigger"
          :class="{ on: filterOpen, active: hasActiveFilter }"
          :aria-expanded="filterOpen" @click="filterOpen = !filterOpen"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true">
            <path d="M3 6h11M3 12h7M3 18h13" /><circle cx="17.5" cy="6" r="2.2" /><circle cx="13.5" cy="12" r="2.2" /><circle cx="19" cy="18" r="2.2" />
          </svg>
          <span>筛选</span>
          <span v-if="activeCount" class="ft-count">{{ activeCount }}</span>
          <svg class="ft-chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><polyline points="6 9 12 15 18 9" /></svg>
        </button>

        <transition name="fp">
          <div v-if="filterOpen" class="filter-panel" role="dialog" aria-label="片单筛选">
            <div class="fp-row">
              <span class="fp-label">来源</span>
              <div class="stage-seg fp-seg" role="group" aria-label="来源筛选">
                <button
                  v-for="opt in originOptions" :key="opt.key" type="button"
                  :class="{ active: originFilter === opt.key }" @click="originFilter = opt.key"
                >{{ opt.label }}</button>
              </div>
            </div>
            <div class="fp-row">
              <span class="fp-label">入库</span>
              <div class="stage-seg fp-seg" role="group" aria-label="入库筛选">
                <button
                  v-for="opt in ownedOptions" :key="opt.key" type="button"
                  :class="{ active: ownedFilter === opt.key }" @click="ownedFilter = opt.key"
                >{{ opt.label }}</button>
              </div>
            </div>
            <div class="fp-row">
              <span class="fp-label">时间</span>
              <GlassSelect
                v-model="yearFilter" :options="yearSelectOptions" size="compact"
                placement="right" placeholder="全部年份" aria-label="出演时间筛选"
              />
            </div>
            <div class="fp-foot">
              <span class="fp-count">{{ countLabel }}</span>
              <button v-if="hasActiveFilter" type="button" class="fp-clear" @click="clearFilters">清除筛选</button>
            </div>
          </div>
        </transition>
      </div>

      <span v-if="hasActiveFilter" class="cl-result">已筛选 {{ filteredCount }} 部</span>
      <span class="cl-spacer"></span>

      <button class="btn btn-primary" type="button" :disabled="recomputing" @click="$emit('recompute')">
        <span v-if="recomputing" class="spin-ring" aria-hidden="true"></span>
        {{ recomputing ? '补全中…' : '重新拉片单' }}
      </button>
    </div>

    <AppleSkeleton v-if="loading && !yearGroups.length" class="panel-state" variant="list" :items="8" label="影片目录加载中" />

    <AppleEmptyState
      v-else-if="!yearGroups.length"
      class="panel-state"
      title="还没有作品目录"
      description="这位演员的片单还没有结果。"
      next-step="点「重新拉片单」拉取她的完整作品集。"
      action-label="重新拉片单"
      density="compact"
      @action="$emit('recompute')"
    />

    <template v-else>
      <AppleEmptyState
        v-if="!filteredGroups.length"
        class="panel-state"
        title="没有符合筛选的作品"
        description="当前的来源 / 入库 / 出演时间筛选下没有作品。"
        next-step="放宽筛选条件，或清除筛选查看全部。"
        action-label="清除筛选"
        density="compact"
        @action="clearFilters"
      />

      <div v-for="group in filteredGroups" v-else :key="group.year" class="year-group">
        <div class="year-header">
          <span class="year-label">{{ group.year }}</span>
          <span class="year-count">{{ group.films.length }} 部</span>
        </div>
        <div class="movie-list">
          <div class="movie-list-head">
            <span class="ml-col ml-code">番号</span>
            <span class="ml-col ml-title">片名</span>
            <span class="ml-col ml-date">出演时间</span>
            <span class="ml-col ml-origin">来源</span>
            <span class="ml-col ml-owned">115</span>
          </div>
          <div v-for="film in group.films" :key="film.canonical_number" class="movie-list-row">
            <span class="ml-col ml-code">{{ film.display_code || film.canonical_number }}</span>
            <span class="ml-col ml-title">{{ film.title || '—' }}</span>
            <span class="ml-col ml-date">{{ film.release_date || '—' }}</span>
            <span class="ml-col ml-origin">{{ isSupplement(film) ? '私拍' : '正片' }}</span>
            <span class="ml-col ml-owned">
              <span class="owned-badge" :class="isOwned(film) ? 'is-owned' : 'not-owned'">{{ isOwned(film) ? '已入库' : '未入库' }}</span>
            </span>
          </div>
        </div>
      </div>
    </template>
  </section>
</template>

<script>
import AppleSkeleton from '../../components/AppleSkeleton.vue'
import AppleEmptyState from '../../components/AppleEmptyState.vue'
import GlassSelect from '../../components/GlassSelect.vue'

const ORIGIN_OPTIONS = [
  { key: 'all', label: '全部' },
  { key: 'native', label: '正片' },
  { key: 'supplement', label: '私拍' },
]
const OWNED_OPTIONS = [
  { key: 'all', label: '全部' },
  { key: 'owned', label: '已入库' },
  { key: 'not', label: '未入库' },
]

export default {
  name: 'CatalogCollectionList',
  components: { AppleSkeleton, AppleEmptyState, GlassSelect },
  props: {
    yearGroups: { type: Array, default: () => [] },
    ownedCount: { type: Number, default: 0 },
    totalCount: { type: Number, default: 0 },
    loading: { type: Boolean, default: false },
    recomputing: { type: Boolean, default: false },
  },
  emits: ['recompute'],
  data() {
    return { originFilter: 'all', ownedFilter: 'all', yearFilter: 'all', filterOpen: false }
  },
  computed: {
    originOptions() { return ORIGIN_OPTIONS },
    ownedOptions() { return OWNED_OPTIONS },
    allFilms() {
      return this.yearGroups.flatMap(group => group.films)
    },
    yearOptions() {
      // newest-first year order already comes from yearGroups; mirror it as strings.
      return this.yearGroups.map(group => String(group.year))
    },
    yearSelectOptions() {
      return [{ value: 'all', label: '全部年份' }, ...this.yearOptions.map(year => ({ value: year, label: year }))]
    },
    filteredGroups() {
      return this.yearGroups
        .filter(group => this.yearFilter === 'all' || String(group.year) === this.yearFilter)
        .map(group => ({ year: group.year, films: group.films.filter(f => this.matchOrigin(f) && this.matchOwned(f)) }))
        .filter(group => group.films.length)
    },
    filteredCount() {
      return this.filteredGroups.reduce((total, group) => total + group.films.length, 0)
    },
    hasActiveFilter() {
      return this.originFilter !== 'all' || this.ownedFilter !== 'all' || this.yearFilter !== 'all'
    },
    activeCount() {
      return [this.originFilter !== 'all', this.ownedFilter !== 'all', this.yearFilter !== 'all'].filter(Boolean).length
    },
    countLabel() {
      return this.hasActiveFilter ? `${this.filteredCount} / ${this.allFilms.length} 部` : `共 ${this.allFilms.length} 部`
    },
  },
  watch: {
    filterOpen(open) {
      if (open) {
        document.addEventListener('mousedown', this.onDocPointer)
        document.addEventListener('keydown', this.onKeydown)
      } else {
        document.removeEventListener('mousedown', this.onDocPointer)
        document.removeEventListener('keydown', this.onKeydown)
      }
    },
  },
  beforeUnmount() {
    document.removeEventListener('mousedown', this.onDocPointer)
    document.removeEventListener('keydown', this.onKeydown)
  },
  methods: {
    isOwned(film) { return film.funnel_stage === 'complete' || film.status === 'owned' || film.stage === 'complete' },
    isSupplement(film) { return film.origin === 'supplement' },
    matchOrigin(film) {
      if (this.originFilter === 'all') return true
      return this.originFilter === 'supplement' ? this.isSupplement(film) : !this.isSupplement(film)
    },
    matchOwned(film) {
      if (this.ownedFilter === 'all') return true
      return this.ownedFilter === 'owned' ? this.isOwned(film) : !this.isOwned(film)
    },
    clearFilters() {
      this.originFilter = 'all'
      this.ownedFilter = 'all'
      this.yearFilter = 'all'
    },
    // Close on outside click — but ignore the year GlassSelect's teleported menu.
    onDocPointer(event) {
      const root = this.$refs.filterRoot
      if (!root) return
      if (root.contains(event.target) || (event.target.closest && event.target.closest('.glass-select__menu'))) return
      this.filterOpen = false
    },
    onKeydown(event) {
      if (event.key === 'Escape') this.filterOpen = false
    },
  },
}
</script>

<style scoped src="./actressCatalogPanel.css"></style>
<style scoped>
.collection-list { display: grid; gap: var(--space-4); }

/* ---- toolbar ------------------------------------------------------------- */
.cl-toolbar { display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap; }
.cl-spacer { flex: 1; min-width: 0; }
.cl-result { font-size: var(--type-caption); color: var(--text-muted); font-variant-numeric: tabular-nums; white-space: nowrap; }

/* ---- 筛选 disclosure trigger -------------------------------------------- */
.cl-filter { position: relative; }
.filter-trigger {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  height: 36px;
  padding: 0 var(--space-3);
  border-radius: var(--radius-control);
  background: var(--card);
  border: 1px solid var(--hairline);
  color: var(--text-secondary);
  font: inherit;
  font-size: var(--type-caption);
  font-weight: 600;
  cursor: pointer;
}
.filter-trigger:hover { border-color: var(--hairline-strong); color: var(--text-primary); }
.filter-trigger.active { background: rgba(var(--accent-rgb), 0.14); border-color: rgba(var(--accent-rgb), 0.4); color: var(--text-primary); }
.filter-trigger > svg { width: 16px; height: 16px; }
.ft-chev { transition: transform var(--motion-fast); opacity: 0.7; }
.filter-trigger.on .ft-chev { transform: rotate(180deg); }
.ft-count {
  min-width: 18px;
  height: 18px;
  padding: 0 4px;
  border-radius: 999px;
  background: var(--accent);
  color: var(--text-on-accent-solid);
  font-size: var(--type-micro);
  font-weight: 700;
  display: inline-grid;
  place-items: center;
  font-variant-numeric: tabular-nums;
}

/* ---- floating filter panel ---------------------------------------------- */
.filter-panel {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  z-index: var(--z-dropdown);
  width: 320px;
  max-width: calc(100vw - var(--space-8));
  display: grid;
  gap: var(--space-4);
  padding: var(--space-4);
  border-radius: var(--radius-card);
  background: var(--card);
  border: 1px solid var(--hairline-strong);
  box-shadow: var(--shadow-pop, var(--shadow-card));
}
.fp-row { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); }
.fp-label { font-size: var(--type-caption); color: var(--text-muted); font-weight: 600; flex-shrink: 0; }
/* reuse the app's segmented control (.stage-seg) — bordered track, accent-tinted active */
.fp-seg { margin-bottom: 0; border: 1px solid var(--hairline); }
.fp-seg button { border-radius: 999px; font-size: var(--type-caption); }
.fp-seg button.active { background: rgba(var(--accent-rgb), 0.18); color: var(--text-primary); }
.fp-foot { display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); padding-top: var(--space-3); border-top: 1px solid var(--hairline); }
.fp-count { font-size: var(--type-caption); color: var(--text-muted); font-variant-numeric: tabular-nums; }
.fp-clear { border: 0; background: none; padding: 0; font: inherit; font-size: var(--type-caption); font-weight: 600; color: var(--accent); cursor: pointer; }
.fp-clear:hover { text-decoration: underline; }

.fp-enter-active, .fp-leave-active { transition: opacity var(--motion-fast), transform var(--motion-fast); }
.fp-enter-from, .fp-leave-to { opacity: 0; transform: translateY(-6px) scale(0.98); }

/* ---- year list ----------------------------------------------------------- */
.movie-list { display: grid; gap: 2px; background: var(--card); border: 1px solid var(--hairline); border-radius: var(--radius-card); padding: 6px 8px; }
.movie-list-head, .movie-list-row { display: grid; grid-template-columns: 130px 1fr 110px 64px 96px; gap: 12px; align-items: center; padding: 8px 10px; }
.movie-list-head { font-size: var(--type-caption-1); color: var(--text-muted); border-bottom: 1px solid var(--hairline); }
.movie-list-row { border-radius: 8px; }
.movie-list-row:hover { background: var(--card-hover); }
.ml-col { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: var(--type-callout); }
.ml-title { color: var(--text-secondary); }
.ml-origin { color: var(--text-muted); }
.owned-badge { font-size: var(--type-caption-1); padding: 2px 8px; border-radius: 999px; }
.owned-badge.is-owned { background: rgba(var(--ok-rgb), 0.16); color: var(--ok); }
.owned-badge.not-owned { background: var(--card-2); color: var(--text-muted); }
.year-header { display: flex; align-items: baseline; gap: 10px; margin: 14px 2px 6px; }
.year-label { font-size: var(--type-section-title); font-weight: 600; color: var(--text-primary); }
.year-count { font-size: var(--type-caption-1); color: var(--text-muted); }

@media (max-width: 720px) {
  .filter-panel { width: min(320px, calc(100vw - var(--space-6))); }
}
</style>

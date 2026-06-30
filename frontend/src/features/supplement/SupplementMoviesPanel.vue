<template>
  <!-- 全库「全部待补全」聚合视图 — 复用作品目录(catalog)卡片设计，去掉演员 hero。
       数据来自全库 supplement movies；按字段缺口呈现，保留筛选 / 批量动作 / 分页。 -->
  <section class="catalog-panel">
    <!-- 批量动作 Teleport 到顶部菜单行右侧(与 待补全演员/任务/来源健康 各 tab 一致)，
         与 tab 同行、靠右、等高，不再在面板内单占一行。 -->
    <Teleport to="#supplement-tab-actions" :disabled="!canTeleport">
      <button class="btn btn-primary btn-sm" type="button" :disabled="batchEnriching" @click="$emit('batch-enrich')">
        {{ batchEnriching ? '批量排队中…' : '批量补详情' }}
      </button>
      <button class="btn btn-ghost btn-sm" type="button" :disabled="candidateImporting" @click="$emit('create-candidates')">
        {{ candidateImporting ? '生成中…' : '生成下载候选' }}
      </button>
      <button class="btn btn-ghost btn-sm" type="button" @click="$emit('pick-actor')">选择演员</button>
    </Teleport>

    <!-- 未选演员的全库聚合 hero(只剩胶囊，无头像)——与选中演员时的作品目录 hero 同构，
         切 tab 时高度一致、不割裂。 -->
    <SupplementActorHero :actor="null">
      <template #meters>
        <div class="job-stat"><b>{{ moviesTotalCount }}</b><span>待补全作品</span></div>
        <div class="job-stat"><b>{{ detailTargetCount }}</b><span>可补详情</span></div>
        <div class="job-stat"><b>{{ pendingCandidateCount }}</b><span>候选待定</span></div>
      </template>
    </SupplementActorHero>

    <!-- 搜索撑满整行；匹配状态 / 质量 收进右侧「筛选」下拉（与作品目录、候选页一致），
         不再在前面平铺两个独立下拉。 -->
    <div class="cat-toolbar">
      <label class="cat-search">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" aria-hidden="true">
          <circle cx="11" cy="11" r="7"></circle><path d="M21 21l-4.3-4.3"></path>
        </svg>
        <input
          v-model="movieFilters.q"
          type="search"
          placeholder="搜索番号或片名"
          aria-label="搜索番号或片名"
          @keyup.enter="$emit('apply-filters')"
        />
        <button v-if="movieFilters.q" type="button" class="cat-search-clear" aria-label="清除搜索" @click="clearSearch">×</button>
      </label>

      <div ref="filterRoot" class="cat-filter">
        <button
          type="button" class="filter-trigger"
          :class="{ on: filterOpen, active: activeFilterCount > 0 }"
          :aria-expanded="filterOpen" @click="filterOpen = !filterOpen"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true">
            <path d="M3 6h11M3 12h7M3 18h13" /><circle cx="17.5" cy="6" r="2.2" /><circle cx="13.5" cy="12" r="2.2" /><circle cx="19" cy="18" r="2.2" />
          </svg>
          <span>筛选</span>
          <span v-if="activeFilterCount" class="ft-count">{{ activeFilterCount }}</span>
          <svg class="ft-chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><polyline points="6 9 12 15 18 9" /></svg>
        </button>

        <transition name="fp">
          <div v-if="filterOpen" class="filter-panel" role="dialog" aria-label="待补全筛选">
            <div class="fp-row">
              <span class="fp-label">匹配</span>
              <div class="stage-seg fp-seg" role="group" aria-label="匹配状态筛选">
                <button
                  v-for="opt in matchFilterOptions" :key="String(opt.value)" type="button"
                  :class="{ active: movieFilters.matched === opt.value }" @click="setMatched(opt.value)"
                >{{ opt.label }}</button>
              </div>
            </div>
            <div class="fp-row">
              <span class="fp-label">质量</span>
              <GlassSelect
                v-model="movieFilters.quality"
                :options="qualityFilterOptions"
                size="compact"
                placement="right"
                aria-label="影片质量筛选"
                @change="$emit('apply-filters')"
              />
            </div>
            <div class="fp-foot">
              <span class="fp-count">共 {{ moviesTotalCount }} 部</span>
              <button v-if="activeFilterCount" type="button" class="fp-clear" @click="$emit('clear-filters')">清除筛选</button>
            </div>
          </div>
        </transition>
      </div>
    </div>

    <AppleSkeleton
      v-if="moviesLoading"
      class="panel-state"
      variant="list"
      :items="6"
      label="待补全作品加载中"
    />

    <AppleEmptyState
      v-else-if="!supplementMovies.length"
      class="panel-state"
      title="暂无待补全作品"
      :description="emptyDescription"
      :next-step="emptyNextStep"
      action-label="刷新"
      secondary-action-label="清除筛选"
      density="compact"
      @action="$emit('refresh')"
      @secondary-action="$emit('clear-filters')"
    />

    <div v-else class="field-list">
      <div
        v-for="movie in supplementMovies"
        :key="movie.id"
        class="cand-card"
        :class="{ dim: isComplete(movie) }"
      >
        <div class="cc-poster" @click="$emit('open-sources', movie)">
          <img
            v-if="movieCover(movie)"
            :src="movieCover(movie)"
            :alt="codeOf(movie)"
            loading="lazy"
            decoding="async"
            referrerpolicy="no-referrer"
            @error="applyImageFallback($event)"
          />
          <div v-else class="cc-poster-placeholder">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="m3 16 5-5 4 4 3-3 6 6"/></svg>
          </div>
          <div class="cc-scrim"></div>
          <span class="cc-code">{{ codeOf(movie) }}</span>
        </div>

        <div class="cc-main">
          <div class="cc-srcline">
            <span class="src-pill" :class="`m-${movieMatchClass(movie)}`">{{ movieMatchLabel(movie) }}</span>
            <span class="cc-tag">{{ gapText(movie) }}</span>
          </div>
          <div class="cc-title" :title="movie.title || ''">{{ movie.title || codeOf(movie) }}</div>
          <div class="cc-orig">
            <template v-if="movie.release_date">{{ String(movie.release_date).slice(0, 7) }} · </template>
            <span class="why-link" @click="$emit('open-sources', movie)">{{ isComplete(movie) ? '诊断与字段来源' : '看缺什么字段' }}</span>
          </div>
        </div>

        <div class="cc-decide">
          <div class="trail-act">
            <button
              v-if="canEnrich(movie)"
              class="btn btn-primary"
              type="button"
              :disabled="enrichingMovies[movie.id]"
              @click="$emit('enrich', movie)"
            >{{ enrichingMovies[movie.id] ? '排队中…' : '补详情' }}</button>
            <span v-else-if="isComplete(movie)" class="trail-done">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>
            </span>
          </div>
          <button type="button" class="cc-dots" aria-label="诊断与字段来源" @click="$emit('open-sources', movie)">⋯</button>
        </div>
      </div>
    </div>

    <div v-if="moviesTotalPages > 1" class="catalog-pager">
      <button class="page-btn" type="button" :disabled="moviePage <= 1" @click="$emit('go-page', moviePage - 1)">上一页</button>
      <span class="page-indicator">{{ moviePage }} / {{ moviesTotalPages }}</span>
      <button class="page-btn" type="button" :disabled="moviePage >= moviesTotalPages" @click="$emit('go-page', moviePage + 1)">下一页</button>
    </div>
  </section>
</template>

<script>
import GlassSelect from '../../components/GlassSelect.vue'
import AppleEmptyState from '../../components/AppleEmptyState.vue'
import AppleSkeleton from '../../components/AppleSkeleton.vue'
import SupplementActorHero from './SupplementActorHero.vue'

export default {
  name: 'SupplementMoviesPanel',
  components: { GlassSelect, AppleEmptyState, AppleSkeleton, SupplementActorHero },
  props: {
    movieFilters: { type: Object, required: true },
    matchFilterOptions: { type: Array, default: () => [] },
    qualityFilterOptions: { type: Array, default: () => [] },
    moviesLoading: { type: Boolean, default: false },
    supplementMovies: { type: Array, default: () => [] },
    moviesTotalCount: { type: Number, default: 0 },
    moviesTotalPages: { type: Number, default: 1 },
    moviePage: { type: Number, default: 1 },
    detailTargetCount: { type: Number, default: 0 },
    pendingCandidateCount: { type: Number, default: 0 },
    batchEnriching: { type: Boolean, default: false },
    candidateImporting: { type: Boolean, default: false },
    enrichingMovies: { type: Object, default: () => ({}) },
    applyImageFallback: { type: Function, required: true },
    movieCover: { type: Function, required: true },
    movieFieldChips: { type: Function, required: true },
    movieMatchClass: { type: Function, required: true },
    movieMatchLabel: { type: Function, required: true },
  },
  emits: ['apply-filters', 'batch-enrich', 'create-candidates', 'enrich', 'open-sources', 'go-page', 'refresh', 'clear-filters', 'pick-actor'],
  data() {
    return {
      filterOpen: false,
      // 仅当父级菜单行的 Teleport 目标存在时才传送（隔离单测/无父级时就地渲染）。
      canTeleport: typeof document !== 'undefined' && !!document.getElementById('supplement-tab-actions'),
    }
  },
  computed: {
    hasActiveFilters() {
      return Boolean(this.movieFilters.q || this.movieFilters.quality || this.movieFilters.matched !== null)
    },
    // 「筛选」徽标只数下拉里的维度（匹配状态 / 质量）；搜索是独立输入，不计入。
    // 匹配状态默认落在「未匹配(false)」这一待补全视角，全部(null) 视为未设。
    activeFilterCount() {
      return [this.movieFilters.matched !== null, this.movieFilters.quality !== ''].filter(Boolean).length
    },
    emptyDescription() {
      return this.hasActiveFilters ? '当前筛选下没有待补全作品。' : '补全来源还没有写入作品字段。'
    },
    emptyNextStep() {
      return this.hasActiveFilters
        ? '清除筛选可以回到全部待补全作品；也可以刷新确认最新补全结果。'
        : '先刷新列表，或选一位演员启动一次作品补全任务。'
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
    setMatched(value) {
      this.movieFilters.matched = value
      this.$emit('apply-filters')
    },
    clearSearch() {
      this.movieFilters.q = ''
      this.$emit('apply-filters')
    },
    // 下拉外点 / Esc 收起；GlassSelect 的浮层挂在 body 外，点它不算外点。
    onDocPointer(event) {
      const root = this.$refs.filterRoot
      if (!root) return
      if (root.contains(event.target) || (event.target.closest && event.target.closest('.glass-select__menu'))) return
      this.filterOpen = false
    },
    onKeydown(event) {
      if (event.key === 'Escape') this.filterOpen = false
    },
    codeOf(movie) {
      return movie.dvd_id || movie.canonical_number || movie.display_number || '—'
    },
    isComplete(movie) {
      return this.movieFieldChips(movie).every(chip => Boolean(chip.value))
    },
    canEnrich(movie) {
      return Boolean(movie.source_movie_id) && !this.isComplete(movie)
    },
    gapText(movie) {
      const miss = this.movieFieldChips(movie).filter(chip => !chip.value).map(chip => chip.label)
      if (!miss.length) return '字段已齐'
      return `缺 ${miss.slice(0, 3).join(' · ')}`
    },
  },
}
</script>

<style scoped src="./actressCatalogPanel.css"></style>
<style scoped src="./supplementHero.css"></style>
<style scoped>
/* match-state tint for the src-pill (catalog uses it for origin; here for 匹配状态) */
.src-pill.m-matched { background: rgba(var(--ok-rgb), 0.16); color: var(--ok); border-color: transparent; }
.src-pill.m-candidate { background: rgba(var(--warn-rgb), 0.16); color: var(--warn); border-color: transparent; }
.src-pill.m-ignored { color: var(--text-muted); }
</style>

<template>
  <!-- 全库「全部待补全」聚合视图 — 复用作品目录(catalog)卡片设计，去掉演员 hero。
       数据来自全库 supplement movies；按字段缺口呈现，保留筛选 / 批量动作 / 分页。 -->
  <section class="catalog-panel">
    <div class="all-pending-head">
      <div class="aph-id">
        <h2>全部待补全</h2>
        <div class="sh-sub">全库字段缺口 · 共 {{ moviesTotalCount }} 部待补全作品</div>
      </div>
      <div class="aph-actions">
        <button class="btn btn-primary" type="button" :disabled="batchEnriching" @click="$emit('batch-enrich')">
          {{ batchEnriching ? '批量排队中…' : '批量补详情' }}
        </button>
        <button class="btn btn-ghost btn-sm" type="button" :disabled="candidateImporting" @click="$emit('create-candidates')">
          {{ candidateImporting ? '生成中…' : '生成下载候选' }}
        </button>
        <button class="btn btn-ghost btn-sm" type="button" @click="$emit('pick-actor')">选择演员</button>
      </div>
    </div>

    <div class="catalog-toolbar">
      <GlassSelect
        v-model="movieFilters.matched"
        :options="matchFilterOptions"
        size="compact"
        aria-label="影片匹配状态"
        @change="$emit('apply-filters')"
      />
      <GlassSelect
        v-model="movieFilters.quality"
        :options="qualityFilterOptions"
        size="compact"
        aria-label="影片质量筛选"
        @change="$emit('apply-filters')"
      />
      <label class="catalog-search">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
          <circle cx="11" cy="11" r="7"></circle><path d="M16.5 16.5 21 21"></path>
        </svg>
        <input
          v-model="movieFilters.q"
          type="search"
          placeholder="搜索番号或片名"
          aria-label="搜索番号或片名"
          @keyup.enter="$emit('apply-filters')"
        />
      </label>
      <button class="btn btn-ghost btn-sm" type="button" @click="$emit('apply-filters')">筛选</button>
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

export default {
  name: 'SupplementMoviesPanel',
  components: { GlassSelect, AppleEmptyState, AppleSkeleton },
  props: {
    movieFilters: { type: Object, required: true },
    matchFilterOptions: { type: Array, default: () => [] },
    qualityFilterOptions: { type: Array, default: () => [] },
    moviesLoading: { type: Boolean, default: false },
    supplementMovies: { type: Array, default: () => [] },
    moviesTotalCount: { type: Number, default: 0 },
    moviesTotalPages: { type: Number, default: 1 },
    moviePage: { type: Number, default: 1 },
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
  computed: {
    hasActiveFilters() {
      return Boolean(this.movieFilters.q || this.movieFilters.quality || this.movieFilters.matched !== null)
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
  methods: {
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
<style scoped>
.all-pending-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-4);
  flex-wrap: wrap;
  margin-bottom: var(--space-5);
}

.aph-id h2 {
  margin: 0;
  font-size: var(--type-title-1);
  font-weight: var(--type-title-1-weight);
  letter-spacing: var(--type-title-1-tracking);
  color: var(--text-primary);
}

.aph-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
  flex-wrap: wrap;
}

/* match-state tint for the src-pill (catalog uses it for origin; here for 匹配状态) */
.src-pill.m-matched { background: rgba(var(--ok-rgb), 0.16); color: var(--ok); border-color: transparent; }
.src-pill.m-candidate { background: rgba(var(--warn-rgb), 0.16); color: var(--warn); border-color: transparent; }
.src-pill.m-ignored { color: var(--text-muted); }
</style>

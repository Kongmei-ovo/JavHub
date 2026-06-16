<template>
  <section class="workspace-panel">
    <div class="panel-header">
      <div>
        <h2>待补全作品</h2>
        <p class="panel-subtitle">全库字段缺口对齐补全来源 · 补详情 / 诊断走右侧抽屉</p>
      </div>
      <div class="movies-panel-toolbar">
        <button class="btn btn-primary btn-sm" type="button" :disabled="batchEnriching" @click="$emit('batch-enrich')">
          {{ batchEnriching ? '批量排队中...' : '批量补详情' }}
        </button>
        <button class="btn btn-ghost btn-sm" type="button" :disabled="candidateImporting" @click="$emit('create-candidates')">
          {{ candidateImporting ? '生成中...' : '生成下载候选' }}
        </button>
      </div>
    </div>

    <div class="filter-bar">
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
      <input
        v-model="movieFilters.q"
        placeholder="番号 / 标题"
        class="filter-input"
        @keyup.enter="$emit('apply-filters')"
      />
      <button class="btn btn-ghost btn-sm" type="button" @click="$emit('apply-filters')">筛选</button>
    </div>

    <div v-if="!moviesLoading && supplementMovies.length" class="movie-field-ledger" aria-label="当前页字段缺口">
      <div class="ledger-summary">
        <strong>{{ movieFieldSummaryTotalMissing }}</strong>
        <span>当前页字段缺口</span>
      </div>
      <div class="ledger-chips">
        <span
          v-for="row in movieFieldSummaryRows"
          :key="row.key"
          class="ledger-chip"
          :class="{ clear: row.missing === 0 }"
        >
          <b>{{ row.label }}</b>
          <em>{{ row.missing ? `${row.missing} 个缺口` : '已齐' }}</em>
        </span>
      </div>
    </div>

    <AppleSkeleton
      v-if="moviesLoading"
      class="panel-state"
      variant="list"
      :items="5"
      label="补全影片加载中"
    />
    <div v-else class="field-card-list">
      <article v-for="movie in supplementMovies" :key="movie.id" class="field-card">
        <div class="fc-poster" @click="$emit('open-sources', movie)">
          <img
            v-if="movieCover(movie)"
            :src="movieCover(movie)"
            loading="lazy"
            decoding="async"
            referrerpolicy="no-referrer"
            alt=""
            @error="applyImageFallback($event)"
          />
          <div v-else class="fc-poster-empty">无封面</div>
          <div class="fc-scrim"></div>
          <span class="fc-code">{{ movie.dvd_id || movie.canonical_number || '—' }}</span>
        </div>
        <div class="fc-main">
          <h3 class="fc-title" :title="movie.title">{{ movie.title || movie.dvd_id || movie.canonical_number || '—' }}</h3>
          <div class="fc-meta">
            <span>{{ movie.release_date || '日期未知' }}</span>
            <span v-if="movie.runtime_mins">· {{ movie.runtime_mins }} 分钟</span>
            <span v-if="movie.maker_name">· {{ movie.maker_name }}</span>
            <span v-if="movieCategories(movie)" class="fc-cats">· {{ movieCategories(movie) }}</span>
          </div>
          <div class="fc-fieldgrid" aria-label="影片字段完整度">
            <span
              v-for="chip in movieFieldChips(movie)"
              :key="chip.key"
              class="field-chip"
              :class="{ miss: !chip.value }"
            >
              <b>{{ chip.label }}</b>
              <em>{{ chip.value || '缺失' }}</em>
            </span>
          </div>
        </div>
        <div class="fc-act">
          <span class="status-pill match" :class="`match-${movieMatchClass(movie)}`">{{ movieMatchLabel(movie) }}</span>
          <button
            v-if="movie.source_movie_id && !movieIsFieldComplete(movie)"
            class="btn btn-primary btn-sm fc-act-btn"
            type="button"
            :disabled="enrichingMovies[movie.id]"
            @click="$emit('enrich', movie)"
          >{{ enrichingMovies[movie.id] ? '排队中...' : '补详情' }}</button>
          <span v-else-if="movieIsFieldComplete(movie)" class="fc-ready">字段已齐</span>
          <button class="btn btn-ghost btn-sm fc-act-btn" type="button" @click="$emit('open-sources', movie)">诊断</button>
        </div>
      </article>
      <AppleEmptyState
        v-if="!supplementMovies.length"
        class="panel-state empty-inline"
        title="暂无补全影片"
        :description="emptyDescription"
        :next-step="emptyNextStep"
        action-label="刷新影片"
        secondary-action-label="清除筛选"
        density="compact"
        @action="$emit('refresh')"
        @secondary-action="$emit('clear-filters')"
      />
    </div>

    <div v-if="moviesTotalPages > 1" class="pagination">
      <button class="btn btn-ghost btn-sm" :disabled="moviePage <= 1" @click="$emit('go-page', moviePage - 1)">上一页</button>
      <span>{{ moviePage }} / {{ moviesTotalPages }}</span>
      <button class="btn btn-ghost btn-sm" :disabled="moviePage >= moviesTotalPages" @click="$emit('go-page', moviePage + 1)">下一页</button>
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
    moviesTotalPages: { type: Number, default: 1 },
    moviePage: { type: Number, default: 1 },
    batchEnriching: { type: Boolean, default: false },
    candidateImporting: { type: Boolean, default: false },
    enrichingMovies: { type: Object, default: () => ({}) },
    applyImageFallback: { type: Function, required: true },
    movieCover: { type: Function, required: true },
    movieCategories: { type: Function, required: true },
    movieMatchClass: { type: Function, required: true },
    movieMatchLabel: { type: Function, required: true },
  },
  emits: ['apply-filters', 'batch-enrich', 'create-candidates', 'enrich', 'open-sources', 'go-page', 'refresh', 'clear-filters'],
  computed: {
    hasActiveFilters() {
      return Boolean(this.movieFilters.q || this.movieFilters.quality || this.movieFilters.matched !== null)
    },
    emptyDescription() {
      return this.hasActiveFilters ? '当前筛选下没有可补全影片。' : '补全来源还没有写入作品字段。'
    },
    emptyNextStep() {
      return this.hasActiveFilters
        ? '清除筛选可以回到全部补全影片；也可以刷新确认最新补全结果。'
        : '先刷新影片列表，或回到演员工作台启动一次作品补全任务。'
    },
    movieFieldSummaryRows() {
      const rows = this.movieFieldChips({}).map(chip => ({ key: chip.key, label: chip.label, missing: 0 }))
      const map = new Map(rows.map(r => [r.key, r]))
      this.supplementMovies.forEach(movie => {
        this.movieFieldChips(movie).forEach(chip => { if (!chip.value) map.get(chip.key).missing += 1 })
      })
      return rows
    },
    movieFieldSummaryTotalMissing() {
      return this.movieFieldSummaryRows.reduce((sum, row) => sum + row.missing, 0)
    },
  },
  methods: {
    movieFieldChips(movie) {
      return [
        { key: 'cover', label: '封面', value: this.movieCover(movie) ? '已取' : '' },
        { key: 'runtime', label: '时长', value: movie.runtime_mins ? `${movie.runtime_mins}m` : '' },
        { key: 'maker', label: '厂商', value: movie.maker_name || '' },
        { key: 'label', label: '厂牌', value: movie.label_name || '' },
        { key: 'series', label: '系列', value: movie.series_name || '' },
        { key: 'category', label: '分类', value: this.movieCategories(movie) || '' },
      ]
    },
    movieIsFieldComplete(movie) {
      return this.movieFieldChips(movie).every(chip => Boolean(chip.value))
    },
  },
}
</script>

<style scoped src="./supplementPanel.css"></style>
<style scoped src="./supplementMoviesPanel.css"></style>
<style scoped src="./supplementMovieRepair.css"></style>

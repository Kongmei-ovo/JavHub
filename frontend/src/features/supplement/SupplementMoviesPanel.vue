<template>
  <section class="workspace-panel apple-surface">
    <div class="panel-header">
      <div>
        <h2>作品字段</h2>
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
        placeholder="搜索番号/标题"
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
    <div v-if="!moviesLoading && supplementMovies.length" class="movie-field-priority-strip" aria-label="字段优先级">
      <span
        v-for="row in movieFieldPriorityRows"
        :key="row.key"
        class="field-priority-chip"
        :class="fieldPriorityClass(row)"
      >
        <b>{{ row.label }}</b>
        <em>{{ row.missing ? `${row.missing} 个缺口` : '已齐' }}</em>
        <small>{{ row.action }}</small>
      </span>
    </div>
    <div v-if="!moviesLoading && supplementMovies.length" class="movie-field-triage-board" aria-label="字段分拣台">
      <div class="field-triage-summary">
        <strong>{{ movieFieldTriageTotal }}</strong>
        <span>字段分拣</span>
      </div>
      <div class="field-triage-grid">
        <span
          v-for="lane in movieFieldTriageLanes"
          :key="lane.key"
          class="field-triage-card"
          :class="fieldTriageLaneClass(lane)"
        >
          <b>{{ lane.label }}</b>
          <em>{{ lane.count }} 项</em>
          <small>{{ lane.action }}</small>
          <i>{{ lane.samples.length ? lane.samples.join(' · ') : lane.empty }}</i>
        </span>
      </div>
    </div>
    <div v-if="!moviesLoading && supplementMovies.length" class="movie-repair-queue" aria-label="当前页修复队列">
      <div class="repair-queue-summary">
        <strong>{{ movieRepairQueueTotal }}</strong>
        <span>当前页修复队列</span>
      </div>
      <div class="repair-queue-cards">
        <span
          v-for="row in movieRepairQueueRows"
          :key="row.key"
          class="repair-queue-card"
          :class="repairQueueCardClass(row)"
        >
          <b>{{ row.label }}</b>
          <em>{{ row.count }} 项</em>
          <small>{{ row.hint }}</small>
        </span>
      </div>
    </div>
    <div v-if="!moviesLoading && supplementMovies.length" class="movie-repair-flow" aria-label="当前页处理线">
      <span
        v-for="step in movieRepairFlowSteps"
        :key="step.key"
        class="repair-flow-step"
        :class="flowStepClass(step)"
      >
        <b>{{ step.label }}</b>
        <em>{{ step.count }} 项</em>
        <small>{{ step.action }}</small>
      </span>
    </div>
    <AppleSkeleton
      v-if="moviesLoading"
      class="panel-state"
      variant="list"
      :items="5"
      label="补全影片加载中"
    />
    <div v-else class="ios-list">
      <article v-for="movie in supplementMovies" :key="movie.id" class="ios-row movie-row">
        <img
          v-if="movieCover(movie)"
          :src="movieCover(movie)"
          class="movie-cover"
          loading="lazy"
          decoding="async"
          referrerpolicy="no-referrer"
          alt=""
          @error="applyImageFallback($event)"
        />
        <div v-else class="movie-cover movie-cover-empty">无封面</div>
        <div class="movie-row-main">
          <strong>{{ movie.dvd_id || movie.canonical_number || '—' }}</strong>
          <span>{{ movie.title || movie.dvd_id || movie.canonical_number || '—' }}</span>
          <small>{{ movie.release_date || '未知日期' }}</small>
          <div class="movie-meta">
            <span v-if="movie.runtime_mins">{{ movie.runtime_mins }} 分钟</span>
            <span v-if="movie.maker_name">{{ movie.maker_name }}</span>
            <span v-if="movieCategories(movie)" class="movie-meta-cats">{{ movieCategories(movie) }}</span>
          </div>
          <template v-for="summary in [movieFieldRepairSummary(movie)]" :key="`${movie.id}-field-repair-summary`">
            <div class="movie-field-repair-summary" :class="fieldRepairSummaryClass(summary)" aria-label="影片字段修复摘要">
              <span class="field-repair-priority">
                <b>{{ summary.label }}</b>
                <em>{{ summary.primary }}</em>
              </span>
              <span class="field-repair-status">
                <b>{{ summary.countLabel }}</b>
                <em>{{ summary.sourceLabel }}</em>
              </span>
            </div>
          </template>
          <div v-if="movieFieldWorkOrders(movie).length" class="movie-field-work-orders" aria-label="字段修复工单">
            <span
              v-for="order in movieFieldWorkOrders(movie)"
              :key="order.key"
              class="field-work-order-chip"
              :class="fieldWorkOrderClass(order)"
            >
              <b>{{ order.label }}</b>
              <em>{{ order.status }}</em>
              <small>{{ order.action }}</small>
            </span>
          </div>
          <div class="movie-field-grid" aria-label="影片字段完整度">
            <span
              v-for="chip in movieFieldChips(movie)"
              :key="chip.key"
              class="field-chip"
              :class="fieldChipClass(chip)"
            >
              <b>{{ chip.label }}</b>
              <em>{{ chip.value || '缺失' }}</em>
            </span>
          </div>
          <div class="movie-repair-stage-grid" aria-label="影片修复阶段">
            <span
              v-for="stage in movieRepairStages(movie)"
              :key="stage.key"
              class="repair-stage-chip"
              :class="repairStageClass(stage)"
            >
              <b>{{ stage.label }}</b>
              <em>{{ stage.status }}</em>
            </span>
          </div>
          <div class="movie-repair-flags">
            <span v-for="flag in movieRepairFlags(movie)" :key="flag">{{ flag }}</span>
          </div>
        </div>
        <div class="movie-row-actions">
          <span class="status-pill" :class="`match-${movieMatchClass(movie)}`">{{ movieMatchLabel(movie) }}</span>
          <button
            v-if="movie.source_movie_id"
            class="btn btn-primary btn-sm"
            type="button"
            :disabled="enrichingMovies[movie.id]"
            @click="$emit('enrich', movie)"
          >{{ enrichingMovies[movie.id] ? '排队中...' : '补详情' }}</button>
          <button class="btn btn-ghost btn-sm" type="button" @click="$emit('open-sources', movie)">诊断</button>
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
  emits: [
    'apply-filters',
    'batch-enrich',
    'create-candidates',
    'enrich',
    'open-sources',
    'go-page',
    'refresh',
    'clear-filters',
  ],
  computed: {
    hasActiveFilters() {
      return Boolean(
        this.movieFilters.q ||
        this.movieFilters.quality ||
        this.movieFilters.matched !== null
      )
    },
    emptyDescription() {
      return this.hasActiveFilters
        ? '当前筛选下没有可补全影片。'
        : '补全来源还没有写入作品字段。'
    },
    emptyNextStep() {
      return this.hasActiveFilters
        ? '清除筛选可以回到全部补全影片；也可以刷新确认最新补全结果。'
        : '先刷新影片列表，或回到演员工作台启动一次作品补全任务。'
    },
    movieFieldSummaryRows() {
      const rows = this.movieFieldChips({}).map(chip => ({
        key: chip.key,
        label: chip.label,
        missingLabel: chip.missingLabel,
        missing: 0,
      }))
      const rowMap = new Map(rows.map(row => [row.key, row]))
      this.supplementMovies.forEach(movie => {
        this.movieFieldChips(movie).forEach(chip => {
          if (!chip.value) rowMap.get(chip.key).missing += 1
        })
      })
      return rows
    },
    movieFieldSummaryTotalMissing() {
      return this.movieFieldSummaryRows.reduce((total, row) => total + row.missing, 0)
    },
    movieFieldPriorityRows() {
      return [...this.movieFieldSummaryRows]
        .sort((a, b) => b.missing - a.missing)
        .slice(0, 3)
        .map(row => ({
          ...row,
          action: row.missing ? (['cover', 'runtime', 'maker'].includes(row.key) ? '优先补详情' : '打开诊断确认来源') : '字段已齐',
        }))
    },
    movieFieldTriageLanes() {
      const lanes = [
        {
          key: 'ready',
          label: '可补详情',
          count: this.supplementMovies.filter(movie => this.movieNeedsDetail(movie)).length,
          action: '打开详情补抓',
          empty: '暂无可补字段',
        },
        {
          key: 'diagnose',
          label: '需诊断',
          count: this.supplementMovies.filter(movie => this.movieMissingFieldChips(movie).length && !movie.source_movie_id && this.movieMatchClass(movie) === 'candidate').length,
          action: '先确认来源',
          empty: '暂无诊断项',
        },
        {
          key: 'waiting',
          label: '等待来源',
          count: this.supplementMovies.filter(movie => this.movieMissingFieldChips(movie).length && !movie.source_movie_id && this.movieMatchClass(movie) !== 'candidate').length,
          action: '等待匹配',
          empty: '暂无等待项',
        },
        {
          key: 'complete',
          label: '字段已齐',
          count: this.supplementMovies.filter(movie => this.movieIsFieldComplete(movie)).length,
          action: '可生成候选',
          empty: '暂无完整项',
        },
      ]
      return lanes.map(lane => ({
        ...lane,
        samples: this.movieFieldTriageSamples(lane.key),
      }))
    },
    movieFieldTriageTotal() {
      return this.movieFieldTriageLanes.reduce((total, lane) => total + lane.count, 0)
    },
    movieRepairQueueRows() {
      const pendingMatches = this.supplementMovies.filter(movie => this.movieMatchClass(movie) === 'candidate')
      const detailTargets = this.supplementMovies.filter(movie => this.movieNeedsDetail(movie))
      const completeMovies = this.supplementMovies.filter(movie => this.movieIsFieldComplete(movie))
      return [
        { key: 'pending-match', label: '待确认', count: pendingMatches.length, hint: '候选需要人工判定' },
        { key: 'needs-detail', label: '需补详情', count: detailTargets.length, hint: '字段缺口可继续抓取' },
        { key: 'field-complete', label: '字段已齐', count: completeMovies.length, hint: '可进入下载候选' },
      ]
    },
    movieRepairQueueTotal() {
      return this.movieRepairQueueRows.reduce((total, row) => total + row.count, 0)
    },
    movieRepairFlowSteps() {
      const rows = new Map(this.movieRepairQueueRows.map(row => [row.key, row]))
      return [
        { key: 'confirm', label: '确认匹配', count: rows.get('pending-match')?.count || 0, action: '先确认候选' },
        { key: 'detail', label: '补字段', count: rows.get('needs-detail')?.count || 0, action: '批量补字段' },
        { key: 'candidate', label: '生成候选', count: rows.get('field-complete')?.count || 0, action: '生成候选包' },
      ]
    },
  },
  methods: {
    movieFieldChips(movie) {
      return [
        { key: 'cover', label: '封面', missingLabel: '缺封面', value: this.movieCover(movie) ? '已取' : '', important: true },
        { key: 'runtime', label: '时长', missingLabel: '缺时长', value: movie.runtime_mins ? `${movie.runtime_mins}m` : '', important: true },
        { key: 'maker', label: '厂商', missingLabel: '缺厂商', value: movie.maker_name || '' },
        { key: 'label', label: '厂牌', missingLabel: '缺厂牌', value: movie.label_name || '' },
        { key: 'series', label: '系列', missingLabel: '缺系列', value: movie.series_name || '' },
        { key: 'category', label: '分类', missingLabel: '缺分类', value: this.movieCategories(movie) || '' },
      ]
    },
    fieldChipClass(chip) {
      return {
        missing: !chip.value,
        important: chip.important,
      }
    },
    movieMissingFieldChips(movie) {
      return this.movieFieldChips(movie).filter(chip => !chip.value)
    },
    movieFieldWorkOrders(movie) {
      return this.movieMissingFieldChips(movie).map(chip => ({
        key: chip.key,
        label: chip.label,
        status: chip.missingLabel,
        action: this.fieldWorkOrderAction(chip, movie),
        sourceReady: Boolean(movie.source_movie_id),
      }))
    },
    fieldWorkOrderAction(chip, movie) {
      if (movie.source_movie_id) return '补详情可修'
      if (this.movieMatchClass(movie) === 'candidate') return '打开诊断'
      return '等待来源'
    },
    fieldWorkOrderClass(order) {
      return {
        ready: order.sourceReady,
        missing: !order.sourceReady,
      }
    },
    movieFieldTriageSamples(laneKey) {
      return this.supplementMovies
        .filter(movie => {
          const missing = this.movieMissingFieldChips(movie).length
          if (laneKey === 'ready') return this.movieNeedsDetail(movie)
          if (laneKey === 'diagnose') return missing && !movie.source_movie_id && this.movieMatchClass(movie) === 'candidate'
          if (laneKey === 'waiting') return missing && !movie.source_movie_id && this.movieMatchClass(movie) !== 'candidate'
          return this.movieIsFieldComplete(movie)
        })
        .map(movie => movie.dvd_id || movie.canonical_number || '未命名')
        .slice(0, 2)
    },
    fieldTriageLaneClass(lane) {
      return {
        ready: lane.key === 'ready' && lane.count > 0,
        diagnose: lane.key === 'diagnose' && lane.count > 0,
        waiting: lane.key === 'waiting' && lane.count > 0,
        complete: lane.key === 'complete' && lane.count > 0,
        empty: lane.count === 0,
      }
    },
    movieFieldRepairSummary(movie) {
      const missing = this.movieMissingFieldChips(movie)
      const sourceReady = Boolean(movie.source_movie_id)
      if (!missing.length) {
        return {
          label: '字段齐全',
          primary: '可进入候选生成',
          countLabel: '0 个缺口',
          sourceLabel: sourceReady ? '详情源可用' : '等待详情源',
          complete: true,
          sourceReady: Boolean(movie.source_movie_id),
        }
      }
      return {
        label: '优先修复',
        primary: missing.slice(0, 3).map(chip => chip.missingLabel).join(' · '),
        countLabel: `${missing.length} 个缺口`,
        sourceLabel: sourceReady ? '详情源可用' : '等待详情源',
        complete: false,
        sourceReady: Boolean(movie.source_movie_id),
      }
    },
    fieldRepairSummaryClass(summary) {
      return {
        ready: summary.sourceReady && !summary.complete,
        complete: summary.complete,
      }
    },
    movieNeedsDetail(movie) {
      return Boolean(movie.source_movie_id) && !this.movieIsFieldComplete(movie)
    },
    movieIsFieldComplete(movie) {
      return this.movieFieldChips(movie).every(chip => Boolean(chip.value))
    },
    movieRepairStages(movie) {
      const matchState = this.movieMatchClass(movie)
      return [
        { key: 'match', label: '确认匹配', status: matchState === 'candidate' ? '待确认' : (matchState === 'matched' ? '已完成' : '可跳过'), current: matchState === 'candidate', ready: matchState === 'matched' },
        { key: 'detail', label: '补详情', status: this.movieNeedsDetail(movie) ? '可补字段' : '字段已齐', current: this.movieNeedsDetail(movie), ready: this.movieIsFieldComplete(movie) },
        { key: 'candidate', label: '生成候选', status: this.movieIsFieldComplete(movie) && matchState !== 'ignored' ? '可生成' : '待补齐', current: this.movieIsFieldComplete(movie) && matchState !== 'ignored', missing: !this.movieIsFieldComplete(movie) },
      ]
    },
    repairStageClass(stage) {
      return {
        current: stage.current,
        ready: stage.ready,
        missing: stage.missing,
      }
    },
    repairQueueCardClass(row) {
      return {
        ready: row.key === 'field-complete',
        empty: row.count === 0,
      }
    },
    fieldPriorityClass(row) {
      return {
        ready: row.missing > 0,
        clear: row.missing === 0,
      }
    },
    flowStepClass(step) {
      return {
        ready: step.count > 0,
        empty: step.count === 0,
      }
    },
    movieRepairFlags(movie) {
      const flags = this.movieFieldChips(movie).filter(chip => !chip.value).map(chip => chip.missingLabel)
      if (!flags.length) flags.push('字段完整')
      return flags
    },
  },
}
</script>

<style scoped src="./supplementMoviesPanel.css"></style>
<style scoped src="./supplementMovieRepair.css"></style>

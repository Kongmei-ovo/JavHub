<template>
  <section class="workspace-panel apple-surface">
    <div class="panel-header">
      <div>
        <h2>来源诊断</h2>
      </div>
    </div>
    <div v-if="sourceDiagnosticsOpen" class="diagnostics-inline-state">
      <span class="status-pill" :class="sourceDiagnosticsLoading ? 'status-running' : 'status-succeeded'">
        {{ sourceDiagnosticsLoading ? '读取中' : '已载入' }}
      </span>
      <div>
        <h3>正在查看诊断：{{ diagnosticsMovieTitle }}</h3>
        <p>{{ diagnosticsMovieSubtitle || '字段来源、匹配候选和人工校正记录已在弹窗中展开。' }}</p>
      </div>
    </div>
    <div v-else class="diagnostics-launchpad">
      <div class="diagnostics-launchpad-grid" aria-label="来源诊断待办概览">
        <button v-for="row in diagnosticsLaunchpadRows" :key="row.key" type="button" class="diagnostics-launchpad-card" @click="emit('movies-requested')">
          <strong>{{ row.value }}</strong>
          <span>{{ row.label }}</span>
          <small>{{ row.hint }}</small>
        </button>
      </div>
      <div class="diagnostics-focus-movie">
        <div>
          <span class="status-pill">诊断入口</span>
          <h3>{{ diagnosticsFocusMovie?.dvd_id || diagnosticsFocusMovie?.canonical_number || '等待影片数据' }}</h3>
          <p>{{ diagnosticsFocusMovie?.title || '先在作品字段列表中载入补全影片，再打开字段来源和候选诊断。' }}</p>
        </div>
        <div class="diagnostics-focus-badges">
          <span v-for="badge in diagnosticsFocusMovieBadges" :key="badge">{{ badge }}</span>
        </div>
        <div class="diagnostics-focus-actions">
          <button class="btn btn-primary btn-sm" type="button" :disabled="!diagnosticsFocusMovie" @click="openDiagnosticsFocusMovie">打开首个待诊断影片</button>
          <button class="btn btn-ghost btn-sm" type="button" @click="emit('movies-requested')">回到作品字段</button>
        </div>
      </div>
    </div>
    <SupplementSourceDiagnosticsDialog
      v-if="sourceDiagnosticsOpen"
      v-model:manual-content-id="manualContentId"
      :source-diagnostics-loading="sourceDiagnosticsLoading"
      :source-diagnostics="sourceDiagnostics"
      :diagnostics-movie-title="diagnosticsMovieTitle"
      :diagnostics-movie-subtitle="diagnosticsMovieSubtitle"
      :manual-action-loading="manualActionLoading"
      :field-label="fieldLabel"
      :field-value-preview="fieldValuePreview"
      :manual-action-label="manualActionLabel"
      :format-action-time="formatActionTime"
      @close="closeMovieSources"
      @match="manualMatchMovieAction"
      @unmatch="manualUnmatchMovieAction"
      @ignore="manualIgnoreMovieAction"
    />
  </section>
</template>

<script>
import { computed, watch } from 'vue'
import SupplementSourceDiagnosticsDialog from './SupplementSourceDiagnosticsDialog.vue'
import { useSupplementApi } from './useSupplementApi.js'

export default {
  name: 'RepairLaneTab',
  components: { SupplementSourceDiagnosticsDialog },
  props: {
    actorContext: { type: Object, default: null },
    focusMovie: { type: Object, default: null },
    movies: { type: Array, default: () => [] },
    fieldGapCount: { type: Number, default: 0 },
    pendingCandidateCount: { type: Number, default: 0 },
    detailTargetCount: { type: Number, default: 0 },
  },
  emits: ['movies-requested', 'movies-refresh-requested'],
  setup(props, { emit }) {
    const supplement = useSupplementApi()

    const diagnosticsMovieTitle = computed(() => {
      const movie = supplement.sourceDiagnostics.value?.movie
      return movie?.dvd_id || movie?.canonical_number || '来源诊断'
    })

    const diagnosticsMovieSubtitle = computed(() => {
      const movie = supplement.sourceDiagnostics.value?.movie
      return movie?.title || movie?.matched_content_id || ''
    })

    const diagnosticsFocusMovie = computed(() => props.focusMovie
      || props.movies.find(movie => supplement.movieMatchClass(movie) === 'candidate')
      || props.movies.find(movie => supplement.movieFieldChips(movie).some(chip => !chip.value))
      || props.movies[0]
      || null)

    const diagnosticsFocusMovieBadges = computed(() => {
      const movie = diagnosticsFocusMovie.value
      if (!movie) return ['暂无影片']
      const badges = []
      if (supplement.movieMatchClass(movie) === 'candidate') badges.push('候选待确认')
      const missing = supplement.movieFieldChips(movie).filter(chip => !chip.value)
      if (missing.length) badges.push(`${missing.length} 个字段缺口`)
      if (movie.source_movie_id) badges.push('可追溯来源')
      if (!badges.length) badges.push('字段已齐')
      return badges
    })

    const diagnosticsLaunchpadRows = computed(() => [
      { key: 'candidate', value: props.pendingCandidateCount, label: '待确认候选', hint: '先确认高风险匹配' },
      { key: 'fields', value: props.fieldGapCount, label: '字段缺口', hint: '定位缺封面、时长、系列和分类' },
      { key: 'details', value: props.detailTargetCount, label: '可补详情', hint: '可继续抓取详情来源' },
    ])

    async function openDiagnosticsFocusMovie() {
      if (!diagnosticsFocusMovie.value) return
      await supplement.openMovieSources(diagnosticsFocusMovie.value)
    }

    async function openMovieSources(movie) {
      await supplement.openMovieSources(movie)
    }

    async function manualMatchMovieAction(contentId) {
      await supplement.manualMatchMovie(contentId)
      emit('movies-refresh-requested')
    }

    async function manualIgnoreMovieAction() {
      await supplement.manualIgnoreMovie()
      emit('movies-refresh-requested')
    }

    async function manualUnmatchMovieAction() {
      await supplement.manualUnmatchMovie()
      emit('movies-refresh-requested')
    }

    watch(
      () => props.focusMovie?.id,
      async (id) => {
        if (!id || !props.focusMovie) return
        await openMovieSources(props.focusMovie)
      },
      { immediate: true }
    )

    return {
      ...supplement,
      emit,
      diagnosticsMovieTitle,
      diagnosticsMovieSubtitle,
      diagnosticsLaunchpadRows,
      diagnosticsFocusMovie,
      diagnosticsFocusMovieBadges,
      openDiagnosticsFocusMovie,
      openMovieSources,
      manualMatchMovieAction,
      manualIgnoreMovieAction,
      manualUnmatchMovieAction,
    }
  },
}
</script>

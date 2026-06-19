<template>
  <div class="works-tab">
    <SupplementMoviesPanel
      :movie-filters="movieFilters"
      :match-filter-options="matchFilterOptions"
      :quality-filter-options="qualityFilterOptions"
      :movies-loading="moviesLoading"
      :supplement-movies="supplementMovies"
      :movies-total-pages="moviesTotalPages"
      :movie-page="moviePage"
      :batch-enriching="batchEnriching"
      :candidate-importing="candidateImporting"
      :enriching-movies="enrichingMovies"
      :apply-image-fallback="applyImageFallback"
      :movie-cover="movieCover"
      :movie-categories="movieCategories"
      :movie-match-class="movieMatchClass"
      :movie-match-label="movieMatchLabel"
      @apply-filters="applyMovieFilters"
      @batch-enrich="batchEnrichMoviesAction"
      @create-candidates="createDownloadCandidatesAction"
      @enrich="enrichMovieAction"
      @open-sources="openMovieSourcesAction"
      @go-page="goMoviePage"
      @refresh="loadMovies"
      @clear-filters="clearMovieFilters"
    />

    <SupplementSourceDiagnosticsDialog
      v-if="sourceDiagnosticsOpen"
      drawer
      :source-diagnostics-loading="sourceDiagnosticsLoading"
      :source-diagnostics="sourceDiagnostics"
      :diagnostics-movie-title="diagnosticsMovieTitle"
      :diagnostics-movie-subtitle="diagnosticsMovieSubtitle"
      :actress-name="actorName"
      :actress-avatar="actressAvatar"
      :enriching="diagnosticsEnriching"
      :manual-action-loading="manualActionLoading"
      :field-label="fieldLabel"
      :field-value-preview="fieldValuePreview"
      :manual-action-label="manualActionLabel"
      :format-action-time="formatActionTime"
      @close="closeDrawer"
      @enrich="enrichDiagnosticsAll"
      @enrich-source="enrichDiagnosticsSourceAction"
      @match="manualMatchMovie"
      @unmatch="manualUnmatchMovie"
      @ignore="manualIgnoreMovie"
    />
  </div>
</template>

<script>
import { computed, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { applyImageFallback } from '../../utils/imageFallback.js'
import { actorAvatar } from '../../utils/actorDisplay.js'
import SupplementMoviesPanel from './SupplementMoviesPanel.vue'
import SupplementSourceDiagnosticsDialog from './SupplementSourceDiagnosticsDialog.vue'
import { useSupplementApi } from './useSupplementApi.js'

export default {
  name: 'MoviesTab',
  components: { SupplementMoviesPanel, SupplementSourceDiagnosticsDialog },
  props: {
    actorContext: { type: Object, default: null },
    actorName: { type: String, default: '' },
    initialFilters: { type: Object, default: () => ({}) },
    refreshNonce: { type: Number, default: 0 },
  },
  emits: ['filters-change', 'jobs-requested', 'summary-change'],
  setup(props, { emit }) {
    const router = useRouter()
    const route = useRoute()
    const supplement = useSupplementApi()
    const moviePage = ref(1)
    const movieFilters = reactive({ matched: false, quality: '', actress_id: '', q: '' })
    const matchFilterOptions = [
      { value: null, label: '全部' },
      { value: false, label: '未匹配' },
      { value: true, label: '已匹配' },
    ]
    const qualityFilterOptions = [
      { value: '', label: '全部质量' },
      { value: 'missing_cover', label: '缺封面' },
      { value: 'missing_runtime', label: '缺时长' },
      { value: 'missing_maker', label: '缺厂商' },
      { value: 'missing_categories', label: '缺分类' },
      { value: 'low_completeness', label: '低完整度' },
    ]

    const actressAvatar = computed(() => actorAvatar(props.actorContext))

    const diagnosticsMovieTitle = computed(() => {
      const movie = supplement.sourceDiagnostics.value?.movie
      return movie?.dvd_id || movie?.canonical_number || '字段来源'
    })
    const diagnosticsMovieSubtitle = computed(() => {
      const movie = supplement.sourceDiagnostics.value?.movie
      return movie?.title || movie?.matched_content_id || ''
    })

    function syncFilters() {
      Object.assign(movieFilters, {
        matched: props.initialFilters.matched ?? false,
        quality: props.initialFilters.quality || '',
        q: props.initialFilters.q || '',
        actress_id: props.actorContext?.id ? String(props.actorContext.id) : '',
      })
    }

    function emitSummary() {
      emit('summary-change', {
        total: supplement.moviesTotalCount.value,
        movies: supplement.supplementMovies.value,
        fieldGapCount: supplement.workspaceMovieFieldGapCount.value,
        pendingCandidateCount: supplement.workspacePendingCandidateCount.value,
        detailTargetCount: supplement.workspaceDetailTargetCount.value,
      })
    }

    async function loadMovies(options = {}) {
      await supplement.loadMovies({ page: moviePage.value, pageSize: 20, filters: movieFilters, ...options })
      emitSummary()
    }

    async function applyMovieFilters() {
      moviePage.value = 1
      emit('filters-change', { ...movieFilters })
      await loadMovies()
    }

    async function clearMovieFilters() {
      movieFilters.matched = null
      movieFilters.quality = ''
      movieFilters.q = ''
      moviePage.value = 1
      await applyMovieFilters()
    }

    async function goMoviePage(page) {
      moviePage.value = page
      await loadMovies()
    }

    async function enrichMovieAction(movie) {
      await supplement.enrichMovie(movie, {
        actressId: props.actorContext?.id,
        onJobsRequested: () => emit('jobs-requested'),
      })
    }

    function enrichDiagnosticsAll() {
      return supplement.enrichDiagnosticsMovie({
        source: 'all',
        actressId: props.actorContext?.id,
        onJobsRequested: () => emit('jobs-requested'),
      })
    }

    function enrichDiagnosticsSourceAction({ source, sourceMovieId } = {}) {
      return supplement.enrichDiagnosticsMovie({
        source,
        sourceMovieId,
        actressId: props.actorContext?.id,
        onJobsRequested: () => emit('jobs-requested'),
      })
    }

    async function batchEnrichMoviesAction() {
      await supplement.batchEnrichMovies({
        filters: movieFilters,
        onJobsRequested: () => emit('jobs-requested'),
      })
    }

    async function createDownloadCandidatesAction() {
      await supplement.createDownloadCandidates({
        filters: movieFilters,
        actressId: props.actorContext?.id,
        actressName: props.actorName,
        router,
      })
    }

    // Diagnostics drawer is addressed by ?work=<id> so the back button closes it
    // instead of leaving the page, and it never swaps tabs or pops a full-screen modal.
    function buildQuery(patch) {
      const next = { ...route.query, ...patch }
      Object.keys(next).forEach(key => {
        if (next[key] === undefined || next[key] === null || next[key] === '') delete next[key]
      })
      return next
    }

    function openMovieSourcesAction(movie) {
      if (!movie?.id) return
      router.push({ path: route.path, query: buildQuery({ work: String(movie.id) }) }).catch(() => {})
    }

    function closeDrawer() {
      router.push({ path: route.path, query: buildQuery({ work: undefined }) }).catch(() => {})
    }

    watch(
      () => route.query.work,
      async (work) => {
        const workId = Array.isArray(work) ? work[0] : work
        if (workId) {
          if (String(supplement.sourceDiagnostics.value?.movie?.id || '') !== String(workId)) {
            await supplement.openMovieSources({ id: workId })
          }
        } else if (supplement.sourceDiagnosticsOpen.value) {
          supplement.closeMovieSources()
        }
      },
      { immediate: true }
    )

    watch(
      () => [props.actorContext?.id || '', JSON.stringify(props.initialFilters), props.refreshNonce],
      async () => {
        moviePage.value = 1
        syncFilters()
        await loadMovies()
      },
      { immediate: true }
    )

    return {
      ...supplement,
      moviePage,
      movieFilters,
      matchFilterOptions,
      qualityFilterOptions,
      actressAvatar,
      diagnosticsMovieTitle,
      diagnosticsMovieSubtitle,
      applyImageFallback,
      loadMovies,
      applyMovieFilters,
      clearMovieFilters,
      goMoviePage,
      enrichMovieAction,
      enrichDiagnosticsAll,
      enrichDiagnosticsSourceAction,
      batchEnrichMoviesAction,
      createDownloadCandidatesAction,
      openMovieSourcesAction,
      closeDrawer,
    }
  },
}
</script>

<style scoped src="./supplementMoviesPanel.css"></style>

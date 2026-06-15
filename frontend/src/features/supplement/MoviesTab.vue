<template>
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
</template>

<script>
import { reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { applyImageFallback } from '../../utils/imageFallback.js'
import SupplementMoviesPanel from './SupplementMoviesPanel.vue'
import { useSupplementApi } from './useSupplementApi.js'

export default {
  name: 'MoviesTab',
  components: { SupplementMoviesPanel },
  props: {
    actorContext: { type: Object, default: null },
    actorName: { type: String, default: '' },
    initialFilters: { type: Object, default: () => ({}) },
    refreshNonce: { type: Number, default: 0 },
  },
  emits: ['filters-change', 'jobs-requested', 'sources-opened', 'summary-change'],
  setup(props, { emit }) {
    const router = useRouter()
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

    async function openMovieSourcesAction(movie) {
      emit('sources-opened', movie)
    }

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
      applyImageFallback,
      loadMovies,
      applyMovieFilters,
      clearMovieFilters,
      goMoviePage,
      enrichMovieAction,
      batchEnrichMoviesAction,
      createDownloadCandidatesAction,
      openMovieSourcesAction,
    }
  },
}
</script>

<template>
  <div class="works-tab">
    <!-- Scoped to an actress: drill-down 作品目录 (collection→metadata lifecycle).
         Unscoped: the legacy flat 待补全作品 panel across all actresses. -->
    <ActressCatalogPanel
      v-if="actorContext"
      :actor="actorContext"
      :films="catalogFilms"
      :summary="catalogSummary"
      :loading="catalogLoading"
      :recomputing="recomputing"
      @find="catalogFind"
      @download="catalogDownload"
      @enrich="catalogEnrich"
      @open-sources="catalogOpenSources"
      @recompute="$emit('start-supplement')"
      @back="$emit('back-to-list')"
      @view-all="$emit('view-all')"
    />

    <SupplementMoviesPanel
      v-else
      :movie-filters="movieFilters"
      :match-filter-options="matchFilterOptions"
      :quality-filter-options="qualityFilterOptions"
      :movies-loading="moviesLoading"
      :supplement-movies="supplementMovies"
      :movies-total-count="moviesTotalCount"
      :movies-total-pages="moviesTotalPages"
      :movie-page="moviePage"
      :batch-enriching="batchEnriching"
      :candidate-importing="candidateImporting"
      :enriching-movies="enrichingMovies"
      :apply-image-fallback="applyImageFallback"
      :movie-cover="movieCover"
      :movie-field-chips="movieFieldChips"
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
      @pick-actor="$emit('pick-actor')"
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
import { ElMessage } from '../../utils/message.js'
import api from '../../api'
import SupplementMoviesPanel from './SupplementMoviesPanel.vue'
import ActressCatalogPanel from './ActressCatalogPanel.vue'
import SupplementSourceDiagnosticsDialog from './SupplementSourceDiagnosticsDialog.vue'
import { useSupplementApi } from './useSupplementApi.js'

function normNumber(value) {
  return String(value || '').toUpperCase().replace(/[^A-Z0-9]/g, '')
}

export default {
  name: 'MoviesTab',
  components: { SupplementMoviesPanel, ActressCatalogPanel, SupplementSourceDiagnosticsDialog },
  props: {
    actorContext: { type: Object, default: null },
    actorName: { type: String, default: '' },
    initialFilters: { type: Object, default: () => ({}) },
    refreshNonce: { type: Number, default: 0 },
    recomputing: { type: Boolean, default: false },
  },
  emits: ['filters-change', 'jobs-requested', 'summary-change', 'start-supplement', 'back-to-list', 'view-all', 'pick-actor'],
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

    // ---- drill-down catalog actions (per canonical film) -------------------
    async function reloadCatalog() {
      if (props.actorContext?.id) await supplement.loadCatalog(props.actorContext.id, { silent: true })
    }

    function filmNumber(film) {
      return film?.display_code || film?.canonical_number || ''
    }

    // 找源：按番号生成下载候选（含磁力检索），留在下钻里刷新状态。
    async function catalogFind(film) {
      await supplement.createDownloadCandidates({
        filters: { matched: false, q: filmNumber(film) },
        actressId: props.actorContext?.id,
        actressName: props.actorName,
      })
      await reloadCatalog()
    }

    // 下载：同样生成候选，但跳到下载中心审批/秒离线。
    async function catalogDownload(film) {
      await supplement.createDownloadCandidates({
        filters: { matched: false, q: filmNumber(film) },
        actressId: props.actorContext?.id,
        actressName: props.actorName,
        router,
      })
    }

    // 补元数据：按番号触发蛋源 detail job（全部源），进任务队列观察。
    async function catalogEnrich(film) {
      const seed = filmNumber(film)
      if (!seed) return
      try {
        await api.startSupplementMovieDetailJob(seed, 'all', props.actorContext?.id || null)
        ElMessage.success('已加入补全队列（全部源）')
        emit('jobs-requested')
      } catch (error) {
        ElMessage.error(`补全失败：${error?.message || '请求失败'}`)
      }
    }

    // number -> supplement movie, so the per-film ⋯ can open the diagnostics
    // drawer (字段来源 / match·unmatch·ignore) for works backed by a 蛋源 record.
    const movieByNumber = computed(() => {
      const idx = {}
      for (const movie of supplement.supplementMovies.value || []) {
        for (const key of [movie.dvd_id, movie.canonical_number, movie.normalized_number, movie.display_number]) {
          const n = normNumber(key)
          if (n && !idx[n]) idx[n] = movie
        }
      }
      return idx
    })

    function catalogOpenSources(film) {
      const movie = movieByNumber.value[normNumber(filmNumber(film))]
        || movieByNumber.value[normNumber(film?.canonical_number)]
      if (movie?.id) openMovieSourcesAction(movie)
      else ElMessage.info('该作品暂无补全源记录（多为原生作品，无需诊断）')
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
        if (props.actorContext?.id) {
          // Scoped drill-down: load the canonical 作品目录 for the panel, plus this
          // actress's flat supplement movies (any match state) as the ⋯ diagnostics index.
          await Promise.all([
            supplement.loadCatalog(props.actorContext.id),
            // page_size is capped at 100 server-side; the index is best-effort.
            supplement.loadMovies({ page: 1, pageSize: 100, filters: { matched: null, actress_id: String(props.actorContext.id) } }),
          ])
          emitSummary()
        } else {
          await loadMovies()
        }
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
      catalogFind,
      catalogDownload,
      catalogEnrich,
      catalogOpenSources,
    }
  },
}
</script>

<style scoped>
.works-tab { display: grid; gap: 14px; }
</style>

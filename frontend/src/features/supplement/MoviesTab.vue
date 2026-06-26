<template>
  <div class="works-tab">
    <!-- Scoped to an actress: drill-down 作品目录 (collection→metadata lifecycle).
         Unscoped: the legacy flat 待补全作品 panel across all actresses. -->
    <ActressCatalogPanel
      v-if="actorContext"
      :actor="actorContext"
      :year-groups="catalogYearGroups"
      :by-tab="catalogByTab"
      :summary="catalogSummary"
      :stage="catalogStageTab"
      :busy="catalogEnriching"
      :batch-busy="catalogBatchEnriching"
      :loading="catalogLoading"
      :recomputing="recomputing"
      @change-stage="setCatalogStage"
      @find="catalogFind"
      @download="catalogDownload"
      @enrich="catalogEnrich"
      @enrich-all="catalogEnrichAll"
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
import { requestConfirm } from '../../utils/confirmDialog'
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
    // Three-stage drill-down sub-tab (collection | fields | sources), driven by ?stage=.
    const catalogStageTab = ref('collection')
    // Per-canonical 补字段 busy flags, so the ② card shows 排队中 on the right film.
    const catalogEnriching = reactive({})
    // 字段阶段「一键补全」整体进行中标记，驱动批量按钮的转圈/禁用。
    const catalogBatchEnriching = ref(false)
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
      // Scoped: the three-stage panel is driven by completeness (catalogSummary),
      // so the top-nav 待补全作品 count comes from there — no capped movie pre-load.
      if (props.actorContext?.id) {
        emit('summary-change', { total: supplement.catalogSummary.value?.total || 0, movies: [] })
        return
      }
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
      const key = film.canonical_number
      catalogEnriching[key] = true
      try {
        await api.startSupplementMovieDetailJob(seed, 'all', props.actorContext?.id || null)
        ElMessage.success('已加入补全队列（全部源）')
        emit('jobs-requested')
      } catch (error) {
        ElMessage.error(`补全失败：${error?.message || '请求失败'}`)
      } finally {
        catalogEnriching[key] = false
      }
    }

    // 一键补全：把字段阶段所有缺字段作品一次性加入蛋源 detail 队列（全部源），
    // 免去逐部点「补字段」。走后端单次调用，后台逐个按番号入队（与单部「补字段」
    // 同一路径，覆盖正片/私拍），即时返回排期数；JavInfoApi 侧对 active job 去重。
    async function catalogEnrichAll() {
      if (catalogBatchEnriching.value || !props.actorContext?.id) return
      const count = (supplement.catalogByTab.value.fields || []).length
      if (!count) return
      const confirmed = await requestConfirm({
        title: '一键补全缺字段',
        message: `将为 ${count} 部缺字段作品加入补全队列（全部源）。`,
        details: '蛋源会按番号在后台逐部补全标题/封面/时长/厂商等字段，可在「任务」标签查看进度。',
        confirmText: '开始补全',
      })
      if (!confirmed) return
      catalogBatchEnriching.value = true
      try {
        const resp = await api.enrichSupplementActressFields(props.actorContext.id)
        const scheduled = (resp && (resp.data?.scheduled ?? resp.scheduled)) || 0
        ElMessage.success(`已加入补全队列（全部源）：${scheduled} 部`)
        emit('jobs-requested')
      } catch (error) {
        ElMessage.error(`一键补全失败：${error?.message || '请求失败'}`)
      } finally {
        catalogBatchEnriching.value = false
      }
    }

    // ?stage= drives the three-stage sub-tab; switching only updates the query
    // (buildQuery preserves tab/actress_id/work), so it never reloads the catalog.
    function setCatalogStage(stage) {
      catalogStageTab.value = stage
      router.push({ path: route.path, query: buildQuery({ stage: stage === 'collection' ? undefined : stage }) }).catch(() => {})
    }
    watch(
      () => route.query.stage,
      (value) => {
        const v = Array.isArray(value) ? value[0] : value
        catalogStageTab.value = (v === 'fields' || v === 'sources') ? v : 'collection'
      },
      { immediate: true }
    )

    // Resolve an actress's 蛋源 record by 番号 (exact normalized match), ON DEMAND
    // and uncapped. Returns the movie or null; never throws (a failure just yields
    // the fallback hint). Replaces the old server-capped pre-loaded number→id table
    // that silently dropped any 蛋源-backed film sorting past the first 100 rows.
    async function findSupplementMovieByNumber(number) {
      const want = normNumber(number)
      if (!want) return null
      try {
        const resp = await api.listSupplementMovies({ actress_id: props.actorContext?.id, q: number, page_size: 10 })
        const payload = resp && Object.prototype.hasOwnProperty.call(resp, 'data') ? resp.data : resp
        const list = (payload && payload.data) || payload || []
        return list.find(movie =>
          [movie.dvd_id, movie.canonical_number, movie.normalized_number, movie.display_number]
            .some(key => normNumber(key) === want),
        ) || null
      } catch {
        return null
      }
    }

    // The per-film ⋯ opens the diagnostics drawer (字段来源 / match·unmatch·ignore)
    // for works backed by a 蛋源 record; native works fall back to a hint.
    async function catalogOpenSources(film) {
      const number = filmNumber(film) || film?.canonical_number || ''
      const movie = number ? await findSupplementMovieByNumber(number) : null
      if (movie?.id) openMovieSourcesAction(movie)
      else if (film?.origin === 'supplement') ElMessage.info('该私拍片暂未建立蛋源诊断记录')
      else ElMessage.info('正片作品 · 字段来自正片目录；点「补字段」用蛋源补全缺失字段')
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
          // Scoped drill-down: load the canonical 作品目录 for the panel. The ⋯
          // diagnostics drawer resolves its 蛋源 record on demand (catalogOpenSources),
          // so there is no capped pre-load of the flat supplement-movie list here.
          await supplement.loadCatalog(props.actorContext.id)
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
      catalogEnrichAll,
      catalogOpenSources,
      catalogStageTab,
      catalogEnriching,
      catalogBatchEnriching,
      setCatalogStage,
    }
  },
}
</script>

<style scoped>
.works-tab { display: grid; gap: 14px; }
</style>

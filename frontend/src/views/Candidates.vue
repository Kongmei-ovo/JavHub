<template>
  <div class="candidates-page page-shell page-shell--workspace">
    <header class="page-header">
      <div class="header-left">
        <h1>候选确认</h1>
        <p class="header-subtitle">
          <span class="total-tasks">待确认 {{ candidateStats.candidate || 0 }}</span>
          <span v-if="candidateStats.needs_magnet > 0" class="downloading-hint"> · {{ candidateStats.needs_magnet }} 个待补磁力</span>
          <span v-if="candidateRuns.length" class="downloading-hint"> · 最近处理 {{ candidateRuns.length }} 次</span>
        </p>
      </div>
      <div class="header-actions">
        <button class="btn btn-ghost" type="button" @click="$router.push('/downloads')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16"><polyline points="9 18 15 12 9 6"/></svg>
          下载队列
        </button>
        <button class="btn btn-primary" type="button" @click="reload">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/></svg>
          刷新
        </button>
      </div>
    </header>

    <div v-if="candidateFilterLedger.length" class="candidate-filter-ledger" aria-label="当前候选筛选">
      <span v-for="filter in candidateFilterLedger" :key="filter.key" class="candidate-filter-token">{{ filter.label }}</span>
    </div>

    <DownloadCandidatePanel
      :candidate-filter="candidateFilter"
      :candidate-stats="candidateStats"
      :selecting-candidates="selectingCandidates"
      :selected-candidate-ids="selectedCandidateIds"
      :candidate-batch-processing="candidateBatchProcessing"
      :bulk-candidate-loading="bulkCandidateLoading"
      :candidate-runs="candidateRuns"
      :candidate-runs-loading="candidateRunsLoading"
      :candidate-total-pages="candidateTotalPages"
      :candidate-page="candidatePage"
      :candidate-total="candidateTotal"
      :candidate-repair-scope="candidateRepairScope"
      :filtered-candidates="filteredCandidates"
      :candidate-mutations="candidateMutations"
      :magnet-editor="magnetEditor"
      :candidate-detail="candidateDetail"
      @update-candidate-search="updateCandidateSearch"
      @search="submitCandidateSearch"
      @set-status="setCandidateStatus"
      @set-needs-magnet="setNeedsMagnet"
      @set-source="setCandidateSource"
      @set-latest-event="setCandidateLatestEvent"
      @toggle-selection="toggleCandidateSelection"
      @enrich-visible="enrichVisibleCandidateMagnets"
      @process-visible="processVisibleCandidates"
      @select-all-visible="selectAllVisibleCandidates"
      @clear-selection="clearCandidateSelection"
      @bulk-reject="bulkRejectCandidates"
      @bulk-restore="bulkRestoreCandidates"
      @refresh-runs="loadCandidateRuns"
      @apply-run="applyCandidateRunFilters"
      @apply-run-failed="applyCandidateRunFilters($event, { status: 'failed' })"
      @retry-failed-run="retryFailedCandidateRun"
      @go-page="goCandidatePage"
      @toggle-selected="toggleCandidateSelected"
      @open-detail="openCandidateDetail"
      @go-actor="goCandidateActor"
      @edit-magnet="editCandidateMagnet"
      @enrich-magnet="enrichCandidateMagnet"
      @approve="approveCandidate"
      @process="processCandidate"
      @reject="rejectCandidate"
      @close-magnet-editor="closeMagnetEditor"
      @update-magnet-editor-value="updateMagnetEditorValue"
      @submit-magnet-editor="submitMagnetEditor"
      @close-detail="closeCandidateDetail"
    />
  </div>
</template>

<script>
import { defineAsyncComponent, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useDownloadCandidates } from '../features/candidates/useDownloadCandidates.js'

const DownloadCandidatePanel = defineAsyncComponent(() => import('../features/candidates/DownloadCandidatePanel.vue'))

export default {
  name: 'Candidates',
  components: { DownloadCandidatePanel },
  setup() {
    const route = useRoute()
    const c = useDownloadCandidates({
      routePath: '/candidates',
      syncRoute: true,
    })

    function reload() {
      c.loadCandidates()
      c.loadCandidateRuns()
    }

    onMounted(() => {
      c.applyRouteQuery(route.query)
      reload()
    })

    watch(() => route.query, (query) => {
      if (c.applyRouteQuery(query)) reload()
    })

    return { ...c, reload }
  },
}
</script>

<style scoped src="../features/candidates/candidates.css"></style>

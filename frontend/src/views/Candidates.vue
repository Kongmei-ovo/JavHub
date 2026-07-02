<template>
  <div class="candidates-page page-shell page-shell--gallery">
    <header class="page-header">
      <div class="header-left">
        <h1>候选确认</h1>
        <div class="header-metrics" aria-label="候选概览">
          <span>待确认 {{ candidateStats.candidate || 0 }}</span>
          <span v-if="candidateStats.needs_magnet > 0">{{ candidateStats.needs_magnet }} 待补磁力</span>
        </div>
      </div>
      <div class="header-actions">
        <button class="btn btn-ghost" type="button" :class="{ active: selectingCandidates }" @click="toggleCandidateSelection">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16"><path d="M9 11l3 3L22 4"/><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/></svg>
          {{ selectingCandidates ? '退出批量' : '批量' }}
        </button>
        <button class="btn btn-ghost" type="button" :class="{ active: runsOpen }" @click="runsOpen = !runsOpen">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16"><circle cx="12" cy="12" r="9"/><polyline points="12 7 12 12 15 14"/></svg>
          最近处理
        </button>
        <RefreshButton @click="reload" />
      </div>
    </header>

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
      :runs-open="runsOpen"
      @update-candidate-search="updateCandidateSearch"
      @search="submitCandidateSearch"
      @set-status="setCandidateStatus"
      @set-needs-magnet="setNeedsMagnet"
      @set-source="setCandidateSource"
      @set-latest-event="setCandidateLatestEvent"
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
      @close-runs="runsOpen = false"
    />
  </div>
</template>

<script>
import { defineAsyncComponent, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useDownloadCandidates } from '../features/candidates/useDownloadCandidates.js'

const DownloadCandidatePanel = defineAsyncComponent(() => import('../features/candidates/DownloadCandidatePanel.vue'))
import RefreshButton from '../components/RefreshButton.vue'

export default {
  name: 'Candidates',
  components: { DownloadCandidatePanel, RefreshButton },
  setup() {
    const route = useRoute()
    const c = useDownloadCandidates({
      routePath: '/candidates',
      syncRoute: true,
    })

    // 「最近处理」改为按需弹窗（学其他页「历史按钮→弹窗」），默认不占版面。
    const runsOpen = ref(false)

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

    return { ...c, reload, runsOpen }
  },
}
</script>

<style scoped src="../features/candidates/candidates.css"></style>

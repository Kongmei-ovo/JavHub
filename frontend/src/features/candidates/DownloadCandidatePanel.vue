<template>
  <div class="candidate-panel">
    <div class="candidate-toolbar">
      <input
        :value="candidateFilter.q"
        class="candidate-search-input"
        placeholder="搜索番号、标题、演员"
        @input="$emit('update-candidate-search', $event.target.value)"
        @keyup.enter="$emit('search')"
      />
      <button class="chip" type="button" @click="$emit('search')">搜索</button>
      <button class="chip" type="button" :class="{ active: candidateFilter.status === 'candidate' }" @click="$emit('set-status', 'candidate')">待确认</button>
      <button class="chip" type="button" :class="{ active: candidateFilter.status === 'candidate' && candidateFilter.needs_magnet === true }" @click="$emit('set-needs-magnet', true)">待补磁力</button>
      <button class="chip" type="button" :class="{ active: candidateFilter.status === 'candidate' && candidateFilter.needs_magnet === false }" @click="$emit('set-needs-magnet', false)">可批准</button>
      <button class="chip" type="button" :class="{ active: candidateFilter.status === 'sent' }" @click="$emit('set-status', 'sent')">已下发</button>
      <button class="chip" type="button" :class="{ active: candidateFilter.status === 'failed' }" @click="$emit('set-status', 'failed')">失败</button>
      <button class="chip" type="button" :class="{ active: candidateFilter.status === 'rejected' }" @click="$emit('set-status', 'rejected')">已拒绝</button>
      <button class="chip" type="button" :class="{ active: !candidateFilter.status }" @click="$emit('set-status', '')">全部</button>
      <button class="chip" type="button" :class="{ active: candidateFilter.source === 'subscription' }" @click="$emit('set-source', 'subscription')">
        订阅 {{ candidateStats.by_source?.subscription || 0 }}
      </button>
      <button class="chip" type="button" :class="{ active: candidateFilter.source === 'inventory' }" @click="$emit('set-source', 'inventory')">
        库存 {{ candidateStats.by_source?.inventory || 0 }}
      </button>
      <button class="chip" type="button" :class="{ active: candidateFilter.source === 'supplement' }" @click="$emit('set-source', 'supplement')">
        补全 {{ candidateStats.by_source?.supplement || 0 }}
      </button>
      <button class="chip" type="button" :class="{ active: !candidateFilter.source }" @click="$emit('set-source', '')">全部来源</button>
      <button class="chip" type="button" :class="{ active: selectingCandidates }" @click="$emit('toggle-selection')">
        {{ selectingCandidates ? '退出选择' : '选择' }}
      </button>
      <button class="chip action-chip" type="button" :disabled="candidateBatchProcessing" @click="$emit('enrich-visible')">
        {{ candidateBatchProcessing === 'enrich' ? '补磁力中...' : '补当前磁力' }}
      </button>
      <button class="chip action-chip primary" type="button" :disabled="candidateBatchProcessing" @click="$emit('process-visible')">
        {{ processVisibleLabel }}
      </button>
    </div>

    <div v-if="candidateRepairScope" class="candidate-repair-scope" aria-label="候选修复范围">
      <div>
        <span>修复范围</span>
        <strong>{{ candidateRepairScope.scopeLabel }}</strong>
      </div>
      <div class="candidate-repair-scope-grid">
        <span><b>{{ candidateRepairScope.total || 0 }}</b><small>筛选总量</small></span>
        <span><b>{{ candidateRepairScope.visibleCount || 0 }}</b><small>当前页</small></span>
        <span><b>{{ candidateRepairScope.visibleMagnetTargets || 0 }}</b><small>当前页可补磁力</small></span>
      </div>
    </div>

    <div v-if="candidateLatestEventFilters.length" class="candidate-event-toolbar">
      <span class="candidate-event-toolbar-label">最近动作</span>
      <button
        class="chip"
        type="button"
        :class="{ active: !candidateFilter.latest_event_action }"
        @click="$emit('set-latest-event', '')"
      >
        全部
      </button>
      <button
        v-for="filter in candidateLatestEventFilters"
        :key="filter.action"
        class="chip"
        type="button"
        :class="{ active: candidateFilter.latest_event_action === filter.action }"
        @click="$emit('set-latest-event', filter.action)"
      >
        {{ filter.label }} {{ filter.count }}
      </button>
    </div>

    <div v-if="selectingCandidates" class="bulk-toolbar">
      <span>已选 {{ selectedCandidateIds.length }} 个</span>
      <button class="btn btn-ghost" type="button" @click="$emit('select-all-visible')">选择当前页</button>
      <button class="btn btn-ghost" type="button" @click="$emit('clear-selection')">清空</button>
      <button class="btn btn-ghost" type="button" :disabled="selectedCandidateIds.length === 0 || bulkCandidateLoading" @click="$emit('bulk-reject')">批量拒绝</button>
      <button class="btn btn-primary" type="button" :disabled="selectedCandidateIds.length === 0 || bulkCandidateLoading" @click="$emit('bulk-restore')">批量恢复</button>
    </div>

    <CandidateRunPanel
      :runs="candidateRuns"
      :loading="candidateRunsLoading"
      :processing="candidateBatchProcessing"
      @refresh="$emit('refresh-runs')"
      @apply="$emit('apply-run', $event)"
      @apply-failed="$emit('apply-run-failed', $event)"
      @retry-failed="$emit('retry-failed-run', $event)"
    />

    <div v-if="candidateTotalPages > 1" class="candidate-pagination">
      <button class="page-btn" type="button" :disabled="candidatePage <= 1" @click="$emit('go-page', 1)">«</button>
      <button class="page-btn" type="button" :disabled="candidatePage <= 1" @click="$emit('go-page', candidatePage - 1)">‹</button>
      <span class="page-indicator">{{ candidatePage }} / {{ candidateTotalPages }} · {{ candidateTotal }} 个候选</span>
      <button class="page-btn" type="button" :disabled="candidatePage >= candidateTotalPages" @click="$emit('go-page', candidatePage + 1)">›</button>
      <button class="page-btn" type="button" :disabled="candidatePage >= candidateTotalPages" @click="$emit('go-page', candidateTotalPages)">»</button>
    </div>

    <div v-if="filteredCandidates.length > 0" class="tasks-grid">
      <div
        v-for="candidate in filteredCandidates"
        :key="candidate.id"
        class="task-card av-card candidate-card"
      >
        <label v-if="selectingCandidates" class="candidate-select" @click.stop>
          <input
            type="checkbox"
            :checked="selectedCandidateIds.includes(candidate.id)"
            @change="$emit('toggle-selected', candidate.id)"
          />
        </label>
        <div class="task-cover">
          <img v-if="candidate.jacket_thumb_url" :src="candidate.jacket_thumb_url" :alt="candidate.title || candidate.content_id" loading="lazy" decoding="async" />
          <div v-else class="cover-placeholder">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="40" height="40">
              <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/>
              <line x1="7" y1="2" x2="7" y2="22"/>
              <line x1="17" y1="2" x2="17" y2="22"/>
            </svg>
          </div>
          <div class="cover-overlay">
            <span class="cover-code">{{ candidate.dvd_id || candidate.content_id }}</span>
          </div>
        </div>

        <div class="task-info">
          <h3 class="task-title" :title="candidate.title">{{ candidate.title || candidate.content_id }}</h3>
          <div class="task-meta">
            <span :class="['badge', candidateBadge(candidate.status)]">{{ candidateStatusLabel(candidate.status) }}</span>
            <span class="task-time">{{ candidateSourceLabel(candidate.source) }}</span>
          </div>
          <div class="candidate-subtitle">{{ candidate.actress_name || '未知演员' }} · {{ candidate.release_date || '日期未知' }}</div>
          <div class="candidate-magnet" :class="{ empty: !candidate.magnet }">
            {{ candidate.magnet ? '已有 magnet' : '待补磁力' }}
          </div>
          <div v-if="candidate.reason" class="candidate-reason" :title="candidate.reason">
            {{ candidate.reason }}
          </div>
          <div v-if="candidate.download_task_id" class="candidate-task-link">
            已关联任务 #{{ candidate.download_task_id }}
            <span v-if="candidate.download_task?.status">· {{ statusLabel(candidate.download_task.status) }}</span>
            <span v-if="candidate.download_task?.downloader_name">· {{ candidate.download_task.downloader_name }}</span>
          </div>
          <div v-if="candidate.error_msg" class="task-error" :title="candidate.error_msg">
            {{ candidate.error_msg }}
          </div>
          <div v-if="candidate.events?.length" class="candidate-event">
            最近动作 {{ candidate.events[0].action }}
          </div>
          <div class="candidate-context-actions">
            <button class="link-btn" type="button" @click="$emit('open-detail', candidate)">详情</button>
            <button v-if="candidate.actress_id" class="link-btn" type="button" @click="$emit('go-actor', candidate)">演员</button>
            <button v-if="candidate.source === 'supplement' && candidate.actress_id" class="link-btn" type="button" @click="$emit('go-supplement', candidate)">补全</button>
          </div>
        </div>

        <div class="task-actions">
          <button v-if="candidate.status === 'candidate' || candidate.status === 'failed'" class="btn btn-ghost" type="button" :disabled="isCandidateMutating(candidate.id)" @click="$emit('edit-magnet', candidate)">填磁力</button>
          <button v-if="(candidate.status === 'candidate' || candidate.status === 'failed') && !candidate.magnet" class="btn btn-ghost" type="button" :disabled="isCandidateMutating(candidate.id)" @click="$emit('enrich-magnet', candidate)">
            {{ candidateMutations[candidate.id] === 'enrich' ? '查找中...' : '补磁力' }}
          </button>
          <button v-if="candidate.status === 'candidate' || candidate.status === 'failed'" class="btn btn-primary" type="button" :disabled="isCandidateMutating(candidate.id)" @click="$emit('approve', candidate)">
            {{ candidateMutations[candidate.id] === 'approve' ? '处理中...' : (candidate.status === 'failed' ? '重试' : '批准') }}
          </button>
          <button v-if="candidate.status === 'candidate' || candidate.status === 'failed'" class="btn btn-primary" type="button" :disabled="isCandidateMutating(candidate.id)" @click="$emit('process', candidate)">
            {{ candidateMutations[candidate.id] === 'process' ? '处理中...' : '策略处理' }}
          </button>
          <button v-if="candidate.status === 'candidate'" class="btn btn-ghost" type="button" :disabled="isCandidateMutating(candidate.id)" @click="$emit('reject', candidate)">拒绝</button>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
        <polyline points="7 10 12 15 17 10"/>
        <line x1="12" y1="15" x2="12" y2="3"/>
      </svg>
      <p>暂无下载候选</p>
      <p class="text-secondary empty-state-hint">订阅检查和库存对比会把缺失影片写到这里</p>
    </div>

    <div v-if="candidateTotalPages > 1" class="candidate-pagination bottom">
      <button class="page-btn" type="button" :disabled="candidatePage <= 1" @click="$emit('go-page', 1)">«</button>
      <button class="page-btn" type="button" :disabled="candidatePage <= 1" @click="$emit('go-page', candidatePage - 1)">‹</button>
      <span class="page-indicator">{{ candidatePage }} / {{ candidateTotalPages }}</span>
      <button class="page-btn" type="button" :disabled="candidatePage >= candidateTotalPages" @click="$emit('go-page', candidatePage + 1)">›</button>
      <button class="page-btn" type="button" :disabled="candidatePage >= candidateTotalPages" @click="$emit('go-page', candidateTotalPages)">»</button>
    </div>

    <div v-if="magnetEditor.open" class="inline-dialog-overlay" @click.self="$emit('close-magnet-editor')">
      <div class="inline-dialog">
        <div class="inline-dialog-header">
          <div>
            <h2>填磁力</h2>
            <p>{{ magnetEditor.candidate?.dvd_id || magnetEditor.candidate?.content_id || '下载候选' }}</p>
          </div>
          <button class="dialog-close-btn" type="button" @click="$emit('close-magnet-editor')">×</button>
        </div>
        <textarea
          :value="magnetEditor.value"
          class="magnet-editor-input"
          placeholder="magnet:?xt=urn:btih:..."
          @input="$emit('update-magnet-editor-value', $event.target.value)"
          @keyup.meta.enter="$emit('submit-magnet-editor')"
          @keyup.ctrl.enter="$emit('submit-magnet-editor')"
        ></textarea>
        <div class="inline-dialog-actions">
          <button class="btn btn-ghost" type="button" @click="$emit('close-magnet-editor')">取消</button>
          <button
            class="btn btn-primary"
            type="button"
            :disabled="!magnetEditor.value.trim() || isCandidateMutating(magnetEditor.candidate?.id)"
            @click="$emit('submit-magnet-editor')"
          >
            {{ isCandidateMutating(magnetEditor.candidate?.id) ? '保存中...' : '保存磁力' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="candidateDetail.open" class="inline-dialog-overlay" @click.self="$emit('close-detail')">
      <div class="inline-dialog candidate-detail-dialog">
        <div class="inline-dialog-header">
          <div>
            <h2>{{ candidateDetail.data?.dvd_id || candidateDetail.data?.content_id || '候选详情' }}</h2>
            <p>{{ candidateDetail.data?.title || candidateDetail.data?.actress_name || '' }}</p>
          </div>
          <button class="dialog-close-btn" type="button" @click="$emit('close-detail')">×</button>
        </div>
        <div v-if="candidateDetail.loading" class="candidate-detail-loading">加载中...</div>
        <template v-else-if="candidateDetail.data">
          <div class="candidate-detail-grid">
            <div><span>状态</span><strong>{{ candidateStatusLabel(candidateDetail.data.status) }}</strong></div>
            <div><span>来源</span><strong>{{ candidateSourceLabel(candidateDetail.data.source) }}</strong></div>
            <div><span>磁力</span><strong>{{ candidateDetail.data.magnet ? '已有' : '待补' }}</strong></div>
            <div><span>下载任务</span><strong>{{ candidateDetail.data.download_task_id || '未下发' }}</strong></div>
          </div>
          <div v-if="candidateDetail.data.error_msg" class="candidate-detail-error">{{ candidateDetail.data.error_msg }}</div>
          <div v-if="candidateDetail.data.magnet" class="candidate-detail-magnet">{{ candidateDetail.data.magnet }}</div>
          <div class="event-timeline">
            <div v-for="event in candidateDetail.data.events || []" :key="event.id" class="event-row">
              <span class="event-dot"></span>
              <div>
                <strong>{{ eventActionLabel(event.action) }}</strong>
                <p>{{ event.detail || '无详情' }}</p>
                <small>{{ event.operator || 'system' }} · {{ formatTime(event.created_at) }}</small>
              </div>
            </div>
            <small v-if="!(candidateDetail.data.events || []).length">暂无事件记录</small>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script>
import CandidateRunPanel from './CandidateRunPanel.vue'

export default {
  name: 'DownloadCandidatePanel',
  components: { CandidateRunPanel },
  props: {
    candidateFilter: { type: Object, required: true },
    candidateStats: { type: Object, required: true },
    selectingCandidates: { type: Boolean, default: false },
    selectedCandidateIds: { type: Array, default: () => [] },
    candidateBatchProcessing: { type: [Boolean, String], default: '' },
    bulkCandidateLoading: { type: Boolean, default: false },
    candidateRuns: { type: Array, default: () => [] },
    candidateRunsLoading: { type: Boolean, default: false },
    candidateTotalPages: { type: Number, default: 1 },
    candidatePage: { type: Number, default: 1 },
    candidateTotal: { type: Number, default: 0 },
    candidateRepairScope: { type: Object, default: null },
    filteredCandidates: { type: Array, default: () => [] },
    candidateMutations: { type: Object, default: () => ({}) },
    magnetEditor: { type: Object, required: true },
    candidateDetail: { type: Object, required: true },
  },
  emits: [
    'update-candidate-search',
    'search',
    'set-status',
    'set-needs-magnet',
    'set-source',
    'set-latest-event',
    'toggle-selection',
    'enrich-visible',
    'process-visible',
    'select-all-visible',
    'clear-selection',
    'bulk-reject',
    'bulk-restore',
    'refresh-runs',
    'apply-run',
    'apply-run-failed',
    'retry-failed-run',
    'go-page',
    'toggle-selected',
    'open-detail',
    'go-actor',
    'go-supplement',
    'edit-magnet',
    'enrich-magnet',
    'approve',
    'process',
    'reject',
    'close-magnet-editor',
    'update-magnet-editor-value',
    'submit-magnet-editor',
    'close-detail',
  ],
  computed: {
    processVisibleLabel() {
      if (this.candidateBatchProcessing === 'dry-run') return '预演中...'
      if (this.candidateBatchProcessing === 'process') return '处理中...'
      return '按策略处理当前'
    },
    candidateLatestEventFilters() {
      const counts = this.candidateStats.latest_event_by_action || {}
      return Object.entries(counts)
        .filter(([, count]) => Number(count || 0) > 0)
        .map(([action, count]) => ({
          action,
          count: Number(count || 0),
          label: this.eventActionLabel(action),
        }))
    },
  },
  methods: {
    isCandidateMutating(id) {
      return Boolean(this.candidateMutations[id]) || this.bulkCandidateLoading || Boolean(this.candidateBatchProcessing)
    },
    statusLabel(status) {
      const map = { pending: '待处理', downloading: '下载中', completed: '已完成', failed: '失败' }
      return map[status] || status
    },
    candidateBadge(status) {
      const map = { candidate: 'badge-pending', approved: 'badge-info', sent: 'badge-success', failed: 'badge-error', rejected: 'badge-pending' }
      return map[status] || 'badge-pending'
    },
    candidateStatusLabel(status) {
      const map = { candidate: '待确认', approved: '已批准', sent: '已下发', failed: '失败', rejected: '已拒绝' }
      return map[status] || status
    },
    candidateSourceLabel(source) {
      const map = { subscription: '订阅', inventory: '库存', supplement: '补全', manual: '手动' }
      return map[source] || source || '未知来源'
    },
    eventActionLabel(action) {
      const map = {
        without_event: '未处理',
        upsert: '写入候选',
        magnet_updated: '手动更新磁力',
        magnet_enriched: '自动补充磁力',
        magnet_enrich_failed: '磁力补充失败',
        magnet_enrich_skipped: '跳过补磁力',
        policy_skipped: '策略跳过',
        auto_approved: '自动下发',
        approved: '人工批准',
        approve_failed: '批准失败',
        process_failed: '处理失败',
        rejected: '拒绝候选',
        bulk_rejected: '批量拒绝',
        bulk_restored: '批量恢复',
        supplement_imported: '补全导入',
      }
      return map[action] || action
    },
    formatTime(time) {
      if (!time) return ''
      const d = new Date(time)
      return `${d.getMonth()+1}/${d.getDate()} ${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`
    },
  },
}
</script>

<style scoped src="./downloadCandidatePanel.css"></style>

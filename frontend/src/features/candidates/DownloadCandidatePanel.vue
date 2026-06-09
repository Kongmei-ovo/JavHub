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

    <div v-if="filteredCandidates.length > 0" class="cand-list">
      <div
        v-for="candidate in filteredCandidates"
        :key="candidate.id"
        :class="candidateCardClass(candidate)"
      >
        <div class="cc-poster" @click="$emit('open-detail', candidate)">
          <img v-if="candidate.jacket_thumb_url" :src="candidate.jacket_thumb_url" :alt="candidate.title || candidate.content_id" loading="lazy" decoding="async" />
          <div v-else class="cc-poster-placeholder">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="28" height="28">
              <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/>
              <line x1="7" y1="2" x2="7" y2="22"/>
              <line x1="17" y1="2" x2="17" y2="22"/>
            </svg>
          </div>
          <div class="cc-scrim"></div>
          <span class="cc-code">{{ candidate.dvd_id || candidate.content_id }}</span>
          <button
            v-if="selectingCandidates && isSelectable(candidate)"
            type="button"
            class="cc-check"
            :class="{ on: selectedCandidateIds.includes(candidate.id) }"
            :aria-pressed="selectedCandidateIds.includes(candidate.id)"
            aria-label="选择候选"
            @click.stop="$emit('toggle-selected', candidate.id)"
          >
            <svg v-if="selectedCandidateIds.includes(candidate.id)" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" width="14" height="14">
              <polyline points="20 6 9 17 4 12"/>
            </svg>
          </button>
        </div>

        <div class="cc-main">
          <div class="cc-srcline">
            <span class="src-pill">{{ candidateSourceLabel(candidate.source) }}</span>
            <span class="mag-state" :class="{ empty: !candidate.magnet }">{{ candidate.magnet ? '已有 magnet' : '待补磁力' }}</span>
            <span v-if="candidate.events?.length" class="cc-time">{{ formatTime(candidate.events[0].created_at) }}</span>
          </div>
          <h3 class="cc-title" :title="candidate.title" @click="$emit('open-detail', candidate)">{{ candidate.title || candidate.content_id }}</h3>
          <div class="cc-actor">
            <span class="cc-av" :style="actorAvatarStyle(candidate)">{{ actorInitial(candidate) }}</span>
            <span class="cc-actor-name">{{ candidate.actress_name || '未知演员' }}</span>
            <span class="cc-actor-date">· {{ candidate.release_date || '日期未知' }}</span>
          </div>
          <div v-if="candidate.status === 'failed' && (candidate.reason || candidate.error_msg)" class="cc-reason" :title="candidate.reason || candidate.error_msg">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="12" height="12"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            {{ candidate.reason || candidate.error_msg }}
          </div>
          <div v-if="candidate.status === 'sent' && candidate.download_task_id" class="cc-tasklink">
            已关联任务 #{{ candidate.download_task_id }}
            <span v-if="candidate.download_task?.status">· {{ statusLabel(candidate.download_task.status) }}</span>
            <span v-if="candidate.download_task?.downloader_name">· {{ candidate.download_task.downloader_name }}</span>
          </div>
          <div v-if="candidate.events?.length && candidate.status !== 'sent' && candidate.status !== 'failed'" class="cc-event-note">
            最近动作 {{ eventActionLabel(candidate.events[0].action) }}
          </div>
          <div class="cc-links">
            <button class="link-btn" type="button" @click="$emit('open-detail', candidate)">详情</button>
            <button v-if="candidate.actress_id" class="link-btn" type="button" @click="$emit('go-actor', candidate)">演员</button>
            <button v-if="candidate.source === 'supplement' && candidate.actress_id" class="link-btn" type="button" @click="$emit('go-supplement', candidate)">补全</button>
          </div>
        </div>

        <div class="cc-decide">
          <template v-if="candidate.status === 'candidate' && candidate.magnet">
            <div class="cc-seed"><span class="cc-dot ok"></span>可批准</div>
            <div class="cc-btn-row">
              <button class="btn cc-approve" type="button" :disabled="isCandidateMutating(candidate.id)" @click="$emit('approve', candidate)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" width="15" height="15"><polyline points="20 6 9 17 4 12"/></svg>
                {{ candidateMutations[candidate.id] === 'approve' ? '处理中...' : '批准' }}
              </button>
              <button class="btn btn-ghost cc-ghost-btn" type="button" :disabled="isCandidateMutating(candidate.id)" title="按下载策略自动处理" @click="$emit('process', candidate)">
                {{ candidateMutations[candidate.id] === 'process' ? '处理中...' : '策略处理' }}
              </button>
            </div>
            <div class="cc-quiet">
              <button class="link-btn quiet" type="button" :disabled="isCandidateMutating(candidate.id)" @click="$emit('edit-magnet', candidate)">填磁力</button>
              <span class="sep">·</span>
              <button class="link-btn danger" type="button" :disabled="isCandidateMutating(candidate.id)" @click="$emit('reject', candidate)">拒绝</button>
            </div>
          </template>

          <template v-else-if="candidate.status === 'candidate' && !candidate.magnet">
            <div class="cc-warn">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
              待补磁力 · 暂不可批准
            </div>
            <div class="cc-btn-row">
              <button class="btn cc-supplement" type="button" :disabled="isCandidateMutating(candidate.id)" @click="$emit('enrich-magnet', candidate)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15"><path d="M10 13a5 5 0 007.54.54l3-3a5 5 0 00-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 00-7.54-.54l-3 3a5 5 0 007.07 7.07l1.71-1.71"/></svg>
                {{ candidateMutations[candidate.id] === 'enrich' ? '查找中...' : '补磁力' }}
              </button>
              <button class="btn btn-ghost cc-ghost-btn" type="button" :disabled="isCandidateMutating(candidate.id)" @click="$emit('edit-magnet', candidate)">填磁力</button>
            </div>
            <div class="cc-quiet">
              <button class="link-btn danger" type="button" :disabled="isCandidateMutating(candidate.id)" @click="$emit('reject', candidate)">拒绝</button>
            </div>
          </template>

          <template v-else-if="candidate.status === 'failed'">
            <div class="cc-btn-row">
              <button class="btn cc-approve" type="button" :disabled="isCandidateMutating(candidate.id)" @click="$emit('approve', candidate)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/></svg>
                {{ candidateMutations[candidate.id] === 'approve' ? '处理中...' : '重试' }}
              </button>
            </div>
            <div class="cc-quiet">
              <button class="link-btn quiet" type="button" :disabled="isCandidateMutating(candidate.id)" @click="$emit('edit-magnet', candidate)">填磁力</button>
              <span class="sep">·</span>
              <button class="link-btn danger" type="button" :disabled="isCandidateMutating(candidate.id)" @click="$emit('reject', candidate)">拒绝</button>
            </div>
          </template>

          <template v-else-if="candidate.status === 'sent'">
            <span class="cc-badge ok"><span class="cc-dot ok"></span>已下发</span>
          </template>

          <template v-else-if="candidate.status === 'rejected'">
            <span class="cc-badge bad"><span class="cc-dot bad"></span>已拒绝</span>
            <div class="cc-quiet">
              <button class="link-btn quiet" type="button" @click="$emit('approve', candidate)">恢复</button>
            </div>
          </template>

          <template v-else-if="candidate.status === 'approved'">
            <span class="cc-badge info"><span class="cc-dot info"></span>已批准</span>
          </template>
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
    isSelectable(candidate) {
      return candidate.status === 'candidate' && Boolean(candidate.magnet)
    },
    candidateCardClass(candidate) {
      const cls = ['cand-card', `status-${candidate.status}`]
      if (candidate.status === 'candidate' && !candidate.magnet) cls.push('nomag')
      if (this.selectedCandidateIds.includes(candidate.id)) cls.push('picked')
      return cls
    },
    actorInitial(candidate) {
      const name = (candidate.actress_name || '').trim()
      return name ? name.charAt(0) : '?'
    },
    actorAvatarStyle(candidate) {
      const seed = candidate.actress_id || candidate.actress_name || candidate.dvd_id || candidate.content_id || ''
      let h = 5381
      for (let i = 0; i < seed.length; i++) h = ((h << 5) + h + seed.charCodeAt(i)) & 0xffffffff
      const hue = Math.abs(h) % 360
      return { background: `linear-gradient(135deg, hsl(${hue} 60% 58%), hsl(${(hue + 38) % 360} 55% 46%))` }
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

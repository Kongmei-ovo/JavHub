<template>
  <AppleSkeleton
    v-if="loading"
    class="panel-state"
    variant="list"
    :items="4"
    label="补全任务加载中"
  />
  <AppleEmptyState
    v-else-if="!jobs.length"
    class="panel-state empty-inline"
    title="暂无补全任务"
    :description="emptyDescription"
    :next-step="emptyNextStep"
    action-label="刷新任务"
    secondary-action-label="补全作品"
    density="compact"
    @action="$emit('refresh')"
    @secondary-action="$emit('start-supplement')"
  />
  <div v-else class="ios-list job-list">
    <div class="job-queue-ledger" aria-label="当前任务状态概览">
      <div class="job-queue-summary">
        <strong>{{ jobQueueSummaryTotal }}</strong>
        <span>当前页任务</span>
        <small class="job-queue-total-label">{{ jobQueueTotalLabel }}</small>
      </div>
      <div class="job-queue-cards">
        <span
          v-for="row in jobQueueSummaryRows"
          :key="row.key"
          class="job-queue-card"
          :class="jobQueueSummaryClass(row)"
        >
          <b>{{ row.label }}</b>
          <em>{{ row.count }} 项</em>
          <small>{{ row.action }}</small>
        </span>
      </div>
    </div>
    <article v-for="job in jobs" :key="job.id" class="ios-row job-row">
      <div class="job-main">
        <div class="job-avatar">{{ jobAvatarLabel(job) }}</div>
        <div class="job-copy">
          <strong>{{ displayJobLabel(job) }}</strong>
          <span>#{{ job.id }} · {{ job.created_at ? new Date(job.created_at).toLocaleString() : '' }}</span>
          <small v-if="jobAttemptMeta(job)" class="job-meta">{{ jobAttemptMeta(job) }}</small>
          <small
            v-if="job.last_error"
            :class="job.status === 'failed' ? 'job-error' : 'job-warning'"
            :title="job.last_error"
          >
            {{ jobFailureSummary(job) }}
          </small>
          <div class="job-repair-lane" aria-label="任务修复状态">
            <span
              v-for="item in jobRepairLaneItems(job)"
              :key="item.label"
              class="job-repair-lane-item"
              :class="jobRepairLaneItemClass(item)"
            >
              <b>{{ item.label }}</b>
              <em>{{ item.value }}</em>
              <small>{{ item.detail }}</small>
            </span>
          </div>
        </div>
      </div>
      <div class="job-actions">
        <span class="status-pill" :class="`status-${job.status}`">{{ statusLabel(job.status) }}</span>
        <button
          v-if="job.local_actress_id && !actorContext"
          class="btn btn-ghost btn-sm"
          type="button"
          @click="$emit('actor', job)"
        >查看演员</button>
        <button
          v-if="job.status === 'failed'"
          class="btn btn-primary btn-sm"
          type="button"
          @click="$emit('retry', job.id)"
        >重试</button>
        <button
          v-if="job.status === 'queued' || job.status === 'running'"
          class="btn btn-ghost btn-sm"
          type="button"
          @click="$emit('cancel', job.id)"
        >取消</button>
      </div>
    </article>
  </div>
</template>

<script>
import AppleEmptyState from '../../components/AppleEmptyState.vue'
import AppleSkeleton from '../../components/AppleSkeleton.vue'
import {
  supplementJobFailureDiagnostics,
  supplementJobFailureSummary,
} from './supplementJobDiagnostics.js'

export default {
  name: 'SupplementJobList',
  components: { AppleEmptyState, AppleSkeleton },
  props: {
    jobs: { type: Array, default: () => [] },
    loading: { type: Boolean, default: false },
    actorContext: { type: Object, default: null },
    jobLabel: { type: Function, required: true },
    statusLabel: { type: Function, required: true },
    contextLabel: { type: String, default: '' },
    totalCount: { type: Number, default: 0 },
  },
  emits: ['retry', 'cancel', 'actor', 'refresh', 'start-supplement'],
  computed: {
    emptyDescription() {
      if (this.contextLabel) return this.contextLabel
      return this.actorContext
        ? '这个演员还没有补全任务记录。'
        : '当前队列筛选下没有任务记录。'
    },
    emptyNextStep() {
      return this.actorContext
        ? '可以先启动作品补全，或刷新任务队列等待后端写入新状态。'
        : '刷新队列确认最新状态，或回到演员工作台启动具体演员的补全任务。'
    },
    jobQueueSummaryTotal() {
      return this.jobs.length
    },
    jobQueueTotalLabel() {
      const total = this.totalCount || this.jobs.length
      return `筛选总量 ${total}`
    },
    jobQueueSummaryRows() {
      const counts = this.jobs.reduce((totals, job) => {
        const status = job?.status || 'unknown'
        totals[status] = (totals[status] || 0) + 1
        return totals
      }, {})
      return [
        { key: 'failed', label: '失败任务', count: counts.failed || 0, action: '优先重试', tone: 'danger' },
        { key: 'running', label: '运行中', count: counts.running || 0, action: '观察运行', tone: 'warning' },
        { key: 'queued', label: '等待执行', count: counts.queued || 0, action: '等待调度', tone: 'warning' },
        { key: 'succeeded', label: '已完成', count: counts.succeeded || 0, action: '归档完成', tone: 'ready' },
      ]
    },
  },
  methods: {
    isGfriendsAvatarSyncJob(job) {
      return job?.source === 'gfriends' && job?.job_type === 'actress_avatar_sync'
    },
    displayJobLabel(job) {
      if (this.isGfriendsAvatarSyncJob(job)) return 'gfriends 头像同步'
      return this.jobLabel(job)
    },
    jobAvatarLabel(job) {
      if (this.isGfriendsAvatarSyncJob(job)) return 'G'
      return job.source_actor_name?.slice(0, 1) || String(job.local_actress_id || '?').slice(0, 1)
    },
    jobAttemptMeta(job) {
      const pieces = []
      if (job.attempt_count) pieces.push(`尝试 ${job.attempt_count}/3`)
      if (job.status === 'queued' && job.next_run_at) {
        const next = new Date(job.next_run_at)
        if (!Number.isNaN(next.getTime()) && next.getTime() > Date.now() + 1000) {
          pieces.push(`下次 ${next.toLocaleTimeString()}`)
        }
      }
      return pieces.join(' · ')
    },
    jobRepairLaneItems(job) {
      return [
        {
          label: '任务状态',
          value: this.statusLabel(job.status),
          detail: this.jobStatusDetail(job),
          tone: job.status === 'failed' ? 'danger' : ['queued', 'running'].includes(job.status) ? 'warning' : 'ready',
        },
        {
          label: '尝试次数',
          value: `${job.attempt_count || 0}/3`,
          detail: job.next_run_at && job.status === 'queued' ? '等待执行' : '当前轮次',
          tone: (job.attempt_count || 0) >= 3 && job.status === 'failed' ? 'danger' : job.attempt_count ? 'warning' : 'ready',
        },
        {
          label: '错误摘要',
          value: this.jobErrorSummary(job),
          detail: job.last_error ? '查看来源' : '暂无错误',
          tone: job.last_error ? (job.status === 'failed' ? 'danger' : 'warning') : 'ready',
        },
        {
          label: '下一步',
          value: this.jobNextActionLabel(job),
          detail: this.jobNextActionDetail(job),
          tone: job.status === 'failed' ? 'danger' : ['queued', 'running'].includes(job.status) ? 'warning' : 'ready',
        },
      ]
    },
    jobRepairLaneItemClass(item) {
      return item.tone || 'warning'
    },
    jobQueueSummaryClass(row) {
      return row.tone || 'warning'
    },
    jobStatusDetail(job) {
      if (job.status === 'failed') return '需要人工处理'
      if (job.status === 'queued') return '等待执行'
      if (job.status === 'running') return '正在补全'
      if (job.status === 'succeeded') return '已完成'
      return '待观察'
    },
    jobErrorSummary(job) {
      return supplementJobFailureDiagnostics(job).summary
    },
    jobFailureSummary(job) {
      return supplementJobFailureSummary(job)
    },
    jobNextActionLabel(job) {
      if (job.status === 'failed') return '重试任务'
      if (job.status === 'queued') return '等待执行'
      if (job.status === 'running') return '观察进度'
      if (job.status === 'succeeded') return '归档完成'
      return '刷新队列'
    },
    jobNextActionDetail(job) {
      if (job.status === 'failed') return supplementJobFailureDiagnostics(job).nextActionDetail
      if (job.status === 'queued' && job.next_run_at) return this.jobAttemptMeta(job) || '等待执行'
      if (job.status === 'running') return '避免重复调度'
      if (job.status === 'succeeded') return '可继续字段修复'
      return '同步最新状态'
    },
  },
}
</script>

<style scoped>
.empty-inline {
  display: grid;
  gap: 4px;
  padding: 20px;
  color: var(--text-muted);
  text-align: center;
}

.ios-list {
  display: grid;
  gap: 8px;
}

.job-queue-ledger {
  display: grid;
  grid-template-columns: minmax(128px, 0.28fr) minmax(0, 1fr);
  gap: 8px;
  min-width: 0;
  padding: 10px;
  border: 1px solid var(--glass-control-border);
  border-radius: 14px;
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--material-glass-subtle);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}

.job-queue-summary {
  display: grid;
  align-content: center;
  gap: 3px;
  min-width: 0;
  min-height: 58px;
  padding: 8px 10px;
  border: 1px solid var(--badge-info-border);
  border-radius: 12px;
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--badge-info-bg);
}

.job-queue-summary strong {
  color: var(--badge-info-text);
  font-family: var(--font-mono);
  font-size: 22px;
  font-variant-numeric: tabular-nums;
}

.job-queue-summary span {
  color: var(--text-muted);
  font-size: 11px;
}

.job-queue-total-label {
  color: var(--text-muted);
  font-size: 10px;
  line-height: 1.25;
}

.job-queue-cards {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px;
  min-width: 0;
}

.job-queue-card {
  display: grid;
  gap: 2px;
  min-width: 0;
  min-height: 58px;
  padding: 8px 9px;
  border: 1px solid var(--glass-control-border);
  border-radius: 12px;
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--material-glass-control);
  box-shadow: var(--glass-inner-shadow);
}

.job-queue-card.danger {
  border-color: var(--badge-error-border);
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--badge-error-bg);
}

.job-queue-card.warning {
  border-color: var(--badge-warning-border);
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--badge-warning-bg);
}

.job-queue-card.ready {
  border-color: var(--badge-success-border);
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--badge-success-bg);
}

.job-queue-card b,
.job-queue-card em,
.job-queue-card small {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.job-queue-card b {
  color: var(--text-muted);
  font-size: 10px;
}

.job-queue-card em {
  color: var(--text-primary);
  font-size: 12px;
  font-style: normal;
  font-weight: 800;
}

.job-queue-card small {
  color: var(--text-muted);
  font-size: 10px;
}

.ios-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  content-visibility: auto;
  contain-intrinsic-size: 1px 76px;
  padding: 13px 14px;
  border: 1px solid var(--glass-control-border);
  border-radius: 16px;
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--material-glass-control);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  transition: transform var(--motion-fast), opacity var(--motion-fast);
}

.ios-row:hover {
  border-color: var(--glass-control-border-hover);
  background:
    var(--surface-specular-edge-strong),
    var(--surface-noise),
    var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow-hover);
  transform: translateY(-1px);
}

.ios-row:focus-within {
  border-color: var(--glass-control-border-hover);
  background:
    var(--surface-specular-edge-strong),
    var(--surface-noise),
    var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow-hover), var(--focus-ring);
  transform: translateY(-1px);
}

.job-main {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}

.job-avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  overflow: hidden;
  color: var(--text-secondary);
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--material-glass-subtle);
  border: 1px solid var(--glass-control-border);
  border-radius: 50%;
  box-shadow: var(--glass-inner-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  flex-shrink: 0;
  font-weight: 800;
}

.job-copy {
  display: grid;
  gap: 4px;
  min-width: 0;
}

.job-copy strong {
  color: var(--text-primary);
  font-size: 14px;
}

.job-copy span {
  color: var(--text-muted);
  font-size: 12px;
}

.job-copy small {
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.4;
  overflow-wrap: anywhere;
}

.job-copy small.job-error {
  color: var(--badge-error-text);
}

.job-copy small.job-warning {
  color: var(--badge-warning-text);
}

.job-repair-lane {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 6px;
  margin-top: 4px;
}

.job-repair-lane-item {
  display: grid;
  gap: 2px;
  min-width: 0;
  min-height: 54px;
  padding: 7px 8px;
  border: 1px solid var(--glass-control-border);
  border-radius: 10px;
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--material-glass-control);
  box-shadow: var(--glass-inner-shadow);
}

.job-repair-lane-item.danger {
  border-color: var(--badge-error-border);
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--badge-error-bg);
}

.job-repair-lane-item.warning {
  border-color: var(--badge-warning-border);
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--badge-warning-bg);
}

.job-repair-lane-item.ready {
  border-color: var(--badge-success-border);
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--badge-success-bg);
}

.job-repair-lane-item b,
.job-repair-lane-item em,
.job-repair-lane-item small {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.job-repair-lane-item b {
  color: var(--text-muted);
  font-size: 10px;
}

.job-repair-lane-item em {
  color: var(--text-primary);
  font-size: 11px;
  font-style: normal;
  font-weight: 800;
}

.job-repair-lane-item small {
  color: var(--text-muted);
  font-size: 10px;
}

.job-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 3px 9px;
  border: 1px solid var(--badge-info-border);
  border-radius: 999px;
  color: var(--badge-info-text);
  background: var(--surface-specular-edge), var(--surface-noise), var(--badge-info-bg);
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.status-succeeded {
  color: var(--badge-success-text);
  background: var(--surface-specular-edge), var(--surface-noise), var(--badge-success-bg);
  border-color: var(--badge-success-border);
}

.status-running,
.status-queued {
  color: var(--badge-warning-text);
  background: var(--surface-specular-edge), var(--surface-noise), var(--badge-warning-bg);
  border-color: var(--badge-warning-border);
}

.status-failed {
  color: var(--badge-error-text);
  background: var(--surface-specular-edge), var(--surface-noise), var(--badge-error-bg);
  border-color: var(--badge-error-border);
}

@media (max-width: 860px) {
  .job-queue-ledger {
    grid-template-columns: 1fr;
  }

  .job-queue-cards {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .ios-row,
  .job-actions {
    align-items: flex-start;
    flex-direction: column;
  }

  .job-actions {
    width: 100%;
  }

  .job-repair-lane {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>

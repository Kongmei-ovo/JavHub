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
  <div v-else class="job-list-wrap">
    <div class="job-ledger" aria-label="任务汇总">
      <div class="job-ledger-sum">
        <strong>{{ jobs.length }}</strong>
        <span>当前页任务</span>
      </div>
      <div class="job-ledger-cards">
        <span
          v-for="row in jobSummaryRows"
          :key="row.key"
          class="jl-card"
          :class="`jl-card-${row.key}`"
        >
          <b>{{ row.label }}</b>
          <em>{{ row.count }} 项</em>
        </span>
      </div>
    </div>

    <div class="job-card-list">
      <article v-for="job in jobs" :key="job.id" class="job-card">
        <div class="job-avatar" :style="avatarStyle(job)">{{ jobAvatarLabel(job) }}</div>
        <div class="job-copy">
          <strong class="job-title">{{ displayJobLabel(job) }}</strong>
          <span class="job-id">#{{ job.id }}<span v-if="job.created_at"> · {{ formatJobTime(job.created_at) }}</span></span>
          <small v-if="jobAttemptMeta(job)" class="job-attempt">{{ jobAttemptMeta(job) }}</small>
          <small
            v-if="job.last_error"
            :class="job.status === 'failed' ? 'job-error' : 'job-warning'"
            :title="job.last_error"
          >{{ jobFailureSummary(job) }}</small>
        </div>
        <div class="job-actions">
          <span class="status-pill" :class="`status-${job.status}`">{{ statusLabel(job.status) }}</span>
          <button
            v-if="job.local_actress_id && !actorContext"
            class="btn btn-quiet btn-sm"
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
  </div>
</template>

<script>
import AppleEmptyState from '../../components/AppleEmptyState.vue'
import AppleSkeleton from '../../components/AppleSkeleton.vue'
import { supplementJobFailureSummary } from './supplementJobDiagnostics.js'

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
      return this.actorContext ? '这个演员还没有补全任务记录。' : '当前队列筛选下没有任务记录。'
    },
    emptyNextStep() {
      return this.actorContext
        ? '可以先启动作品补全，或刷新任务队列等待后端写入新状态。'
        : '刷新队列确认最新状态，或回到演员工作台启动具体演员的补全任务。'
    },
    jobSummaryRows() {
      const counts = this.jobs.reduce((acc, job) => {
        const s = job?.status || 'unknown'
        acc[s] = (acc[s] || 0) + 1
        return acc
      }, {})
      return [
        { key: 'running', label: '运行中', count: counts.running || 0 },
        { key: 'queued', label: '排队中', count: counts.queued || 0 },
        { key: 'succeeded', label: '已完成', count: counts.succeeded || 0 },
        { key: 'failed', label: '失败', count: counts.failed || 0 },
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
      const name = job.source_actor_name || String(job.local_actress_id || job.id || '?')
      return name.slice(0, 1)
    },
    avatarStyle(job) {
      const seed = String(job.local_actress_id || job.source_actor_name || job.id || 'jh')
      let h = 5381
      for (let i = 0; i < seed.length; i++) h = ((h << 5) + h + seed.charCodeAt(i)) & 0xffffffff
      const hue = Math.abs(h) % 360
      return { background: `linear-gradient(135deg, hsl(${hue} 60% 58%), hsl(${(hue + 38) % 360} 55% 46%))` }
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
      if (job.total_found != null && job.status === 'succeeded') pieces.push(`命中 ${job.total_found}`)
      return pieces.join(' · ')
    },
    formatJobTime(value) {
      if (!value) return ''
      const t = new Date(value).getTime()
      if (Number.isNaN(t)) return ''
      const m = Math.round((Date.now() - t) / 60000)
      if (m < 1) return '刚刚'
      if (m < 60) return `${m} 分钟前`
      const h = Math.round(m / 60)
      if (h < 24) return `${h} 小时前`
      const d = new Date(value)
      return `${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
    },
    jobFailureSummary(job) {
      return supplementJobFailureSummary(job)
    },
  },
}
</script>

<style scoped>
.panel-state { margin: 14px 0 0; }
.empty-inline {
  display: grid;
  gap: 4px;
  padding: 28px;
  color: var(--text-muted);
  text-align: center;
}

.job-list-wrap {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* 汇总 ledger */
.job-ledger {
  display: flex;
  align-items: center;
  gap: 20px;
  padding: 14px 18px;
  border-radius: var(--radius-card);
  background: var(--card-2);
  border: 1px solid var(--hairline);
  flex-wrap: wrap;
}

.job-ledger-sum {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex-shrink: 0;
  min-width: 84px;
}

.job-ledger-sum strong {
  font-size: 28px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: -0.4px;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.job-ledger-sum span {
  margin-top: 4px;
  font-size: 11px;
  color: var(--text-muted);
}

.job-ledger-cards {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.jl-card {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 6px 14px;
  border-radius: 10px;
  background: var(--card);
  border: 1px solid var(--hairline);
  min-width: 76px;
}

.jl-card b {
  font-size: 10px;
  font-weight: 600;
  color: var(--text-muted);
  letter-spacing: 0.1px;
}

.jl-card em {
  font-size: 13px;
  font-style: normal;
  font-weight: 700;
  color: var(--text-primary);
  font-variant-numeric: tabular-nums;
}

.jl-card-running { border-color: rgba(var(--accent-rgb), 0.3); }
.jl-card-running em { color: var(--accent); }
.jl-card-queued { border-color: rgba(var(--warn-rgb), 0.3); }
.jl-card-queued em { color: var(--warn); }
.jl-card-failed { border-color: rgba(var(--bad-rgb), 0.3); }
.jl-card-failed em { color: var(--bad); }
.jl-card-succeeded em { color: var(--ok); }

/* job cards */
.job-card-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.job-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 14px 16px;
  border-radius: var(--radius-card);
  background: var(--card);
  border: 1px solid var(--hairline);
  transition: border-color var(--motion-fast);
}

.job-card:hover { border-color: var(--hairline-strong); }

.job-avatar {
  width: 44px;
  height: 44px;
  border-radius: 999px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  font-weight: 700;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.18);
}

.job-copy {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.job-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.job-id {
  font-size: 11px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.job-attempt {
  font-size: 11px;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}

.job-error { color: var(--bad); font-size: 11px; }
.job-warning { color: var(--warn); font-size: 11px; }

.job-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  flex-wrap: wrap;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 3px 10px;
  border: 1px solid var(--badge-info-border);
  border-radius: 999px;
  color: var(--badge-info-text);
  background: var(--surface-specular-edge), var(--surface-noise), var(--badge-info-bg);
  font-size: 11px;
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

.btn-quiet {
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 11px;
  padding: 4px 8px;
  box-shadow: none;
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
}

.btn-quiet:hover { color: var(--text-primary); background: var(--card-2); }

@media (max-width: 860px) {
  .job-card {
    flex-wrap: wrap;
    padding: 12px;
  }
  .job-actions {
    width: 100%;
    justify-content: flex-end;
  }
}
</style>

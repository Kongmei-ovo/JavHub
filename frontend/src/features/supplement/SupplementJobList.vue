<template>
  <div v-if="loading" class="loading-wrap">
    <div class="spinner-large"></div>
  </div>
  <div v-else-if="!jobs.length" class="empty-inline">暂无任务</div>
  <div v-else class="ios-list job-list">
    <article v-for="job in jobs" :key="job.id" class="ios-row job-row">
      <div class="job-main">
        <div class="job-avatar">{{ jobAvatarLabel(job) }}</div>
        <div class="job-copy">
          <strong>{{ displayJobLabel(job) }}</strong>
          <span>#{{ job.id }} · {{ job.created_at ? new Date(job.created_at).toLocaleString() : '' }}</span>
          <small v-if="jobAttemptMeta(job)" class="job-meta">{{ jobAttemptMeta(job) }}</small>
          <small v-if="job.last_error" :class="job.status === 'failed' ? 'job-error' : 'job-warning'">
            {{ job.last_error }}
          </small>
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
export default {
  name: 'SupplementJobList',
  props: {
    jobs: { type: Array, default: () => [] },
    loading: { type: Boolean, default: false },
    actorContext: { type: Object, default: null },
    jobLabel: { type: Function, required: true },
    statusLabel: { type: Function, required: true },
  },
  emits: ['retry', 'cancel', 'actor'],
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
  },
}
</script>

<style scoped>
.loading-wrap {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 140px;
}

.spinner-large {
  width: 28px;
  height: 28px;
  border: 2px solid var(--glass-control-border);
  border-top-color: var(--badge-info-text);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.empty-inline {
  padding: 20px;
  color: var(--text-muted);
  text-align: center;
}

.ios-list {
  display: grid;
  gap: 8px;
}

.ios-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
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
  transition: transform var(--motion-fast), background var(--motion-fast), border-color var(--motion-fast), box-shadow var(--motion-fast);
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
  box-shadow: var(--glass-control-shadow-hover), 0 0 0 3px rgba(var(--accent-rgb), 0.12);
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
  background: var(--badge-info-bg);
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.status-succeeded {
  color: var(--badge-success-text);
  background: var(--badge-success-bg);
  border-color: var(--badge-success-border);
}

.status-running,
.status-queued {
  color: var(--badge-warning-text);
  background: var(--badge-warning-bg);
  border-color: var(--badge-warning-border);
}

.status-failed {
  color: var(--badge-error-text);
  background: var(--badge-error-bg);
  border-color: var(--badge-error-border);
}

.btn-sm {
  min-height: 36px;
  padding: 8px 12px;
  font-size: 12px;
}

@media (max-width: 860px) {
  .ios-row,
  .job-actions {
    align-items: flex-start;
    flex-direction: column;
  }

  .job-actions {
    width: 100%;
  }
}
</style>

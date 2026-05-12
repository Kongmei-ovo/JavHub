<template>
  <div v-if="loading" class="loading-wrap">
    <div class="spinner-large"></div>
  </div>
  <div v-else-if="!jobs.length" class="empty-inline">暂无任务</div>
  <div v-else class="ios-list job-list">
    <article v-for="job in jobs" :key="job.id" class="ios-row job-row">
      <div class="job-main">
        <div class="job-avatar">{{ job.source_actor_name?.slice(0, 1) || String(job.local_actress_id || '?').slice(0, 1) }}</div>
        <div class="job-copy">
          <strong>{{ jobLabel(job) }}</strong>
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

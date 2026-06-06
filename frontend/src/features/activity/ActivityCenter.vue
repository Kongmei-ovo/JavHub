<template>
  <section class="activity-center" :class="{ expanded: isExpanded }" aria-label="后台活动中心">
    <button
      class="activity-pill"
      type="button"
      :aria-expanded="isExpanded"
      aria-controls="activity-center-panel"
      @click="toggleExpanded"
    >
      <span class="activity-pill-icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
          <path d="M4 14h4l2-8 4 14 2-6h4" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </span>
      <span>{{ runningSummary }}</span>
    </button>

    <transition name="activity-panel">
      <div v-if="isExpanded" id="activity-center-panel" class="activity-panel" role="region" aria-label="最近后台作业">
        <div class="activity-panel-head">
          <div>
            <h2>Activity Center</h2>
            <p>{{ connected ? '实时同步中' : retrySummary }}</p>
          </div>
          <span class="activity-count">{{ recentJobs.length }}</span>
        </div>

        <div v-if="recentJobs.length" class="activity-job-list">
          <article v-for="job in recentJobs" :key="job.id" class="activity-job">
            <div class="activity-job-main">
              <div class="activity-job-title">
                <span class="activity-kind">{{ job.kind || 'job' }}</span>
                <strong>{{ job.label || job.kind || `Job #${job.id}` }}</strong>
              </div>
              <span class="activity-time">{{ jobTime(job) }}</span>
            </div>
            <div
              class="activity-job-progressbar"
              role="progressbar"
              :aria-valuenow="job.progress"
              aria-valuemin="0"
              aria-valuemax="100"
              :aria-label="`${job.label || job.kind || '作业'}进度`"
            >
              <span :style="{ transform: `scaleX(${Math.max(0, Math.min(100, job.progress || 0)) / 100})` }"></span>
            </div>
            <div class="activity-job-meta">
              <span class="activity-status" :class="`status-${job.status || 'unknown'}`">{{ statusLabel(job.status) }}</span>
              <span>{{ job.progress }}%</span>
            </div>
          </article>
        </div>

        <div v-else class="activity-empty">
          <span>暂无后台作业</span>
        </div>
      </div>
    </transition>
  </section>
</template>

<script>
import { computed, ref, watch } from 'vue'
import { useJobStream } from './useJobStream.js'
import './activityCenter.css'

const STATUS_LABELS = {
  queued: '排队中',
  running: '进行中',
  completed: '已完成',
  failed: '失败',
  canceled: '已取消',
}

export default {
  name: 'ActivityCenter',
  props: {
    expanded: { type: Boolean, default: undefined },
    initialExpanded: { type: Boolean, default: false },
  },
  emits: ['update:expanded'],
  setup(props, { emit }) {
    const localExpanded = ref(Boolean(props.initialExpanded))
    const { orderedJobs, runningJobs, connected, nextRetryDelayMs } = useJobStream()
    const isExpanded = computed(() => props.expanded === undefined ? localExpanded.value : props.expanded)
    const recentJobs = computed(() => orderedJobs.value.slice(0, 10))
    const runningSummary = computed(() => `${runningJobs.value.length} 个进行中`)
    const retrySummary = computed(() => nextRetryDelayMs.value ? `${Math.round(nextRetryDelayMs.value / 1000)} 秒后重连` : '等待连接')

    watch(() => props.expanded, value => {
      if (value !== undefined) localExpanded.value = value
    })

    const setExpanded = (value) => {
      localExpanded.value = value
      emit('update:expanded', value)
    }
    const toggleExpanded = () => setExpanded(!isExpanded.value)
    const statusLabel = (status) => STATUS_LABELS[status] || status || '未知'
    const jobTime = (job) => {
      const value = job.finished_at || job.started_at || job.created_at
      if (!value) return ''
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return ''
      return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    }

    return {
      connected,
      isExpanded,
      jobTime,
      recentJobs,
      retrySummary,
      runningSummary,
      statusLabel,
      toggleExpanded,
    }
  },
}
</script>

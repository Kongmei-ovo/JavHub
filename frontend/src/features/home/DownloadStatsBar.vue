<template>
  <div class="stats-bar">
    <div v-for="item in statusCards" :key="item.status" class="stat-card" @click="$emit('select-status', item.status)">
      <div :class="['stat-icon', item.status]">
        <svg v-if="item.status === 'pending'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="12" cy="12" r="10"/>
          <polyline points="12 6 12 12 16 14"/>
        </svg>
        <svg v-else-if="item.status === 'downloading'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
          <polyline points="7 10 12 15 17 10"/>
          <line x1="12" y1="15" x2="12" y2="3"/>
        </svg>
        <svg v-else-if="item.status === 'completed'" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
          <polyline points="22 4 12 14.01 9 11.01"/>
        </svg>
        <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="12" cy="12" r="10"/>
          <line x1="15" y1="9" x2="9" y2="15"/>
          <line x1="9" y1="9" x2="15" y2="15"/>
        </svg>
      </div>
      <div class="stat-info">
        <div class="stat-num" :class="{ 'animate-in': statsLoaded && item.status === 'pending' }">{{ item.value }}</div>
        <div class="stat-label">{{ item.label }}</div>
      </div>
    </div>
  </div>
  <CandidateOverview :candidate-stats="candidateStats" @open-preset="$emit('open-preset', $event)" />
</template>

<script>
import CandidateOverview from './CandidateOverview.vue'

export default {
  name: 'DownloadStatsBar',
  components: { CandidateOverview },
  props: {
    stats: { type: Object, required: true },
    candidateStats: { type: Object, required: true },
    statsLoaded: { type: Boolean, default: false },
  },
  emits: ['select-status', 'open-preset'],
  computed: {
    statusCards() {
      return [
        { status: 'pending', label: '待处理', value: this.stats.pending || 0 },
        { status: 'downloading', label: '下载中', value: this.stats.downloading || 0 },
        { status: 'completed', label: '已完成', value: this.stats.completed || 0 },
        { status: 'failed', label: '失败', value: this.stats.failed || 0 },
      ]
    },
  },
}
</script>

<style scoped src="./home.css"></style>

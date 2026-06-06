<template>
  <div class="candidate-overview">
    <button class="candidate-metric" type="button" @click="$emit('open-preset', { status: 'candidate', source: '' })">
      <span class="metric-value">{{ candidateStats.candidate || 0 }}</span>
      <span class="metric-label">待确认候选</span>
    </button>
    <button class="candidate-metric" type="button" @click="$emit('open-preset', { status: 'candidate', needs_magnet: true, source: '' })">
      <span class="metric-value">{{ candidateStats.needs_magnet || 0 }}</span>
      <span class="metric-label">待补磁力</span>
    </button>
    <button class="candidate-metric" type="button" @click="$emit('open-preset', { status: 'candidate', needs_magnet: false, source: '' })">
      <span class="metric-value">{{ readyCandidateCount }}</span>
      <span class="metric-label">可批准</span>
    </button>
    <button class="candidate-metric" type="button" @click="$emit('open-preset', { status: 'candidate', source: 'subscription' })">
      <span class="metric-value">{{ candidateStats.candidate_by_source?.subscription || 0 }}</span>
      <span class="metric-label">订阅发现</span>
    </button>
    <button class="candidate-metric" type="button" @click="$emit('open-preset', { status: 'candidate', source: 'inventory' })">
      <span class="metric-value">{{ candidateStats.candidate_by_source?.inventory || 0 }}</span>
      <span class="metric-label">库存发现</span>
    </button>
    <button class="candidate-metric" type="button" @click="$emit('open-preset', { status: 'candidate', source: 'supplement' })">
      <span class="metric-value">{{ candidateStats.candidate_by_source?.supplement || 0 }}</span>
      <span class="metric-label">补全发现</span>
    </button>
  </div>
</template>

<script>
export default {
  name: 'CandidateOverview',
  props: {
    candidateStats: { type: Object, required: true },
  },
  emits: ['open-preset'],
  computed: {
    readyCandidateCount() {
      return Math.max((this.candidateStats.candidate || 0) - (this.candidateStats.needs_magnet || 0), 0)
    },
  },
}
</script>

<style scoped src="./home.css"></style>

<template>
  <div class="operations-page page-shell page-shell--workspace">
    <header class="operations-header operations-hero">
      <div class="header-copy">
        <span class="hero-eyebrow">系统工作台</span>
        <h1>运营总览</h1>
        <p>库存、映射、补全和下载候选的闭环状态。</p>
      </div>
      <div class="hero-stat-grid" aria-label="首要运营指标">
        <button v-for="metric in statusMetrics" :key="metric.key" class="hero-stat" :class="{ urgent: metric.urgent }" type="button" @click="openStatusMetric(metric.key)">
          <strong>{{ metric.value }}</strong>
          <span>{{ metric.label }}</span>
          <small>{{ metric.hint }}</small>
        </button>
      </div>
      <div class="header-actions">
        <button class="btn btn-ghost btn-sm" type="button" @click="$router.push('/settings')">策略设置</button>
        <button class="btn btn-primary btn-sm" type="button" @click="setActiveSegment('diagnostics')">诊断记录</button>
      </div>
    </header>

    <nav class="operations-segments apple-surface" aria-label="运营总览视图">
      <button
        v-for="segment in operationsSegments"
        :key="segment.key"
        type="button"
        :class="{ active: activeSegment === segment.key }"
        @click="setActiveSegment(segment.key)"
      >
        <span>{{ segment.label }}</span>
        <small>{{ segment.hint }}</small>
      </button>
    </nav>

    <!-- 每张卡只出现在一个分段：处理=人工决策，管道=数据流转，诊断=健康记录 -->
    <section v-if="activeSegment === 'workbench'" class="operations-workbench priority-board" aria-label="处理">
      <CandidateAutoCard class="workbench-primary" />
      <MappingCard />
    </section>

    <section v-else-if="activeSegment === 'system'" class="system-layout" aria-label="数据管道">
      <PipelineCard />
      <SchedulerCard />
      <SnapshotCard />
    </section>

    <section v-else-if="activeSegment === 'diagnostics'" class="diagnostic-grid" aria-label="诊断与记录">
      <DataQualityCard class="diagnostic-wide" />
      <CacheCard />
    </section>
  </div>
</template>

<script>
import api from '../api'
import PipelineCard from '../features/operations/PipelineCard.vue'
import SchedulerCard from '../features/operations/SchedulerCard.vue'
import DataQualityCard from '../features/operations/DataQualityCard.vue'
import CandidateAutoCard from '../features/operations/CandidateAutoCard.vue'
import SnapshotCard from '../features/operations/SnapshotCard.vue'
import MappingCard from '../features/operations/MappingCard.vue'
import CacheCard from '../features/operations/CacheCard.vue'

export default {
  name: 'Operations',
  components: {
    PipelineCard,
    SchedulerCard,
    CacheCard,
    DataQualityCard,
    CandidateAutoCard,
    SnapshotCard,
    MappingCard,
  },
  data() {
    return {
      activeSegment: 'workbench',
      metrics: {
        candidate: null,
        needs_magnet: null,
        missing: null,
        data_quality: null,
        mapping: null,
        supplement_failed: null,
      },
    }
  },
  computed: {
    operationsSegments() {
      return [
        { key: 'workbench', label: '处理', hint: '候选与映射' },
        { key: 'system', label: '数据管道', hint: '链路与调度' },
        { key: 'diagnostics', label: '诊断记录', hint: '质量与缓存' },
      ]
    },
    statusMetrics() {
      const value = key => (this.metrics[key] === null ? '—' : String(this.metrics[key]))
      return [
        { key: 'candidate', label: '待确认候选', value: value('candidate'), hint: '打开队列', urgent: false },
        { key: 'needs_magnet', label: '待补磁力', value: value('needs_magnet'), hint: '需要补全', urgent: false },
        { key: 'missing', label: '库存缺口', value: value('missing'), hint: '片库整理', urgent: false },
        { key: 'data_quality', label: '数据质量', value: value('data_quality'), hint: '优先修复', urgent: Number(this.metrics.data_quality) > 0 },
        { key: 'mapping', label: '映射待审核', value: value('mapping'), hint: '覆盖状态', urgent: false },
        { key: 'supplement_failed', label: '补全失败', value: value('supplement_failed'), hint: '补全管理', urgent: Number(this.metrics.supplement_failed) > 0 },
      ]
    },
  },
  mounted() {
    this.activeSegment = this.segmentFromRoute()
    this.loadStatusMetrics()
  },
  watch: {
    '$route.query.tab'() {
      this.activeSegment = this.segmentFromRoute()
    },
  },
  methods: {
    async loadStatusMetrics() {
      const [candidateResp, missingResp, mappingResp, supplementResp, qualityResp] = await Promise.allSettled([
        api.getDownloadCandidateSummary({ status: 'candidate' }),
        api.getMissingActresses(),
        api.getActorMappingSummary(),
        api.getSupplementStats(),
        api.getDataQualityOverview(8),
      ])
      if (candidateResp.status === 'fulfilled') {
        const summary = candidateResp.value.data || {}
        this.metrics.candidate = Number(summary.candidate ?? summary.total ?? 0)
        this.metrics.needs_magnet = Number(summary.needs_magnet || 0)
      }
      if (missingResp.status === 'fulfilled') {
        this.metrics.missing = Number(missingResp.value.data?.total || 0)
      }
      if (mappingResp.status === 'fulfilled') {
        this.metrics.mapping = Number(mappingResp.value.data?.candidate || 0)
      }
      if (supplementResp.status === 'fulfilled') {
        this.metrics.supplement_failed = Number(supplementResp.value.data?.jobs_by_status?.failed || 0)
      }
      if (qualityResp.status === 'fulfilled') {
        const issues = qualityResp.value.data?.issues || qualityResp.value.data?.data || []
        this.metrics.data_quality = Array.isArray(issues) ? issues.length : 0
      }
    },
    segmentFromRoute() {
      const tab = this.$route.query.tab
      return ['workbench', 'system', 'diagnostics'].includes(tab) ? tab : 'workbench'
    },
    setActiveSegment(segment) {
      if (!['workbench', 'system', 'diagnostics'].includes(segment)) return
      this.activeSegment = segment
      this.$router.replace({ query: { ...this.$route.query, tab: segment } })
    },
    openStatusMetric(key) {
      const actions = {
        candidate: () => this.$router.push({ path: '/candidates', query: { status: 'candidate' } }),
        needs_magnet: () => this.$router.push({ path: '/candidates', query: { status: 'candidate', needs_magnet: '1' } }),
        missing: () => this.$router.push({ path: '/library-organize', query: { tab: 'inventory' } }),
        data_quality: () => this.setActiveSegment('diagnostics'),
        mapping: () => this.$router.push({ path: '/library-organize', query: { tab: 'mapping' } }),
        supplement_failed: () => this.$router.push('/supplement'),
      }
      actions[key]?.()
    },
  },
}
</script>

<style scoped src="../features/operations/operations.css"></style>

<template>
  <div class="monitor-page page-shell page-shell--workspace">
    <header class="monitor-header">
      <span class="monitor-eyebrow">系统工作台</span>
      <h1>系统监控</h1>
      <p>状态快照与运行日志合并在此：先看健康，异常一键钻进日志。</p>
    </header>

    <nav class="segmented-control" aria-label="系统监控视图">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        type="button"
        :class="{ active: activeTab === tab.key, 'segment-warning': tab.warn }"
        @click="setTab(tab.key)"
      >
        <span class="segment-label">{{ tab.label }}</span>
        <span v-if="tab.badge" class="segment-count">{{ tab.badge }}</span>
      </button>
    </nav>

    <section class="monitor-view">
      <keep-alive>
        <component :is="activeComponent" @summary="onSummary" />
      </keep-alive>
    </section>
  </div>
</template>

<script>
import OverviewPanel from '../features/operations/OverviewPanel.vue'
import LogStreamPanel from '../features/operations/LogStreamPanel.vue'

export default {
  name: 'SystemMonitor',
  components: { OverviewPanel, LogStreamPanel },
  data() {
    return {
      // 由 OverviewPanel 加载完后通过 @summary 回传，给 tab 标签挂活信息。
      monitorSummary: { status: '', degraded: false, errorCount: 0 },
    }
  },
  computed: {
    activeTab() {
      return this.$route.query.tab === 'logs' ? 'logs' : 'overview'
    },
    activeComponent() {
      return this.activeTab === 'logs' ? 'LogStreamPanel' : 'OverviewPanel'
    },
    tabs() {
      const err = Number(this.monitorSummary.errorCount || 0)
      return [
        { key: 'overview', label: '总览', badge: this.monitorSummary.status || '', warn: Boolean(this.monitorSummary.degraded) },
        { key: 'logs', label: '日志', badge: err > 0 ? String(err) : '', warn: err > 0 },
      ]
    },
  },
  methods: {
    setTab(key) {
      if (key === this.activeTab) return
      const query = { ...this.$route.query, tab: key }
      // 离开日志时清掉来自「近期告警」卡的临时筛选，避免残留。
      if (key !== 'logs') { delete query.level; delete query.q }
      this.$router.replace({ path: '/operations', query })
    },
    onSummary(summary) {
      this.monitorSummary = { status: '', degraded: false, errorCount: 0, ...summary }
    },
  },
}
</script>

<style scoped src="../features/operations/systemMonitor.css"></style>

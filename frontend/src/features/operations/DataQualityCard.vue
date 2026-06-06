<template>
  <article class="workbench-panel data-quality-block" aria-label="数据质量">
    <div class="panel-head">
      <div>
        <h2>数据质量优先级</h2>
        <p>{{ loading ? '数据质量加载中。' : dataQualitySummary }}</p>
      </div>
      <button class="btn btn-ghost btn-sm" type="button" @click="$router.push('/supplement')">补全管理</button>
    </div>

    <AppleSkeleton v-if="loading && !overview" class="loading-panel console-state" variant="list" :items="4" label="数据质量加载中" />
    <AppleErrorState v-else-if="error" class="empty-panel console-state" title="数据质量暂不可用" :description="error" next-step="可以刷新数据质量卡片，或打开补全管理查看修复队列。" retry-label="重试" secondary-action-label="补全管理" source-label="Data Quality API" @retry="loadOverview" @secondary-action="$router.push('/supplement')" />
    <AppleEmptyState v-else-if="!topDataQualityIssues.length" class="empty-panel console-state" title="暂无高优先级问题" description="当前没有需要优先修复的数据质量问题。" next-step="可以继续观察补全队列，或切换到补全管理检查作品字段。" action-label="补全管理" density="compact" @action="$router.push('/supplement')" />
    <div v-else class="compact-list">
      <div v-for="issue in topDataQualityIssues" :key="issue.id" class="compact-row quality-issue-row">
        <span>{{ issue.title }}</span>
        <strong>{{ issue.score }}</strong>
        <small>{{ issue.summary }}</small>
        <div v-if="issueRepairMetaItems(issue).length" class="quality-progress-meta">
          <template v-for="(item, index) in issueRepairMetaItems(issue)" :key="item"><span v-if="index > 0" class="quality-progress-separator" aria-hidden="true"> · </span><span class="quality-progress">{{ item }}</span></template>
        </div>
        <div v-if="issueRepairActions(issue).length" class="quality-progress-actions">
          <button v-for="action in issueRepairActions(issue)" :key="action.route || action.label" class="quality-progress-action" type="button" @click.stop="openDataQualityRepairAction(action, $event)">{{ action.label }}</button>
        </div>
      </div>
    </div>
  </article>
</template>

<script>
import api from '../../api'
import AppleSkeleton from '../../components/AppleSkeleton.vue'
import AppleEmptyState from '../../components/AppleEmptyState.vue'
import AppleErrorState from '../../components/AppleErrorState.vue'

export default {
  name: 'DataQualityCard',
  components: { AppleSkeleton, AppleEmptyState, AppleErrorState },
  data() {
    return {
      overview: null,
      loading: false,
      error: '',
    }
  },
  computed: {
    topDataQualityIssues() {
      return (this.overview?.data_quality?.issues || this.overview?.issues || []).slice(0, 4)
    },
    dataQualitySummary() {
      const summary = this.overview?.data_quality?.summary || this.overview?.summary || {}
      const total = Number(summary.total_issues || 0)
      const high = Number(summary.high || 0) + Number(summary.critical || 0)
      if (!total) return '暂无问题'
      return `${total} 项 · 高优先 ${high}`
    },
  },
  mounted() {
    this.loadOverview()
  },
  methods: {
    async loadOverview() {
      this.loading = true
      this.error = ''
      try {
        const resp = await api.getDataQualityOverview(8)
        this.overview = resp.data
      } catch (e) {
        this.error = e.response?.data?.detail || e.message || '加载失败'
      } finally {
        this.loading = false
      }
    },
    openDataQualityIssue(issue) {
      const route = issue?.action?.route
      if (!route) return
      const [path, queryString = ''] = String(route).split('?')
      const query = Object.fromEntries(new URLSearchParams(queryString))
      if (issue?.type === 'low_quality_cover' && path === '/supplement' && !query.quality) {
        Object.assign(query, { tab: 'movies', quality: 'missing_cover' })
      }
      this.$router.push({ path, query })
    },
    openDataQualityRepairAction(action, event) {
      event?.stopPropagation?.()
      this.openDataQualityRoute(action?.route)
    },
    openDataQualityRoute(route) {
      if (!route) return
      const [path, queryString = ''] = String(route).split('?')
      const query = Object.fromEntries(new URLSearchParams(queryString))
      this.$router.push({ path, query })
    },
    issueRepairProgressLabel(issue) { return issue?.repair_progress?.label || '' },
    issueRepairEventLabel(issue) { return issue?.repair_progress?.event_label || '' },
    issueRepairReasonLabel(issue) { return issue?.repair_progress?.reason_label || '' },
    issueRepairProviderLabel(issue) { return issue?.repair_progress?.provider_label || '' },
    issueRepairLocalLabel(issue) { return issue?.repair_progress?.local_label || '' },
    issueRepairLocalSourceLabel(issue) { return issue?.repair_progress?.local_source_label || '' },
    issueRepairMetaItems(issue) {
      return [
        issue?.priority_reason,
        this.issueRepairProgressLabel(issue),
        this.issueRepairEventLabel(issue),
        this.issueRepairReasonLabel(issue),
        this.issueRepairProviderLabel(issue),
        this.issueRepairLocalLabel(issue),
        this.issueRepairLocalSourceLabel(issue),
      ].filter(Boolean)
    },
    issueRepairActions(issue) {
      const primaryRepairAction = issue?.repair_progress?.action?.route ? issue.repair_progress.action : null
      const actions = [
        issue?.action,
        primaryRepairAction,
        issue?.repair_progress?.reason_action,
        ...this.issueRepairEventActions(issue),
        ...this.issueRepairReasonActions(issue),
        ...this.issueRepairProviderActions(issue),
        ...this.issueRepairLocalActions(issue),
      ].filter(action => action?.route)
      const seen = new Set()
      return actions.filter((action) => {
        const key = action.route || action.label
        if (seen.has(key)) return false
        seen.add(key)
        return true
      })
    },
    issueRepairEventActions(issue) {
      return Array.isArray(issue?.repair_progress?.event_actions) ? issue.repair_progress.event_actions.filter(action => action?.route) : []
    },
    issueRepairReasonActions(issue) {
      return Array.isArray(issue?.repair_progress?.reason_actions) ? issue.repair_progress.reason_actions.filter(action => action?.route) : []
    },
    issueRepairProviderActions(issue) {
      return Array.isArray(issue?.repair_progress?.provider_actions) ? issue.repair_progress.provider_actions.filter(action => action?.route) : []
    },
    issueRepairLocalActions(issue) {
      return Array.isArray(issue?.repair_progress?.local_actions) ? issue.repair_progress.local_actions.filter(action => action?.route) : []
    },
  },
}
</script>

<style scoped src="./operations.css"></style>

<template>
  <article class="workbench-panel mapping-card" aria-label="演员映射">
    <div class="panel-head">
      <div>
        <h2>演员映射</h2>
        <p>{{ mappingSummaryText }}</p>
      </div>
      <div class="panel-actions">
        <button class="btn btn-ghost btn-sm" type="button" @click="goLibraryOrganize('mapping')">映射审核</button>
        <button class="btn btn-ghost btn-sm" type="button" @click="loadOverview">刷新</button>
      </div>
    </div>

    <AppleSkeleton v-if="loading && !overview" class="loading-panel console-state" variant="list" :items="4" label="演员映射加载中" />
    <AppleErrorState v-else-if="error && !overview" class="empty-panel console-state" title="演员映射加载失败" :description="error" next-step="可以刷新映射卡片，或直接打开映射审核。" retry-label="重试" secondary-action-label="映射审核" source-label="Mapping API" @retry="loadOverview" @secondary-action="goLibraryOrganize('mapping')" />
    <AppleEmptyState v-else-if="!overview" class="empty-panel console-state" title="暂无演员映射状态" description="后端还没有返回映射覆盖率和待审状态。" next-step="可以打开映射审核，或先完成片库整理快照。" action-label="映射审核" density="compact" @action="goLibraryOrganize('mapping')" />
    <template v-else>
    <div class="state-grid">
      <button class="state-item" type="button" @click="goLibraryOrganize('mapping')">
        <span>映射待审核</span>
        <strong>{{ mapping.candidate || 0 }}</strong>
      </button>
      <div class="state-item">
        <span>已确认</span>
        <strong>{{ mapping.confirmed || mapping.mapped || 0 }}</strong>
      </div>
      <div class="state-item" :class="{ warning: (mapping.unmapped || 0) > 0 }">
        <span>未映射</span>
        <strong>{{ mapping.unmapped || 0 }}</strong>
      </div>
      <div class="state-item">
        <span>覆盖率</span>
        <strong>{{ coverageText }}</strong>
      </div>
      <button class="state-item" type="button" @click="goLibraryOrganize('mapping')">
        <span>自动匹配</span>
        <strong>{{ mapping.auto_match?.auto_match_after_collect ? '采集后自动匹配' : '手动匹配' }}</strong>
      </button>
      <div class="state-item">
        <span>快照键</span>
        <strong>{{ overview?.snapshot?.snapshot_key || mapping.snapshot_key || '无快照' }}</strong>
      </div>
    </div>

    <div class="action-grid action-grid-compact">
      <button v-for="action in mappingActions" :key="action.key" class="action-card" type="button" @click="goWorkbenchAction(action)">
        <span>{{ action.label }}</span>
        <strong>{{ action.title }}</strong>
        <small>{{ action.hint }}</small>
      </button>
    </div>
    <p v-if="error" class="muted cache-error">{{ error }}</p>
    </template>
  </article>
</template>

<script>
import api from '../../api'
import AppleSkeleton from '../../components/AppleSkeleton.vue'
import AppleEmptyState from '../../components/AppleEmptyState.vue'
import AppleErrorState from '../../components/AppleErrorState.vue'

export default {
  name: 'MappingCard',
  components: { AppleSkeleton, AppleEmptyState, AppleErrorState },
  data() {
    return {
      overview: null,
      loading: false,
      error: '',
    }
  },
  computed: {
    mapping() {
      return this.overview?.mapping || {}
    },
    coverageText() {
      return `${Math.round((Number(this.mapping.coverage || 0)) * 100)}%`
    },
    mappingSummaryText() {
      if (this.loading && !this.overview) return '映射状态加载中。'
      if (this.error) return `映射状态加载失败：${this.error}`
      return `${this.mapping.candidate || 0} 个待审 · 覆盖率 ${this.coverageText}`
    },
    mappingActions() {
      return [
        { key: 'mapping', label: '1', title: '确认映射', hint: `${this.mapping.unmapped || 0} 位待处理`, path: '/library-organize', query: { tab: 'mapping' } },
        { key: 'inventory', label: '2', title: '片库整理', hint: '查看缺口演员', path: '/library-organize', query: { tab: 'inventory' } },
        { key: 'normalize', label: '3', title: '番号规整', hint: '检查映射覆盖', path: '/normalize' },
      ]
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
        const [mappingResp, configResp] = await Promise.allSettled([
          api.getActorMappingSummary(),
          api.getConfig(),
        ])
        if (mappingResp.status === 'rejected') {
          throw mappingResp.reason
        }
        const cfg = configResp.status === 'fulfilled' ? configResp.value.data : {}
        const mapping = mappingResp.value.data || {}
        this.overview = {
          snapshot: { snapshot_key: mapping.snapshot_key || '' },
          mapping: { ...mapping, auto_match: cfg.actor_mapping || {} },
        }
        if (configResp.status === 'rejected') {
          this.error = configResp.reason?.response?.data?.detail || configResp.reason?.message || '加载失败'
        }
      } catch (e) {
        this.error = e.response?.data?.detail || e.message || '加载失败'
      } finally {
        this.loading = false
      }
    },
    goLibraryOrganize(tab = 'mapping') {
      this.$router.push({ path: '/library-organize', query: { tab } })
    },
    goWorkbenchAction(action) {
      this.$router.push({ path: action.path, query: action.query || {} })
    },
  },
}
</script>

<style scoped src="./operations.css"></style>

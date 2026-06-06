<template>
  <article class="workbench-panel snapshot-card" aria-label="库存快照">
    <div class="panel-head">
      <div>
        <h2>库存快照</h2>
        <p>{{ snapshotSummary }}</p>
      </div>
      <button class="btn btn-ghost btn-sm" type="button" @click="goLibraryOrganize('inventory')">片库整理</button>
    </div>

    <AppleSkeleton v-if="loading && !overview" class="loading-panel console-state" variant="list" :items="5" label="库存快照加载中" />
    <AppleErrorState v-else-if="error && !overview" class="empty-panel console-state" title="库存快照加载失败" :description="error" next-step="可以刷新库存快照卡片，或打开片库整理查看最近任务。" retry-label="重试" secondary-action-label="片库整理" source-label="Inventory API" @retry="loadOverview" @secondary-action="goLibraryOrganize('inventory')" />
    <AppleEmptyState v-else-if="!overview" class="empty-panel console-state" title="暂无库存快照" description="后端还没有返回库存快照、作业和补全状态。" next-step="可以打开片库整理生成快照。" action-label="片库整理" density="compact" @action="goLibraryOrganize('inventory')" />
    <template v-else>
    <div class="mini-stats">
      <div><strong>{{ overview?.snapshot?.actor_count || 0 }}</strong><span>快照演员</span></div>
      <div><strong>{{ overview?.missing?.total || 0 }}</strong><span>库存缺口</span></div>
      <div><strong>{{ overview?.inventory_jobs?.running || 0 }}</strong><span>运行作业</span></div>
      <div><strong>{{ overview?.inventory_jobs?.failed || 0 }}</strong><span>失败作业</span></div>
    </div>

    <div class="queue-grid">
      <div class="list-block">
        <div class="block-head">
          <h3>补全状态</h3>
          <button type="button" @click="$router.push('/supplement')">补全管理</button>
        </div>
        <div v-if="overview?.supplement?.available" class="mini-stats">
          <div><strong>{{ overview.supplement.queued || 0 }}</strong><span>排队</span></div>
          <div><strong>{{ overview.supplement.running || 0 }}</strong><span>运行</span></div>
          <div><strong>{{ overview.supplement.failed || 0 }}</strong><span>失败</span></div>
        </div>
        <p v-else class="muted">补全服务暂不可用：{{ overview?.supplement?.error || '未连接' }}</p>
      </div>

      <div class="list-block">
        <div class="block-head">
          <h3>库存任务</h3>
          <span>运行中 {{ overview?.inventory_jobs?.running || 0 }} · 失败 {{ overview?.inventory_jobs?.failed || 0 }}</span>
        </div>
        <div class="compact-list">
          <div v-for="job in recentJobs" :key="job.id" class="compact-row static-row">
            <strong>{{ job.job_type }}</strong>
            <span>{{ job.status }} · {{ formatTime(job.created_at) }}</span>
          </div>
          <small v-if="!recentJobs.length" class="empty-line">暂无作业记录</small>
        </div>
      </div>
    </div>

    <article class="workbench-panel cache-panel">
      <div class="panel-head">
        <div>
          <h2>缓存诊断</h2>
          <p>{{ cacheStatsSummary }}</p>
        </div>
        <span class="backend-pill">{{ cacheStats?.backend || 'unknown' }}</span>
      </div>
      <div class="mini-stats cache-entry-stats">
        <div><strong>{{ cacheStats?.total_entries || 0 }}</strong><span>总条目</span></div>
        <div><strong>{{ cacheStats?.active_entries || 0 }}</strong><span>有效</span></div>
        <div><strong>{{ cacheStats?.expired_entries || 0 }}</strong><span>过期</span></div>
      </div>
      <div class="cache-rate-grid">
        <div class="state-item"><span>响应命中率</span><strong>{{ responseHitRate }}</strong></div>
        <div class="state-item"><span>搜索命中率</span><strong>{{ searchHitRate }}</strong></div>
        <div class="state-item"><span>合并等待</span><strong>{{ cacheStats?.metrics?.singleflight_waits || 0 }}</strong></div>
      </div>
      <div class="cache-namespaces">
        <div class="block-head"><h3>热门响应命名空间</h3></div>
        <div class="compact-list">
          <div v-for="item in topResponseNamespaces" :key="item.name" class="compact-row static-row">
            <span>{{ item.name }}</span>
            <strong>{{ item.count }}</strong>
          </div>
          <small v-if="!topResponseNamespaces.length" class="empty-line">暂无响应缓存</small>
        </div>
      </div>
      <p v-if="cacheStatsError" class="muted cache-error">{{ cacheStatsError }}</p>
    </article>

    <article class="workbench-panel">
      <div class="panel-head">
        <div>
          <h2>番号版本索引</h2>
          <p>{{ variantIndexJobSummary }}</p>
        </div>
        <button class="btn btn-ghost btn-sm" type="button" :disabled="rebuildingVariantIndex" @click="rebuildVariantIndex">
          {{ rebuildingVariantIndex ? '启动中...' : '重建索引' }}
        </button>
      </div>
      <div class="mini-stats">
        <div><strong>{{ overview?.variant_index?.group_count || 0 }}</strong><span>作品组</span></div>
        <div><strong>{{ overview?.variant_index?.item_count || 0 }}</strong><span>版本项</span></div>
        <div><strong>{{ overview?.variant_index?.last_job?.status || 'none' }}</strong><span>最近作业</span></div>
      </div>
    </article>
    </template>
  </article>
</template>

<script>
import api from '../../api'
import AppleSkeleton from '../../components/AppleSkeleton.vue'
import AppleEmptyState from '../../components/AppleEmptyState.vue'
import AppleErrorState from '../../components/AppleErrorState.vue'

export default {
  name: 'SnapshotCard',
  components: { AppleSkeleton, AppleEmptyState, AppleErrorState },
  data() {
    return {
      overview: null,
      cacheStats: null,
      cacheStatsError: '',
      loading: false,
      error: '',
      rebuildingVariantIndex: false,
    }
  },
  computed: {
    snapshotSummary() {
      if (this.error) return `快照加载失败：${this.error}`
      if (!this.overview) return '加载库存快照、任务和补全状态。'
      return `${this.overview.snapshot?.snapshot_key || '无快照'} · ${this.overview.snapshot?.actor_count || 0} 位演员`
    },
    recentJobs() {
      return this.overview?.inventory_jobs?.recent || []
    },
    cacheStatsSummary() {
      if (this.cacheStatsError) return '缓存统计暂不可用。'
      if (!this.cacheStats) return '加载缓存指标中。'
      return `${this.cacheStats.backend || 'unknown'} · ${this.cacheStats.active_entries || 0}/${this.cacheStats.total_entries || 0} active`
    },
    responseHitRate() {
      return this.formatHitRate(this.cacheStats?.metrics?.response)
    },
    searchHitRate() {
      return this.formatHitRate(this.cacheStats?.metrics?.search)
    },
    topResponseNamespaces() {
      const namespaces = this.cacheStats?.response_namespaces || {}
      return Object.entries(namespaces)
        .map(([name, count]) => ({ name, count: Number(count || 0) }))
        .sort((a, b) => b.count - a.count || a.name.localeCompare(b.name))
        .slice(0, 5)
    },
    variantIndexJobSummary() {
      const job = this.overview?.variant_index?.last_job || {}
      if (!job.status) return '尚未重建。'
      const processed = Number(job.processed || 0)
      const total = Number(job.total || 0)
      const progress = total ? `${processed}/${total}` : `${processed}`
      return `${job.status} · ${progress} · ${this.formatTime(job.updated_at) || this.formatTime(job.created_at) || ''}`
    },
  },
  mounted() {
    this.loadOverview()
  },
  methods: {
    async loadOverview() {
      this.loading = true
      this.error = ''
      this.cacheStatsError = ''
      try {
        const [snapshotResp, missingResp, jobsResp, supplementResp, cacheResp, variantResp] = await Promise.allSettled([
          api.getInventorySnapshotLatest(),
          api.getMissingActresses(),
          api.listInventoryJobs(),
          api.getSupplementStats(),
          api.getCacheStats(),
          api.getVideoVariantIndexStats(),
        ])
        if (snapshotResp.status === 'fulfilled') {
          const snapshot = snapshotResp.value.data || {}
          const missing = missingResp.status === 'fulfilled' ? missingResp.value.data : {}
          const jobs = jobsResp.status === 'fulfilled' ? (jobsResp.value.data?.data || []) : []
          const supplement = supplementResp.status === 'fulfilled' ? supplementResp.value.data : {}
          this.overview = {
            snapshot,
            missing: {
              total: Number(missing.total || 0),
            },
            inventory_jobs: {
              recent: jobs,
              running: jobs.filter(job => job.status === 'running').length,
              failed: jobs.filter(job => job.status === 'failed').length,
            },
            supplement: {
              available: supplementResp.status === 'fulfilled',
              queued: supplement.jobs_by_status?.queued || 0,
              running: supplement.jobs_by_status?.running || 0,
              failed: supplement.jobs_by_status?.failed || 0,
              error: supplementResp.status === 'rejected' ? (supplementResp.reason?.response?.data?.detail || supplementResp.reason?.message || '加载失败') : '',
            },
            variant_index: variantResp.status === 'fulfilled' ? (variantResp.value.data || {}) : {},
          }
        } else this.error = snapshotResp.reason?.response?.data?.detail || snapshotResp.reason?.message || '加载失败'
        if (cacheResp.status === 'fulfilled') this.cacheStats = cacheResp.value.data
        else this.cacheStatsError = cacheResp.reason?.response?.data?.detail || cacheResp.reason?.message || '加载失败'
        const softErrors = [missingResp, jobsResp, supplementResp, variantResp]
          .filter(resp => resp.status === 'rejected')
          .map(resp => resp.reason?.response?.data?.detail || resp.reason?.message || '加载失败')
        if (!this.error) this.error = softErrors[0] || ''
      } finally {
        this.loading = false
      }
    },
    async rebuildVariantIndex() {
      if (this.rebuildingVariantIndex) return
      this.rebuildingVariantIndex = true
      try {
        await api.startVideoVariantIndexJob()
        this.$message?.success?.('番号版本索引已开始重建')
        await this.loadOverview()
      } catch (e) {
        console.error('Rebuild variant index failed:', e)
      } finally {
        this.rebuildingVariantIndex = false
      }
    },
    formatHitRate(metrics = {}) {
      const hits = Number(metrics.hits || 0)
      const misses = Number(metrics.misses || 0)
      const total = hits + misses
      if (!total) return '0%'
      return `${Math.round((hits / total) * 100)}%`
    },
    formatTime(value) {
      if (!value) return ''
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return value
      return `${date.getMonth() + 1}/${date.getDate()} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
    },
    goLibraryOrganize(tab = 'inventory') {
      this.$router.push({ path: '/library-organize', query: { tab } })
    },
  },
}
</script>

<style scoped src="./operations.css"></style>

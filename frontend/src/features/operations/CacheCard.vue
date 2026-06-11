<template>
  <article class="workbench-panel cache-card" aria-label="缓存诊断与清理">
    <div class="panel-head">
      <div>
        <h2>缓存清理</h2>
        <p>{{ cacheSummaryText }}</p>
      </div>
      <div class="panel-actions">
        <button class="btn btn-ghost btn-sm" type="button" @click="loadCacheStats">刷新</button>
      </div>
    </div>

    <AppleSkeleton v-if="loading && !cacheStats" class="loading-panel console-state" variant="list" :items="3" label="缓存状态加载中" />
    <template v-else>
      <div class="state-grid">
        <div class="state-item"><span>响应缓存命中率</span><strong>{{ responseHitRate }}</strong></div>
        <div class="state-item"><span>活跃条目</span><strong>{{ cacheStats?.active_entries ?? cacheStats?.response?.active_entries ?? 0 }}</strong></div>
        <div class="state-item"><span>后端</span><strong>{{ cacheStats?.backend || cacheStats?.response?.backend || 'unknown' }}</strong></div>
      </div>

      <div class="cache-cleanup">
        <div class="block-head">
          <h3>缓存清理</h3>
          <span>{{ selectedCachePurgeLabel }}</span>
        </div>
        <div class="cache-scope-group" role="group" aria-label="缓存清理范围">
          <button
            v-for="scope in cachePurgeScopes"
            :key="scope.value"
            class="scope-chip"
            type="button"
            :class="{ active: selectedCachePurgeScope === scope.value }"
            @click="selectedCachePurgeScope = scope.value"
          >
            {{ scope.label }}
          </button>
        </div>
        <button class="btn btn-ghost btn-sm cache-purge-btn" type="button" :disabled="purgingCache" @click="purgeSelectedCache">
          {{ purgingCache ? '清理中...' : '清理缓存' }}
        </button>
      </div>
      <p v-if="error" class="muted cache-error">{{ error }}</p>
    </template>
  </article>
</template>

<script>
import api from '../../api'
import { requestConfirm } from '../../utils/confirmDialog'
import { CACHE_PURGE_SCOPES } from './operationsOptions'
import AppleSkeleton from '../../components/AppleSkeleton.vue'

export default {
  name: 'CacheCard',
  components: { AppleSkeleton },
  data() {
    return {
      cacheStats: null,
      loading: false,
      error: '',
      purgingCache: false,
      selectedCachePurgeScope: 'video',
      cachePurgeScopes: CACHE_PURGE_SCOPES,
    }
  },
  computed: {
    selectedCachePurgeLabel() {
      return this.cachePurgeScopes.find(scope => scope.value === this.selectedCachePurgeScope)?.label || this.selectedCachePurgeScope
    },
    responseHitRate() {
      const metrics = this.cacheStats?.response || this.cacheStats || {}
      const hits = Number(metrics.hits || 0)
      const misses = Number(metrics.misses || 0)
      const total = hits + misses
      if (!total) return '0%'
      return `${Math.round((hits / total) * 100)}%`
    },
    cacheSummaryText() {
      if (this.loading && !this.cacheStats) return '缓存状态加载中。'
      if (this.error && !this.cacheStats) return `缓存状态加载失败：${this.error}`
      return `命中率 ${this.responseHitRate} · 按范围清理响应缓存`
    },
  },
  mounted() {
    this.loadCacheStats()
  },
  methods: {
    async loadCacheStats() {
      this.loading = true
      this.error = ''
      try {
        const resp = await api.getCacheStats()
        this.cacheStats = resp.data
      } catch (e) {
        this.error = e.response?.data?.detail || e.message || '加载失败'
      } finally {
        this.loading = false
      }
    },
    async purgeSelectedCache() {
      if (this.purgingCache) return
      const confirmed = await requestConfirm({
        title: '缓存清理',
        message: `确认清理${this.selectedCachePurgeLabel}？`,
        details: '清理后会重新拉取相关数据，短时间内接口可能变慢。',
        confirmText: '清理',
        tone: this.selectedCachePurgeScope === 'all' ? 'danger' : 'default',
      })
      if (!confirmed) return
      this.purgingCache = true
      try {
        await api.purgeCache(this.selectedCachePurgeScope)
        this.$message?.success?.('缓存已清理')
        await this.loadCacheStats()
      } catch (e) {
        console.error('Purge cache failed:', e)
      } finally {
        this.purgingCache = false
      }
    },
  },
}
</script>

<style scoped src="./operations.css"></style>

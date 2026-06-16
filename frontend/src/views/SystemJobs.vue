<template>
  <div class="system-jobs-page page-shell page-shell--workspace ops-page">
    <header class="ops-hero">
      <div class="ops-hero-copy">
        <span class="ops-eyebrow">系统工作台</span>
        <h1>系统作业</h1>
        <p>零散的系统级维护作业：触发、看状态、看历史。运营总览里点过来会直接定位到对应作业。</p>
      </div>
    </header>

    <div class="ops-section-list">
      <!-- 演员头像下载 -->
      <section ref="avatarSection" class="ops-panel" aria-label="演员头像下载">
        <div class="ops-panel-head">
          <div><h2>演员头像下载</h2><p>从 gfriends 同步演员头像，补齐缺失的头像资源。</p></div>
        </div>
        <div class="ops-job-list">
          <div class="ops-job" :class="{ 'is-highlighted': isHi('avatar') }">
            <div class="ops-job-main">
              <div class="ops-job-title">
                <h3>gfriends 头像同步</h3>
                <span class="ops-pill" :class="avatarRunning ? 'is-running' : 'is-idle'">{{ avatarRunning ? '运行中' : '就绪' }}</span>
              </div>
              <p class="ops-job-desc">为缺少头像的演员批量抓取并合并头像。</p>
              <p v-if="avatarMessage" class="ops-job-meta">{{ avatarMessage }}</p>
            </div>
            <div class="ops-job-actions">
              <button class="btn btn-primary btn-sm" type="button" :disabled="avatarRunning" @click="runAvatar">
                {{ avatarRunning ? '已开始...' : '立即运行' }}
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- 影片分组索引重建 -->
      <section ref="variantSection" class="ops-panel" aria-label="影片分组索引重建">
        <div class="ops-panel-head">
          <div><h2>影片分组索引重建</h2><p>重建跨页合并与整组收藏所依赖的变体（分组）索引。</p></div>
          <div class="ops-panel-actions">
            <button class="btn btn-ghost btn-sm" type="button" @click="loadVariant">刷新</button>
          </div>
        </div>
        <div class="ops-job-list">
          <div class="ops-job" :class="{ 'is-highlighted': isHi('variant_index_rebuild') }">
            <div class="ops-job-main">
              <div class="ops-job-title">
                <h3>变体索引重建</h3>
                <span class="ops-pill" :class="variantRunning ? 'is-running' : 'is-idle'">{{ variantRunning ? '运行中' : '就绪' }}</span>
              </div>
              <p class="ops-job-desc">{{ variantStatsText }}</p>
            </div>
            <div class="ops-job-actions">
              <button class="btn btn-primary btn-sm" type="button" :disabled="variantRunning" @click="runVariant">
                {{ variantRunning ? '已开始...' : '立即运行' }}
              </button>
            </div>
          </div>
        </div>
        <div class="ops-grid" style="margin-top: 12px;">
          <div class="ops-cell" v-for="job in variantJobs" :key="job.id">
            <span>{{ job.status }}</span>
            <strong>{{ formatTime(job.created_at) || `#${job.id}` }}</strong>
            <small v-if="job.processed != null">处理 {{ job.processed }}{{ job.groups != null ? ` · 分组 ${job.groups}` : '' }}</small>
          </div>
          <p v-if="!variantJobs.length" class="ops-empty">暂无重建记录</p>
        </div>
      </section>

      <!-- 缓存清理 -->
      <section ref="cacheSection" class="ops-panel" aria-label="缓存清理">
        <div class="ops-panel-head">
          <div><h2>缓存清理</h2><p>{{ cacheStatsText }}</p></div>
          <div class="ops-panel-actions">
            <button class="btn btn-ghost btn-sm" type="button" @click="loadCache">刷新</button>
          </div>
        </div>
        <div class="ops-job" :class="{ 'is-highlighted': isHi('cache') }">
          <div class="ops-job-main" style="flex-basis: 100%;">
            <div class="ops-chip-group" role="group" aria-label="缓存清理范围">
              <button
                v-for="scope in cachePurgeScopes"
                :key="scope.value"
                class="ops-chip"
                type="button"
                :class="{ active: selectedScope === scope.value }"
                @click="selectedScope = scope.value"
              >{{ scope.label }}</button>
            </div>
          </div>
          <div class="ops-job-actions">
            <button class="btn btn-primary btn-sm" type="button" :disabled="purging" @click="purge">
              {{ purging ? '清理中...' : '清理缓存' }}
            </button>
          </div>
        </div>
      </section>

      <!-- 调度作业控制台 -->
      <section ref="schedulerSection" class="ops-panel" aria-label="调度作业控制台">
        <div class="ops-panel-head">
          <div><h2>调度作业控制台</h2><p>定时作业的下次运行、上次结果，可手动立即运行。</p></div>
          <div class="ops-panel-actions">
            <button class="btn btn-ghost btn-sm" type="button" @click="loadScheduler">刷新</button>
          </div>
        </div>
        <div v-if="schedulerJobs.length" class="ops-job-list">
          <div
            v-for="job in schedulerJobs"
            :key="job.id"
            class="ops-job"
            :class="{ 'is-highlighted': isHi(job.id) }"
          >
            <div class="ops-job-main">
              <div class="ops-job-title">
                <h3>{{ job.name || job.id }}</h3>
                <span class="ops-pill" :class="pillClass(job.last_status)">{{ pillText(job.last_status) }}</span>
              </div>
              <p class="ops-job-meta">
                下次 {{ formatTime(job.next_run_time) || '未计划' }}
                <template v-if="job.last_run_at"> · 上次 {{ formatTime(job.last_run_at) }}</template>
                <template v-if="job.last_error"> · {{ job.last_error }}</template>
              </p>
            </div>
            <div class="ops-job-actions">
              <button class="btn btn-primary btn-sm" type="button" :disabled="runningJob === job.id" @click="runJob(job)">
                {{ runningJob === job.id ? '启动中...' : '立即运行' }}
              </button>
            </div>
          </div>
        </div>
        <p v-else class="ops-empty">调度未启用，或暂无调度作业。</p>
      </section>
    </div>
  </div>
</template>

<script>
import api from '../api'
import { requestConfirm } from '../utils/confirmDialog'
import { ElMessage } from '../utils/message'
import { CACHE_PURGE_SCOPES } from '../features/operations/operationsOptions'

export default {
  name: 'SystemJobs',
  data() {
    return {
      avatarRunning: false,
      avatarMessage: '',
      variantRunning: false,
      variantStats: null,
      variantJobs: [],
      cacheStats: null,
      cachePurgeScopes: CACHE_PURGE_SCOPES,
      selectedScope: 'video',
      purging: false,
      schedulerJobs: [],
      runningJob: '',
      highlightedJob: '',
    }
  },
  computed: {
    variantStatsText() {
      const s = this.variantStats || {}
      if (s.groups == null && s.videos == null) return '重建跨页合并与整组收藏所依赖的索引。'
      return `当前 ${s.groups ?? 0} 个分组 · ${s.videos ?? 0} 部影片`
    },
    cacheStatsText() {
      if (!this.cacheStats) return '清理影片/搜索、响应、枚举目录等缓存。'
      const active = this.cacheStats.active_entries ?? this.cacheStats.response?.active_entries ?? 0
      const backend = this.cacheStats.backend || this.cacheStats.response?.backend || 'unknown'
      return `后端 ${backend} · 活跃条目 ${active}`
    },
  },
  mounted() {
    this.loadScheduler()
    this.loadVariant()
    this.loadCache()
    this.applyHighlight()
  },
  watch: {
    '$route.query.job'() {
      this.applyHighlight()
    },
  },
  methods: {
    applyHighlight() {
      const raw = String(this.$route.query.job || '')
      if (!raw) return
      const aliases = { gfriends: 'avatar', gfriends_avatar: 'avatar', avatars: 'avatar' }
      const job = aliases[raw] || raw
      this.highlightedJob = job
      const refMap = {
        avatar: 'avatarSection',
        variant_index_rebuild: 'variantSection',
        cache: 'cacheSection',
      }
      const targetRef = refMap[job] || 'schedulerSection'
      this.$nextTick(() => {
        this.$refs[targetRef]?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      })
      if (this._highlightTimer) clearTimeout(this._highlightTimer)
      this._highlightTimer = setTimeout(() => { this.highlightedJob = '' }, 2600)
    },
    isHi(key) {
      return this.highlightedJob === key
    },
    async runAvatar() {
      if (this.avatarRunning) return
      this.avatarRunning = true
      try {
        await api.startGfriendsAvatarSyncJob()
        this.avatarMessage = '已开始演员头像下载，作业在后台运行。'
        ElMessage.success('已开始演员头像下载')
      } catch (e) {
        this.avatarMessage = this.errText(e)
        ElMessage.error(this.avatarMessage)
      } finally {
        this.avatarRunning = false
      }
    },
    async runVariant() {
      if (this.variantRunning) return
      this.variantRunning = true
      try {
        await api.startVideoVariantIndexJob()
        ElMessage.success('已开始变体索引重建')
        await this.loadVariant()
      } catch (e) {
        ElMessage.error(this.errText(e))
      } finally {
        this.variantRunning = false
      }
    },
    async loadVariant() {
      const [statsResp, jobsResp] = await Promise.allSettled([
        api.getVideoVariantIndexStats(),
        api.listVideoVariantIndexJobs(8),
      ])
      if (statsResp.status === 'fulfilled') this.variantStats = statsResp.value.data
      if (jobsResp.status === 'fulfilled') {
        const data = jobsResp.value.data
        this.variantJobs = Array.isArray(data) ? data : (data?.data || data?.jobs || [])
      }
    },
    async loadCache() {
      try {
        const resp = await api.getCacheStats()
        this.cacheStats = resp.data
      } catch (e) {
        this.cacheStats = null
      }
    },
    async purge() {
      if (this.purging) return
      const label = this.cachePurgeScopes.find(s => s.value === this.selectedScope)?.label || this.selectedScope
      const ok = await requestConfirm({
        title: '清理缓存',
        message: `确认清理「${label}」缓存？该操作不可撤销。`,
        confirmText: '清理',
        cancelText: '取消',
        tone: 'warning',
      })
      if (!ok) return
      this.purging = true
      try {
        await api.purgeCache(this.selectedScope)
        ElMessage.success(`已清理「${label}」缓存`)
        await this.loadCache()
      } catch (e) {
        ElMessage.error(this.errText(e))
      } finally {
        this.purging = false
      }
    },
    async loadScheduler() {
      try {
        const resp = await api.getSchedulerJobs()
        this.schedulerJobs = Array.isArray(resp.data) ? resp.data : []
      } catch (e) {
        this.schedulerJobs = []
      }
    },
    async runJob(job) {
      if (this.runningJob) return
      this.runningJob = job.id
      try {
        const resp = await api.runSchedulerJob(job.id)
        if (resp.data?.accepted) ElMessage.success(`已开始运行「${job.name || job.id}」`)
        else ElMessage.info(`「${job.name || job.id}」正在运行中`)
        setTimeout(() => this.loadScheduler(), 600)
      } catch (e) {
        ElMessage.error(this.errText(e))
      } finally {
        this.runningJob = ''
      }
    },
    pillClass(status) {
      return { 'is-success': status === 'success', 'is-failed': status === 'failed', 'is-idle': !status }
    },
    pillText(status) {
      if (status === 'success') return '成功'
      if (status === 'failed') return '失败'
      return '未运行'
    },
    formatTime(value) {
      if (!value) return ''
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return value
      return `${date.getMonth() + 1}/${date.getDate()} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
    },
    errText(reason) {
      return reason?.response?.data?.detail || reason?.message || '操作失败'
    },
  },
}
</script>

<style scoped src="../features/operations/operationsPanel.css"></style>

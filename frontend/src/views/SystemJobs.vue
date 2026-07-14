<template>
  <div class="system-jobs-page page-shell page-shell--gallery ops-page">
    <header class="ops-hero">
      <div class="ops-hero-copy">
        <h1>系统作业</h1>
      </div>
    </header>

    <div class="ops-section-list">
      <!-- AVDB 公开库同步 -->
      <section ref="avdbSection" class="ops-panel" aria-label="AVDB 公开库同步">
        <div class="ops-panel-head">
          <div><h2>AVDB 公开库同步</h2><p>定期下载公开 CSV，全量更新 PostgreSQL 磁力索引。</p></div>
          <div class="ops-panel-actions">
            <button v-if="returnTarget" class="btn btn-ghost btn-sm" type="button" @click="returnToSources">返回下载源</button>
            <RefreshButton @click="refreshAvdb" />
          </div>
        </div>
        <div class="ops-job-list">
          <div class="ops-job" :class="{ 'is-highlighted': isHi('avdb_sync') }">
            <div class="ops-job-main">
              <div class="ops-job-title">
                <h3>AVDB 全量同步</h3>
                <span class="ops-pill" :class="avdbLifecycle.tone">{{ avdbLifecycle.label }}</span>
              </div>
              <p class="ops-job-desc">{{ avdbStatusText }}</p>
              <p class="ops-job-meta">{{ avdbMetaText }}</p>
              <p v-if="avdbErrorText" class="ops-job-meta ops-job-error">{{ avdbErrorText }}</p>
            </div>
            <div class="ops-job-actions">
              <button class="btn btn-primary btn-sm" type="button" :disabled="avdbRunDisabled" @click="runAvdb">
                {{ avdbRunLabel }}
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- 演员头像下载 -->
      <section ref="avatarSection" class="ops-panel" aria-label="演员头像下载">
        <div class="ops-panel-head">
          <div><h2>演员头像下载</h2><p>从 gfriends 同步演员头像，补齐缺失的头像资源。</p></div>
          <div class="ops-panel-actions">
            <button class="btn btn-ghost btn-sm" type="button" @click="openAvatarHistory">历史</button>
            <RefreshButton @click="loadAvatar" />
          </div>
        </div>
        <div class="ops-job-list">
          <div class="ops-job" :class="{ 'is-highlighted': isHi('avatar') }">
            <div class="ops-job-main">
              <div class="ops-job-title">
                <h3>gfriends 头像同步</h3>
                <span class="ops-pill" :class="avatarBusy ? 'is-running' : 'is-idle'">{{ avatarBusy ? '运行中' : '就绪' }}</span>
              </div>
              <p class="ops-job-desc">为缺少头像的演员批量抓取并合并头像。</p>
              <p class="ops-job-meta">{{ avatarStatusText }}</p>
              <p v-if="avatarMessage" class="ops-job-meta">{{ avatarMessage }}</p>
            </div>
            <div class="ops-job-actions">
              <button class="btn btn-primary btn-sm" type="button" :disabled="avatarBusy" @click="runAvatar">
                {{ avatarBusy ? '已开始...' : '立即运行' }}
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- 影片分组索引重建 -->
      <section ref="variantSection" class="ops-panel" aria-label="影片分组索引重建">
        <div class="ops-panel-head">
          <div><h2>影片分组索引重建</h2><p>重建跨页合并与整组收藏所依赖的变体（分组）索引。全量数据库导入后会自动重建一次，平时无需手动触发。</p></div>
          <div class="ops-panel-actions">
            <button class="btn btn-ghost btn-sm" type="button" @click="openVariantHistory">历史</button>
            <RefreshButton @click="loadVariant" />
          </div>
        </div>
        <div class="ops-job-list">
          <div class="ops-job" :class="{ 'is-highlighted': isHi('variant_index_rebuild') }">
            <div class="ops-job-main">
              <div class="ops-job-title">
                <h3>变体索引重建</h3>
                <span class="ops-pill" :class="variantBusy ? 'is-running' : 'is-idle'">{{ variantBusy ? '运行中' : '就绪' }}</span>
              </div>
              <p class="ops-job-desc">{{ variantStatsText }}</p>
            </div>
            <div class="ops-job-actions">
              <button class="btn btn-primary btn-sm" type="button" :disabled="variantBusy" @click="runVariant">
                {{ variantBusy ? '已开始...' : '立即运行' }}
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- 缓存清理 -->
      <section ref="cacheSection" class="ops-panel" aria-label="缓存清理">
        <div class="ops-panel-head">
          <div><h2>缓存清理</h2><p>{{ cacheStatsText }}</p></div>
          <div class="ops-panel-actions">
            <RefreshButton @click="loadCache" />
          </div>
        </div>
        <div class="ops-job" :class="{ 'is-highlighted': isHi('cache') }">
          <div class="ops-job-main">
            <div class="ops-chip-group ops-chip-group--inline" role="group" aria-label="缓存清理范围">
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
            <RefreshButton @click="loadScheduler" />
          </div>
        </div>
        <div v-if="generalSchedulerJobs.length" class="ops-job-list">
          <div
            v-for="job in generalSchedulerJobs"
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

    <JobHistoryDialog
      :open="historyOpen"
      :title="historyTitle"
      :rows="historyRows"
      empty-text="暂无作业记录"
      @close="historyOpen = false"
    />
  </div>
</template>

<script>
import api from '../api'
import { requestConfirm } from '../utils/confirmDialog'
import { ElMessage } from '../utils/message'
import { CACHE_PURGE_SCOPES } from '../features/operations/operationsOptions'
import {
  avdbSourceCountText,
  avdbState,
  formatAvdbCount,
  normalizeAvdbStatus,
} from '../features/downloads/avdbPresentation'
import JobHistoryDialog from '../features/operations/JobHistoryDialog.vue'
import RefreshButton from '../components/RefreshButton.vue'

const AVDB_POLL_RETRY_LIMIT = 5

export default {
  name: 'SystemJobs',
  components: { JobHistoryDialog, RefreshButton },
  data() {
    return {
      avatarRunning: false,
      avatarMessage: '',
      avatarJobs: [],
      variantRunning: false,
      variantStats: null,
      variantJobs: [],
      cacheStats: null,
      cachePurgeScopes: CACHE_PURGE_SCOPES,
      selectedScope: 'video',
      purging: false,
      schedulerJobs: [],
      runningJob: '',
      avdbStatus: {},
      avdbStatusLoading: true,
      avdbStatusKnown: false,
      avdbRunning: false,
      avdbPollPending: false,
      avdbPollFailures: 0,
      avdbMessage: '',
      schedulerLoading: false,
      highlightedJob: '',
      historyOpen: false,
      historyTitle: '',
      historyRows: [],
    }
  },
  computed: {
    normalizedAvdb() {
      return normalizeAvdbStatus(this.avdbStatus)
    },
    avdbLifecycle() {
      return avdbState(this.avdbStatus, {
        loading: this.avdbStatusLoading,
        known: this.avdbStatusKnown,
      })
    },
    avdbBusy() {
      return this.avdbRunning || this.avdbLifecycle.code === 'syncing'
    },
    avdbShouldPoll() {
      return this.avdbBusy || (
        this.normalizedAvdb.status === 'running'
        && this.avdbPollFailures < AVDB_POLL_RETRY_LIMIT
      )
    },
    avdbRunDisabled() {
      return this.avdbBusy || this.avdbStatusLoading || !this.avdbStatusKnown
    },
    avdbJob() {
      return this.schedulerJobs.find(job => job.id === 'avdb_sync') || null
    },
    generalSchedulerJobs() {
      return this.schedulerJobs.filter(job => job.id !== 'avdb_sync')
    },
    returnTarget() {
      const target = String(this.$route.query.return_to || '')
      return target.startsWith('/') && !target.startsWith('//') ? target : ''
    },
    avdbStatusText() {
      const descriptions = {
        loading: '正在读取 AVDB 同步状态。',
        unavailable: '无法确认 AVDB 当前设置，刷新成功前不会修改或运行同步作业。',
        unconfigured: '尚未创建同步作业。创建后会定期检查上游版本。',
        unsynced: '同步作业已创建，运行首次同步后即可启用 AVDB 来源。',
        syncing: '正在下载、校验并全量更新本地索引。',
        available: '本地磁力索引可用，可按番号参与候选补全与下载。',
        failed: this.normalizedAvdb.available
          ? '上次同步失败，当前仍使用上一版可用索引。'
          : '同步失败，当前没有可用的 AVDB 索引。',
      }
      return descriptions[this.avdbLifecycle.code] || descriptions.unconfigured
    },
    avdbMetaText() {
      const parts = []
      const version = this.normalizedAvdb.release || this.normalizedAvdb.generation
      if (version) parts.push(`版本 ${version}`)
      if (this.normalizedAvdb.available || this.normalizedAvdb.recordCount) {
        parts.push(`记录 ${formatAvdbCount(this.normalizedAvdb.recordCount)}`)
      }
      const sources = avdbSourceCountText(this.normalizedAvdb.sourceCounts)
      if (sources) parts.push(sources)
      const last = this.formatTime(
        this.normalizedAvdb.lastCompletedAt
        || this.normalizedAvdb.lastStartedAt
        || this.normalizedAvdb.lastCheckedAt,
      )
      parts.push(`上次 ${last || '尚未运行'}`)
      parts.push(`下次 ${this.formatTime(this.avdbJob?.next_run_time) || '未计划'}`)
      return parts.join(' · ')
    },
    avdbErrorText() {
      return this.avdbMessage || this.normalizedAvdb.lastError
    },
    avdbRunLabel() {
      if (this.avdbRunning) return '启动中...'
      if (this.avdbLifecycle.code === 'loading') return '读取状态...'
      if (this.avdbLifecycle.code === 'unavailable') return '状态不可用'
      if (this.avdbLifecycle.code === 'syncing') return '同步中...'
      if (this.avdbLifecycle.code === 'unconfigured') return '创建并同步'
      if (this.avdbLifecycle.code === 'failed') return '重新同步'
      return '立即同步'
    },
    avatarLatest() {
      return this.avatarJobs[0] || null
    },
    avatarBusy() {
      if (this.avatarRunning) return true
      const s = this.avatarLatest?.status
      return s === 'running' || s === 'queued'
    },
    avatarStatusText() {
      const j = this.avatarLatest
      if (!j) return '尚未运行过头像同步。'
      if (j.status === 'running' || j.status === 'queued') {
        return j.total_found ? `同步进行中… 已命中 ${j.total_found}` : '同步进行中…'
      }
      const t = this.formatTime(j.finished_at || j.started_at || j.created_at)
      if (j.status === 'failed') return `上次同步失败${t ? `（${t}）` : ''}`
      const parts = this.avatarCountParts(j)
      return `上次同步 ${t || '—'}${parts ? ` · ${parts}` : ''}`
    },
    variantBusy() {
      if (this.variantRunning) return true
      const s = this.variantJobs[0]?.status
      return s === 'running' || s === 'queued'
    },
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
    this.refreshAvdb()
    this.loadVariant()
    this.loadCache()
    this.loadAvatar()
    this.applyHighlight()
    this._poll = setInterval(() => {
      if (this.avatarBusy) this.loadAvatar()
      if (this.variantBusy) this.loadVariant()
      if (this.avdbShouldPoll) this.refreshAvdb({ silent: true })
    }, 6000)
  },
  beforeUnmount() {
    if (this._poll) clearInterval(this._poll)
    if (this._highlightTimer) clearTimeout(this._highlightTimer)
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
        avdb_sync: 'avdbSection',
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
    async refreshAvdb({ silent = false } = {}) {
      if (this.avdbPollPending) return
      if (!silent) this.avdbPollFailures = 0
      this.avdbPollPending = true
      try {
        await Promise.all([this.loadAvdbStatus({ silent }), this.loadScheduler()])
      } finally {
        this.avdbPollPending = false
      }
    },
    async loadAvdbStatus({ silent = false } = {}) {
      if (!silent) this.avdbStatusLoading = true
      try {
        const resp = await api.getAvdbStatus()
        this.avdbStatus = resp.data || {}
        this.avdbStatusKnown = true
        this.avdbPollFailures = 0
        this.avdbMessage = ''
      } catch (e) {
        this.avdbStatusKnown = false
        if (this.normalizedAvdb.status === 'running') {
          this.avdbPollFailures = Math.min(
            AVDB_POLL_RETRY_LIMIT,
            this.avdbPollFailures + 1,
          )
        }
        this.avdbMessage = this.errText(e)
      } finally {
        this.avdbStatusLoading = false
      }
    },
    async runAvdb() {
      if (this.avdbRunDisabled) return
      this.avdbRunning = true
      this.avdbMessage = ''
      try {
        if (!this.normalizedAvdb.syncEnabled) {
          await api.updateConfig({
            sources: {
              avdb: {
                enabled: this.normalizedAvdb.enabled,
                sync_enabled: true,
              },
            },
          })
        }
        const resp = await api.runAvdbSync()
        this.avdbStatus = { ...this.avdbStatus, sync_enabled: true, status: 'running' }
        this.avdbStatusKnown = true
        if (resp.data?.accepted === false) ElMessage.info('AVDB 同步正在运行中')
        else ElMessage.success('已开始 AVDB 全量同步')
        setTimeout(() => this.refreshAvdb(), 700)
      } catch (e) {
        this.avdbMessage = this.errText(e)
        ElMessage.error(this.avdbMessage)
      } finally {
        this.avdbRunning = false
      }
    },
    returnToSources() {
      if (this.returnTarget) this.$router.push(this.returnTarget).catch(() => {})
    },
    async runAvatar() {
      if (this.avatarRunning) return
      this.avatarRunning = true
      try {
        await api.startGfriendsAvatarSyncJob()
        this.avatarMessage = '已开始演员头像下载，作业在后台运行。'
        ElMessage.success('已开始演员头像下载')
        setTimeout(() => this.loadAvatar(), 800)
      } catch (e) {
        this.avatarMessage = this.errText(e)
        ElMessage.error(this.avatarMessage)
      } finally {
        this.avatarRunning = false
      }
    },
    async loadAvatar() {
      try {
        const resp = await api.listSupplementJobs({ source: 'gfriends', page_size: 10 })
        const data = resp.data
        this.avatarJobs = Array.isArray(data) ? data : (data?.data || data?.jobs || [])
      } catch (e) {
        this.avatarJobs = []
      }
    },
    avatarCountParts(j) {
      const parts = []
      if (j.total_found != null) parts.push(`命中 ${j.total_found}`)
      if (j.inserted_count != null) parts.push(`新增 ${j.inserted_count}`)
      if (j.updated_count != null) parts.push(`更新 ${j.updated_count}`)
      return parts.join(' · ')
    },
    openAvatarHistory() {
      this.historyTitle = 'gfriends 头像同步历史'
      this.historyRows = this.avatarJobs.map((j) => ({
        id: j.id,
        statusText: this.jobStatusText(j.status),
        tone: this.jobTone(j.status),
        time: this.formatTime(j.finished_at || j.started_at || j.created_at),
        meta: [this.avatarCountParts(j), j.last_error].filter(Boolean).join(' · '),
      }))
      this.historyOpen = true
    },
    openVariantHistory() {
      this.historyTitle = '变体索引重建历史'
      this.historyRows = this.variantJobs.map((j) => ({
        id: j.id,
        statusText: this.jobStatusText(j.status),
        tone: this.jobTone(j.status),
        time: this.formatTime(j.updated_at || j.created_at),
        meta: this.variantRowMeta(j),
      }))
      this.historyOpen = true
    },
    variantRowMeta(j) {
      const parts = []
      if (j.processed != null) parts.push(`处理 ${j.processed}`)
      const groups = j.groups ?? j.result?.group_count
      if (groups != null) parts.push(`分组 ${groups}`)
      const err = j.last_error || j.error
      if (err) parts.push(err)
      return parts.join(' · ')
    },
    jobStatusText(status) {
      const map = {
        succeeded: '成功', success: '成功', completed: '完成',
        failed: '失败', error: '失败', running: '运行中', queued: '排队',
      }
      return map[status] || status || '—'
    },
    jobTone(status) {
      if (['succeeded', 'success', 'completed'].includes(status)) return 'ok'
      if (['failed', 'error'].includes(status)) return 'bad'
      if (['running', 'queued'].includes(status)) return 'run'
      return 'idle'
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
      if (this.schedulerLoading) return
      this.schedulerLoading = true
      try {
        const resp = await api.getSchedulerJobs()
        this.schedulerJobs = Array.isArray(resp.data) ? resp.data : []
      } catch (e) {
        this.schedulerJobs = []
      } finally {
        this.schedulerLoading = false
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

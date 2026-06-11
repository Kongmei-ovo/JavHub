<template>
  <article class="workbench-panel pipeline-card" aria-label="数据管道">
    <div class="panel-head">
      <div>
        <h2>数据管道</h2>
        <p>{{ pipelineSummaryText }}</p>
      </div>
      <div class="panel-actions">
        <button class="btn btn-ghost btn-sm" type="button" @click="goJavInfoImport">导入数据库</button>
        <button class="btn btn-ghost btn-sm" type="button" @click="$router.push('/supplement')">补全管理</button>
        <button class="btn btn-ghost btn-sm" type="button" @click="loadOverview">刷新</button>
      </div>
    </div>

    <AppleSkeleton v-if="loading && !jobs" class="loading-panel console-state" variant="list" :items="4" label="数据管道状态加载中" />
    <AppleErrorState v-else-if="error && !jobs" class="empty-panel console-state" title="数据管道状态加载失败" :description="error" next-step="可以重试，或检查后端调度器是否启动。" retry-label="重试" source-label="Scheduler API" @retry="loadOverview" />
    <template v-else>
      <div class="state-grid pipeline-stages">
        <div v-for="stage in stages" :key="stage.key" class="state-item pipeline-stage" :class="{ warning: stage.lastStatus === 'error' }">
          <span>{{ stage.order }}. {{ stage.label }}</span>
          <strong>{{ stageStatusText(stage) }}</strong>
          <small class="muted">{{ stageScheduleText(stage) }}</small>
          <button
            class="btn btn-ghost btn-sm"
            type="button"
            :disabled="Boolean(running[stage.key])"
            @click="runStage(stage)"
          >
            {{ running[stage.key] ? '启动中...' : '立即运行' }}
          </button>
        </div>
      </div>
      <p v-if="error" class="muted cache-error">{{ error }}</p>
    </template>
  </article>
</template>

<script>
import api from '../../api'
import AppleSkeleton from '../../components/AppleSkeleton.vue'
import AppleErrorState from '../../components/AppleErrorState.vue'

// 管道阶段定义：key 对应后端调度任务 id（/v1/scheduler/jobs），
// 顺序即数据流向：订阅检查 → 库存采集对比 → 候选处理 → 变体索引。
const STAGES = [
  {
    key: 'subscription_check',
    order: 1,
    label: '订阅检查',
    hint: '抓新作并生成候选',
  },
  {
    key: 'supplement_ensure',
    order: 2,
    label: '订阅演员补全',
    hint: '佚名/外快影片抓取与合并',
    schedule: '随订阅检查自动触发',
  },
  {
    key: 'inventory_daily_pipeline',
    order: 3,
    label: '库存采集与对比',
    hint: 'Emby 快照 → 缺口对比',
  },
  {
    key: 'candidate_auto_process',
    order: 4,
    label: '候选自动处理',
    hint: '补磁力并下发下载',
  },
  {
    key: 'variant_index_rebuild',
    order: 5,
    label: '变体索引重建',
    hint: '跨页合并与整组收藏的数据源',
  },
]

export default {
  name: 'PipelineCard',
  components: { AppleSkeleton, AppleErrorState },
  data() {
    return {
      jobs: null,
      loading: false,
      error: '',
      running: {},
    }
  },
  computed: {
    jobsById() {
      const map = {}
      for (const job of this.jobs || []) {
        if (job?.id) map[job.id] = job
      }
      return map
    },
    stages() {
      return STAGES.map(stage => {
        const job = this.jobsById[stage.key] || {}
        return {
          ...stage,
          lastStatus: job.last_status || null,
          lastRunAt: job.last_run_at || null,
          nextRunTime: job.next_run_time || null,
          scheduled: Boolean(job.id),
        }
      })
    },
    pipelineSummaryText() {
      if (this.loading && !this.jobs) return '管道状态加载中。'
      if (this.error && !this.jobs) return `管道状态加载失败：${this.error}`
      const failed = this.stages.filter(stage => stage.lastStatus === 'error').length
      if (failed > 0) return `${failed} 个阶段最近一次运行失败`
      const scheduled = this.stages.filter(stage => stage.scheduled).length
      return `导入 → 补全 → 索引 → 快照 → 对比 → 候选 · ${scheduled}/${this.stages.length} 个阶段已自动调度`
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
        const resp = await api.getSchedulerJobs()
        this.jobs = Array.isArray(resp.data) ? resp.data : []
      } catch (e) {
        this.error = e.response?.data?.detail || e.message || '加载失败'
      } finally {
        this.loading = false
      }
    },
    stageStatusText(stage) {
      if (!stage.lastStatus) return stage.scheduled || stage.schedule ? '未运行' : '未调度'
      if (stage.lastStatus === 'error') return '失败'
      return `成功 ${this.formatTime(stage.lastRunAt)}`
    },
    stageScheduleText(stage) {
      if (stage.nextRunTime) return `下次 ${this.formatTime(stage.nextRunTime)} · ${stage.hint}`
      if (stage.schedule) return `${stage.schedule} · ${stage.hint}`
      return stage.hint
    },
    async runStage(stage) {
      if (this.running[stage.key]) return
      this.running = { ...this.running, [stage.key]: true }
      try {
        if (stage.key === 'subscription_check') {
          await api.checkSubscriptions()
        } else if (stage.key === 'supplement_ensure') {
          await api.ensureSubscribedSupplement()
        } else if (stage.key === 'inventory_daily_pipeline') {
          await api.runInventoryPipeline({ do_collect: true, process: true, dry_run: true })
        } else if (stage.key === 'candidate_auto_process') {
          await api.runCandidateProcessingNow()
        } else if (stage.key === 'variant_index_rebuild') {
          await api.startVideoVariantIndexJob()
        }
        this.$message?.success?.(`${stage.label}已启动`)
        await this.loadOverview()
      } catch (e) {
        console.error(`Run pipeline stage ${stage.key} failed:`, e)
        this.error = e.response?.data?.detail || e.message || `${stage.label}启动失败`
      } finally {
        this.running = { ...this.running, [stage.key]: false }
      }
    },
    formatTime(value) {
      if (!value) return ''
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return value
      return `${date.getMonth() + 1}/${date.getDate()} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
    },
    goJavInfoImport() {
      this.$router.push({ path: '/settings', query: { tab: 'javinfo-import' } })
    },
  },
}
</script>

<style scoped src="./operations.css"></style>

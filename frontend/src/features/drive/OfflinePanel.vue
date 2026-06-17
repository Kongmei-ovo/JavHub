<template>
  <section class="offline-panel" aria-label="115 离线任务">
    <div class="op-head">
      <div class="op-title">
        <strong>离线任务</strong>
        <span v-if="quota" class="op-quota" :class="{ low: quota.remain <= 0 }">
          本月剩余 {{ quota.remain }} / {{ quota.total }}
        </span>
      </div>
      <div class="op-actions">
        <button class="ghost-btn sm" type="button" @click="$emit('add')">＋ 添加离线</button>
        <button class="ghost-btn sm" type="button" :disabled="busy" @click="clearCompleted">清空已完成</button>
        <button class="ghost-btn sm" type="button" :disabled="loading" @click="refresh">刷新</button>
      </div>
    </div>

    <div v-if="loading && !tasks.length" class="op-hint">加载中…</div>
    <div v-else-if="!tasks.length" class="op-hint">暂无离线任务</div>

    <div v-else class="op-list">
      <div v-for="task in tasks" :key="task.info_hash || task.file_id" class="op-row">
        <div class="op-main">
          <div class="op-name" :title="task.name">{{ task.name || '未命名任务' }}</div>
          <div class="op-sub">
            <span class="op-pill" :class="statusClass(task.status)">{{ statusText(task) }}</span>
            <span class="op-size">{{ formatSize(task.size) }}</span>
            <span v-if="task.status === 1" class="op-pct">{{ percent(task) }}%</span>
          </div>
          <div v-if="task.status === 1" class="op-bar"><span :style="{ '--pct': percent(task) + '%' }"></span></div>
        </div>
        <button class="ghost-btn sm danger" type="button" :disabled="busy" @click="remove(task)">删除</button>
      </div>
    </div>
    <div v-if="totalCount > tasks.length" class="op-foot">共 {{ totalCount }} 个任务,显示最近 {{ tasks.length }} 个</div>
  </section>
</template>

<script>
import api from '../../api'
import { ElMessage } from '../../utils/message.js'
import { requestConfirm } from '../../utils/confirmDialog'
import { formatSize } from './driveFormat'

const STATUS_TEXT = { '-1': '失败', 0: '排队中', 1: '下载中', 2: '已完成' }

export default {
  name: 'OfflinePanel',
  emits: ['add', 'changed'],
  data() {
    return { tasks: [], totalCount: 0, quota: null, loading: false, busy: false, timer: null }
  },
  mounted() {
    this.refresh()
    this.loadQuota()
    this.timer = setInterval(this.refresh, 8000)
  },
  beforeUnmount() {
    if (this.timer) clearInterval(this.timer)
  },
  methods: {
    formatSize,
    async refresh() {
      this.loading = true
      try {
        const { data } = await api.listOpen115OfflineTasks(1)
        this.tasks = data.tasks || []
        this.totalCount = data.count || this.tasks.length
      } catch {
        /* silent: panel stays with last data */
      } finally {
        this.loading = false
      }
    },
    async loadQuota() {
      try {
        const { data } = await api.getOpen115Quota()
        this.quota = data
      } catch {
        this.quota = null
      }
    },
    percent(task) {
      const p = Number(task.percentDone || 0)
      return Math.max(0, Math.min(100, Math.round(p)))
    },
    statusText(task) {
      return task.status_text || STATUS_TEXT[String(task.status)] || '处理中'
    },
    statusClass(status) {
      return { '-1': 'failed', 0: 'queued', 1: 'running', 2: 'done' }[String(status)] || ''
    },
    async remove(task) {
      const ok = await requestConfirm({
        title: '删除离线任务',
        message: `确认删除「${task.name || task.info_hash}」?`,
        details: '只删除 115 离线任务,不会删除已下载到网盘的文件。',
        confirmText: '删除',
        tone: 'danger',
      })
      if (!ok) return
      this.busy = true
      try {
        await api.deleteOpen115OfflineTask({ infoHash: task.info_hash })
        ElMessage.success('已删除离线任务')
        await this.refresh()
        this.$emit('changed')
      } catch {
        ElMessage.error('删除失败')
      } finally {
        this.busy = false
      }
    },
    async clearCompleted() {
      const ok = await requestConfirm({
        title: '清空已完成',
        message: '确认清空所有已完成的离线任务?',
        details: '只清理任务列表,不会删除已下载到网盘的文件。',
        confirmText: '清空',
      })
      if (!ok) return
      this.busy = true
      try {
        await api.clearOpen115OfflineTasks(0)
        ElMessage.success('已清空完成任务')
        await this.refresh()
      } catch {
        ElMessage.error('清空失败')
      } finally {
        this.busy = false
      }
    },
    reload() {
      this.refresh()
      this.loadQuota()
    },
  },
}
</script>

<style scoped>
.offline-panel { border: 1px solid var(--border); border-radius: var(--radius-card); background: var(--surface-card); padding: 14px; display: flex; flex-direction: column; gap: 10px; }
.op-head { display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap; }
.op-title { display: flex; align-items: baseline; gap: 10px; }
.op-title strong { font-size: var(--type-card-title); color: var(--text-primary); }
.op-quota { font-size: var(--type-caption); color: var(--text-secondary); }
.op-quota.low { color: var(--badge-error-text); }
.op-actions { display: flex; gap: 6px; flex-wrap: wrap; }

.ghost-btn { background: var(--surface-control); border: 1px solid var(--border); border-radius: var(--radius-control); padding: 7px 14px; color: var(--text-primary); font-size: var(--type-control); cursor: pointer; }
.ghost-btn:hover:not(:disabled) { background: var(--surface-control-hover); }
.ghost-btn:disabled { opacity: .45; cursor: not-allowed; }
.ghost-btn.sm { padding: 5px 10px; font-size: var(--type-caption); }
.ghost-btn.danger { color: var(--badge-error-text); }

.op-hint { color: var(--text-muted); font-size: var(--type-caption); padding: 12px 2px; text-align: center; }
.op-list { display: flex; flex-direction: column; gap: 6px; max-height: 320px; overflow-y: auto; }
.op-row { display: flex; align-items: center; gap: 12px; padding: 10px 12px; border: 1px solid var(--hairline); border-radius: var(--radius-md); background: var(--card-2); }
.op-main { min-width: 0; flex: 1; }
.op-name { font-size: var(--type-control); color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.op-sub { display: flex; align-items: center; gap: 8px; margin-top: 4px; }
.op-size, .op-pct { font-size: var(--type-micro); color: var(--text-muted); }
.op-pill { font-size: var(--type-micro); font-weight: 700; padding: 2px 8px; border-radius: var(--radius-xs); border: 1px solid var(--hairline); color: var(--text-muted); background: var(--card); }
.op-pill.running { color: var(--badge-info-text); border-color: var(--badge-info-border); }
.op-pill.done { color: var(--badge-success-text); border-color: var(--badge-success-border); }
.op-pill.failed { color: var(--badge-error-text); border-color: var(--badge-error-border); }
.op-bar { margin-top: 6px; height: 4px; border-radius: 2px; background: var(--surface-control); overflow: hidden; }
.op-bar span { display: block; height: 100%; width: var(--pct, 0%); background: var(--accent); }
.op-foot { font-size: var(--type-micro); color: var(--text-muted); text-align: center; }
</style>

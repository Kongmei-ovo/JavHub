<template>
  <div v-if="tasks.length > 0" class="tasks-grid">
    <div v-for="task in tasks" :key="task.id" class="task-card av-card">
      <div class="task-cover">
        <div class="cover-placeholder">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="40" height="40">
            <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/>
            <line x1="7" y1="2" x2="7" y2="22"/>
            <line x1="17" y1="2" x2="17" y2="22"/>
            <line x1="2" y1="12" x2="22" y2="12"/>
            <line x1="2" y1="7" x2="7" y2="7"/>
            <line x1="2" y1="17" x2="7" y2="17"/>
            <line x1="17" y1="17" x2="22" y2="17"/>
            <line x1="17" y1="7" x2="22" y2="7"/>
          </svg>
        </div>
        <div class="cover-overlay">
          <span class="cover-code">{{ task.content_id || task.code }}</span>
        </div>
        <div v-if="task.status === 'downloading'" class="progress-overlay">
          <div class="progress-bar">
            <div class="progress-bar-fill progress-bar-fill-demo"></div>
          </div>
        </div>
      </div>

      <div class="task-info">
        <h3 class="task-title" :title="task.title">{{ task.title }}</h3>
        <div class="task-meta">
          <span :class="['badge', statusBadge(task.status)]">{{ statusLabel(task.status) }}</span>
          <span class="task-time">{{ formatTime(task.created_at) }}</span>
        </div>
        <div class="task-downloader">{{ task.downloader_name || downloaderTypeLabel(task.downloader_type) || '默认下载源' }}</div>
        <div v-if="task.error_msg" class="task-error">{{ task.error_msg }}</div>
      </div>

      <div class="task-actions">
        <button v-if="task.status === 'failed'" class="btn btn-primary" type="button" :disabled="retryingTasks[task.id]" @click="$emit('retry', task)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14">
            <polyline points="23 4 23 10 17 10"/>
            <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/>
          </svg>
          {{ retryingTasks[task.id] ? '重试中...' : '重试' }}
        </button>
        <button class="btn btn-ghost" type="button" @click="$emit('remove', task.id)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14">
            <polyline points="3 6 5 6 21 6"/>
            <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
          </svg>
          删除
        </button>
      </div>
    </div>
  </div>

  <AppleEmptyState
    v-else
    class="empty-state"
    :title="taskEmptyTitle"
    :description="taskEmptyHint"
    next-step="可以清除筛选、处理下载候选，或从影片检索和磁链解析添加新任务。"
    :action-label="taskEmptyPrimaryLabel"
    secondary-action-label="磁链解析"
    density="compact"
    @action="$emit('empty-action')"
    @secondary-action="$emit('parse')"
  >
    <template #icon>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
        <polyline points="7 10 12 15 17 10"/>
        <line x1="12" y1="15" x2="12" y2="3"/>
      </svg>
    </template>
  </AppleEmptyState>
</template>

<script>
import AppleEmptyState from '../../components/AppleEmptyState.vue'

export default {
  name: 'TaskList',
  components: { AppleEmptyState },
  props: {
    tasks: { type: Array, required: true },
    retryingTasks: { type: Object, default: () => ({}) },
    statusBadge: { type: Function, required: true },
    statusLabel: { type: Function, required: true },
    formatTime: { type: Function, required: true },
    downloaderTypeLabel: { type: Function, required: true },
    taskEmptyTitle: { type: String, required: true },
    taskEmptyHint: { type: String, required: true },
    taskEmptyPrimaryLabel: { type: String, required: true },
  },
  emits: ['retry', 'remove', 'empty-action', 'parse'],
}
</script>

<style scoped src="./home.css"></style>

<template>
  <div v-if="tasks.length > 0" class="tasks-grid">
    <article v-for="task in tasks" :key="task.id" class="task-card">
      <div class="task-cover">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true">
          <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
          <polyline points="7 10 12 15 17 10"/>
          <line x1="12" y1="15" x2="12" y2="3"/>
        </svg>
        <span class="cover-code">{{ task.content_id || task.code || `#${task.id}` }}</span>
      </div>

      <div class="task-info">
        <h3 class="task-title" :title="task.title">{{ task.title }}</h3>
        <div class="task-meta">
          <span class="task-downloader">{{ task.downloader_name || downloaderTypeLabel(task.downloader_type) || '默认下载源' }}</span>
          <span class="task-time">{{ formatTime(task.created_at) }}</span>
        </div>
        <div v-if="task.error_msg" class="task-error">{{ task.error_msg }}</div>
      </div>

      <div class="task-status">
        <span :class="['badge', statusBadge(task.status)]">{{ statusLabel(task.status) }}</span>
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
    </article>
  </div>

  <AppleEmptyState
    v-else
    class="empty-state"
    :title="taskEmptyTitle"
    :description="taskEmptyHint"
    next-step="可以清除筛选，或从影库添加新任务，或直接添加磁链。"
    :action-label="taskEmptyPrimaryLabel"
    secondary-action-label="添加下载"
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

<style scoped src="./downloads.css"></style>

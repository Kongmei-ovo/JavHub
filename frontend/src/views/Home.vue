<template>
  <div class="home">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <h1>下载管理</h1>
        <p class="header-subtitle">
          <span class="total-tasks">{{ stats.pending + stats.downloading + stats.completed + stats.failed }} 个任务</span>
          <span v-if="stats.downloading > 0" class="downloading-hint">
            · {{ stats.downloading }} 个下载中
          </span>
        </p>
      </div>
      <div class="header-actions">
        <button class="btn btn-ghost" @click="$router.push('/search')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <circle cx="11" cy="11" r="8"/>
            <path d="m21 21-4.35-4.35"/>
          </svg>
          搜索影片
        </button>
        <button class="btn btn-ghost" @click="$router.push('/genres')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <path d="M4 19.5A2.5 2.5 0 016.5 17H20"/>
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/>
          </svg>
          浏览分类
        </button>
        <button class="btn btn-primary" @click="loadTasks">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <polyline points="23 4 23 10 17 10"/>
            <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/>
          </svg>
          刷新
        </button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-bar">
      <div class="stat-card" @click="filterStatus = 'pending'">
        <div class="stat-icon pending">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12 6 12 12 16 14"/>
          </svg>
        </div>
        <div class="stat-info">
          <div class="stat-num">{{ stats.pending }}</div>
          <div class="stat-label">待处理</div>
        </div>
      </div>
      <div class="stat-card" @click="filterStatus = 'downloading'">
        <div class="stat-icon downloading">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
            <polyline points="7 10 12 15 17 10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
        </div>
        <div class="stat-info">
          <div class="stat-num">{{ stats.downloading }}</div>
          <div class="stat-label">下载中</div>
        </div>
      </div>
      <div class="stat-card" @click="filterStatus = 'completed'">
        <div class="stat-icon completed">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M22 11.08V12a10 10 0 11-5.93-9.14"/>
            <polyline points="22 4 12 14.01 9 11.01"/>
          </svg>
        </div>
        <div class="stat-info">
          <div class="stat-num">{{ stats.completed }}</div>
          <div class="stat-label">已完成</div>
        </div>
      </div>
      <div class="stat-card" @click="filterStatus = 'failed'">
        <div class="stat-icon failed">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"/>
            <line x1="15" y1="9" x2="9" y2="15"/>
            <line x1="9" y1="9" x2="15" y2="15"/>
          </svg>
        </div>
        <div class="stat-info">
          <div class="stat-num">{{ stats.failed }}</div>
          <div class="stat-label">失败</div>
        </div>
      </div>
    </div>

    <!-- 任务过滤栏 -->
    <div v-if="filterStatus" class="filter-bar" @click="filterStatus = null">
      <span class="filter-hint">筛选: <strong>{{ filterStatus }}</strong> (点击清除)</span>
    </div>

    <!-- 任务卡片网格 -->
    <div v-if="filteredTasks.length > 0" class="tasks-grid">
      <div
        v-for="task in filteredTasks"
        :key="task.id"
        class="task-card av-card"
      >
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
            <span class="cover-code">{{ task.code }}</span>
          </div>
          <!-- 下载进度条 -->
          <div v-if="task.status === 'downloading'" class="progress-overlay">
            <div class="progress-bar">
              <div class="progress-bar-fill" style="width: 60%"></div>
            </div>
          </div>
        </div>

        <div class="task-info">
          <h3 class="task-title" :title="task.title">{{ task.title }}</h3>
          <div class="task-meta">
            <span :class="['badge', statusBadge(task.status)]">{{ statusLabel(task.status) }}</span>
            <span class="task-time">{{ formatTime(task.created_at) }}</span>
          </div>
          <div v-if="task.error_msg" class="task-error">{{ task.error_msg }}</div>
        </div>

        <div class="task-actions">
          <button
            v-if="task.status === 'failed'"
            class="btn btn-primary"
            @click="retry(task)"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <polyline points="23 4 23 10 17 10"/>
              <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/>
            </svg>
            重试
          </button>
          <button class="btn btn-ghost" @click="remove(task.id)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
            </svg>
            删除
          </button>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="empty-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
        <polyline points="7 10 12 15 17 10"/>
        <line x1="12" y1="15" x2="12" y2="3"/>
      </svg>
      <p>暂无{{ filterStatus ? statusLabel(filterStatus) : '' }}任务</p>
      <p class="text-secondary" style="font-size:13px;margin-top:6px">去搜索页面添加下载吧</p>
    </div>
  </div>
</template>

<script>
import api from '../api'

export default {
  name: 'Home',
  data() {
    return {
      tasks: [],
      stats: { pending: 0, downloading: 0, completed: 0, failed: 0 },
      filterStatus: null,
      timer: null
    }
  },
  computed: {
    filteredTasks() {
      if (!this.filterStatus) return this.tasks
      return this.tasks.filter(t => t.status === this.filterStatus)
    }
  },
  mounted() {
    this.loadTasks()
    this.timer = setInterval(this.loadTasks, 30000)
  },
  beforeUnmount() {
    if (this.timer) clearInterval(this.timer)
  },
  methods: {
    async loadTasks() {
      try {
        const resp = await api.getDownloads()
        this.tasks = resp.data.data || []
        this.stats = {
          pending: this.tasks.filter(t => t.status === 'pending').length,
          downloading: this.tasks.filter(t => t.status === 'downloading').length,
          completed: this.tasks.filter(t => t.status === 'completed').length,
          failed: this.tasks.filter(t => t.status === 'failed').length
        }
      } catch (e) {
        console.error('Failed to load tasks:', e)
      }
    },
    async remove(id) {
      try {
        await api.deleteDownload(id)
        this.loadTasks()
      } catch (e) {
        console.error('Failed to delete:', e)
      }
    },
    retry(task) {
      api.createDownload({ code: task.code, title: task.title, magnet: task.magnet, path: task.path })
      this.loadTasks()
    },
    statusBadge(status) {
      const map = { pending: 'badge-pending', downloading: 'badge-info', completed: 'badge-success', failed: 'badge-error' }
      return map[status] || 'badge-pending'
    },
    statusLabel(status) {
      const map = { pending: '待处理', downloading: '下载中', completed: '已完成', failed: '失败' }
      return map[status] || status
    },
    formatTime(time) {
      if (!time) return ''
      const d = new Date(time)
      return `${d.getMonth()+1}/${d.getDate()} ${d.getHours().toString().padStart(2,'0')}:${d.getMinutes().toString().padStart(2,'0')}`
    }
  }
}
</script>

<style scoped>
.home { padding: 24px; max-width: 1400px; margin: 0 auto; }

/* ===== Header ===== */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
  gap: 16px;
  flex-wrap: wrap;
}
.header-left { display: flex; flex-direction: column; gap: 4px; }
.page-header h1 { font-size: 24px; font-weight: 700; color: var(--text-primary); }
.header-subtitle { font-size: 13px; color: var(--text-muted); }
.downloading-hint { color: #42A5F5; }
.header-actions { display: flex; gap: 8px; }
.header-actions .btn { gap: 6px; }

/* ===== Stats Bar ===== */
.stats-bar {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  cursor: pointer;
  transition: var(--transition);
}
.stat-card:hover { border-color: var(--border-light); transform: translateY(-2px); }

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.stat-icon svg { width: 24px; height: 24px; }
.stat-icon.pending { background: rgba(158, 158, 158, 0.15); color: var(--text-secondary); }
.stat-icon.downloading { background: rgba(33, 150, 243, 0.15); color: #42A5F5; }
.stat-icon.completed { background: rgba(76, 175, 80, 0.15); color: var(--accent-light); }
.stat-icon.failed { background: rgba(244, 67, 54, 0.15); color: #EF5350; }

.stat-info { min-width: 0; }
.stat-num { font-size: 28px; font-weight: 700; color: var(--text-primary); line-height: 1; }
.stat-label { font-size: 13px; color: var(--text-secondary); margin-top: 4px; }

/* ===== Filter Bar ===== */
.filter-bar {
  background: rgba(76, 175, 80, 0.08);
  border: 1px solid rgba(76, 175, 80, 0.2);
  border-radius: var(--radius-sm);
  padding: 10px 16px;
  margin-bottom: 16px;
  cursor: pointer;
  transition: var(--transition);
}
.filter-bar:hover { background: rgba(76, 175, 80, 0.12); }
.filter-hint { font-size: 13px; color: var(--text-secondary); }
.filter-hint strong { color: var(--accent); }

/* ===== Tasks Grid ===== */
.tasks-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 20px;
}

/* ===== Task Card ===== */
.task-card {
  display: flex;
  flex-direction: column;
}

.task-cover {
  position: relative;
  aspect-ratio: 16/9;
  background: var(--bg-secondary);
  overflow: hidden;
}

.cover-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--bg-secondary) 0%, var(--bg-card) 100%);
  color: var(--text-muted);
}

.cover-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 8px 10px;
  background: linear-gradient(transparent, rgba(0,0,0,0.8));
}
.cover-code { font-size: 13px; font-weight: 600; color: white; }

.progress-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 0 8px 6px;
}
.progress-overlay .progress-bar { height: 3px; }
.progress-overlay .progress-bar-fill { animation: progress-pulse 1.5s ease-in-out infinite; }

@keyframes progress-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

.task-info { padding: 12px; flex: 1; }
.task-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  margin-bottom: 8px;
}
.task-meta { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.task-time { font-size: 11px; color: var(--text-muted); }
.task-error { font-size: 11px; color: #EF5350; margin-top: 6px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.task-actions {
  display: flex;
  gap: 8px;
  padding: 10px 12px;
  border-top: 1px solid var(--border);
}
.task-actions .btn { flex: 1; justify-content: center; font-size: 12px; padding: 6px 10px; }

/* ===== Responsive ===== */
@media (max-width: 768px) {
  .home { padding: 16px; }
  .stats-bar { grid-template-columns: repeat(2, 1fr); gap: 10px; }
  .stat-card { padding: 14px; gap: 12px; }
  .stat-num { font-size: 22px; }
  .stat-icon { width: 40px; height: 40px; }
  .tasks-grid { grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
}
</style>

<template>
  <div class="home page-shell page-shell--workspace">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <h1>下载管理</h1>
        <p class="header-subtitle">
          <span class="total-tasks">{{ stats.pending + stats.downloading + stats.completed + stats.failed }} 个任务</span>
          <span v-if="stats.downloading > 0" class="downloading-hint">
            · {{ stats.downloading }} 个下载中
          </span>
          <span v-if="candidateStats.candidate > 0" class="downloading-hint">
            · {{ candidateStats.candidate }} 个候选待确认
          </span>
        </p>
      </div>
      <div class="header-actions">
        <button class="btn btn-ghost" type="button" @click="$router.push('/search')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16">
            <circle cx="11" cy="11" r="8"/>
            <path d="m21 21-4.35-4.35"/>
          </svg>
          搜索影片
        </button>
        <button class="btn btn-ghost" type="button" @click="$router.push('/genres')">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16">
            <path d="M4 19.5A2.5 2.5 0 016.5 17H20"/>
            <path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/>
          </svg>
          浏览分类
        </button>
        <button class="btn btn-primary" type="button" @click="loadTasks">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16">
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
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="12" cy="12" r="10"/>
            <polyline points="12 6 12 12 16 14"/>
          </svg>
        </div>
        <div class="stat-info">
          <div class="stat-num" :class="{ 'animate-in': statsLoaded }">{{ stats.pending }}</div>
          <div class="stat-label">待处理</div>
        </div>
      </div>
      <div class="stat-card" @click="filterStatus = 'downloading'">
        <div class="stat-icon downloading">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
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
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
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
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
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

    <div class="candidate-overview">
      <button class="candidate-metric" type="button" @click="openCandidatePreset({ status: 'candidate', source: '' })">
        <span class="metric-value">{{ candidateStats.candidate || 0 }}</span>
        <span class="metric-label">待确认候选</span>
      </button>
      <button class="candidate-metric" type="button" @click="openCandidatePreset({ status: 'candidate', needs_magnet: true, source: '' })">
        <span class="metric-value">{{ candidateStats.needs_magnet || 0 }}</span>
        <span class="metric-label">待补磁力</span>
      </button>
      <button class="candidate-metric" type="button" @click="openCandidatePreset({ status: 'candidate', needs_magnet: false, source: '' })">
        <span class="metric-value">{{ readyCandidateCount }}</span>
        <span class="metric-label">可批准</span>
      </button>
      <button class="candidate-metric" type="button" @click="openCandidatePreset({ status: 'candidate', source: 'subscription' })">
        <span class="metric-value">{{ candidateStats.candidate_by_source?.subscription || 0 }}</span>
        <span class="metric-label">订阅发现</span>
      </button>
      <button class="candidate-metric" type="button" @click="openCandidatePreset({ status: 'candidate', source: 'inventory' })">
        <span class="metric-value">{{ candidateStats.candidate_by_source?.inventory || 0 }}</span>
        <span class="metric-label">库存发现</span>
      </button>
      <button class="candidate-metric" type="button" @click="openCandidatePreset({ status: 'candidate', source: 'supplement' })">
        <span class="metric-value">{{ candidateStats.candidate_by_source?.supplement || 0 }}</span>
        <span class="metric-label">补全发现</span>
      </button>
    </div>

    <!-- 任务过滤栏 -->
    <div v-if="filterStatus" class="filter-bar" @click="filterStatus = null">
      <span class="filter-hint">筛选: <strong>{{ filterStatus }}</strong> (点击清除)</span>
    </div>

    <div class="download-tabs">
      <button class="tab-btn" type="button" :class="{ active: activeTab === 'tasks' }" @click="activeTab = 'tasks'">真实任务</button>
      <button class="tab-btn" type="button" :class="{ active: activeTab === 'candidates' }" @click="openCandidateTab">
        下载候选
        <span v-if="candidateStats.candidate" class="tab-badge">{{ candidateStats.candidate }}</span>
      </button>
      <button class="tab-btn" type="button" :class="{ active: activeTab === 'downloaders' }" @click="openDownloaderTab">
        下载源
        <span v-if="enabledDownloaderCount" class="tab-badge subtle">{{ enabledDownloaderCount }}</span>
      </button>
    </div>

    <!-- 任务卡片网格 -->
    <div v-if="activeTab === 'tasks' && filteredTasks.length > 0" class="tasks-grid">
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
            <span class="cover-code">{{ task.content_id || task.code }}</span>
          </div>
          <!-- 下载进度条 -->
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
          <button
            v-if="task.status === 'failed'"
            class="btn btn-primary"
            type="button"
            :disabled="retryingTasks[task.id]"
            @click="retry(task)"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14">
              <polyline points="23 4 23 10 17 10"/>
              <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/>
            </svg>
            {{ retryingTasks[task.id] ? '重试中...' : '重试' }}
          </button>
          <button class="btn btn-ghost" type="button" @click="remove(task.id)">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="14" height="14">
              <polyline points="3 6 5 6 21 6"/>
              <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
            </svg>
            删除
          </button>
        </div>
      </div>
    </div>

    <div v-else-if="activeTab === 'candidates'" class="candidate-panel">
      <div class="candidate-toolbar">
        <input
          v-model="candidateFilter.q"
          class="candidate-search-input"
          placeholder="搜索番号、标题、演员"
          @keyup.enter="loadCandidates"
        />
        <button class="chip" type="button" @click="loadCandidates">搜索</button>
        <button class="chip" type="button" :class="{ active: candidateFilter.status === 'candidate' }" @click="setCandidateStatus('candidate')">待确认</button>
        <button class="chip" type="button" :class="{ active: candidateFilter.status === 'candidate' && candidateFilter.needs_magnet === true }" @click="setNeedsMagnet(true)">待补磁力</button>
        <button class="chip" type="button" :class="{ active: candidateFilter.status === 'candidate' && candidateFilter.needs_magnet === false }" @click="setNeedsMagnet(false)">可批准</button>
        <button class="chip" type="button" :class="{ active: candidateFilter.status === 'sent' }" @click="setCandidateStatus('sent')">已下发</button>
        <button class="chip" type="button" :class="{ active: candidateFilter.status === 'failed' }" @click="setCandidateStatus('failed')">失败</button>
        <button class="chip" type="button" :class="{ active: candidateFilter.status === 'rejected' }" @click="setCandidateStatus('rejected')">已拒绝</button>
        <button class="chip" type="button" :class="{ active: !candidateFilter.status }" @click="setCandidateStatus('')">全部</button>
        <button class="chip" type="button" :class="{ active: candidateFilter.source === 'subscription' }" @click="setCandidateSource('subscription')">
          订阅 {{ candidateStats.by_source?.subscription || 0 }}
        </button>
        <button class="chip" type="button" :class="{ active: candidateFilter.source === 'inventory' }" @click="setCandidateSource('inventory')">
          库存 {{ candidateStats.by_source?.inventory || 0 }}
        </button>
        <button class="chip" type="button" :class="{ active: candidateFilter.source === 'supplement' }" @click="setCandidateSource('supplement')">
          补全 {{ candidateStats.by_source?.supplement || 0 }}
        </button>
        <button class="chip" type="button" :class="{ active: !candidateFilter.source }" @click="setCandidateSource('')">全部来源</button>
        <button class="chip" type="button" :class="{ active: selectingCandidates }" @click="toggleCandidateSelection">
          {{ selectingCandidates ? '退出选择' : '选择' }}
        </button>
        <button class="chip action-chip" type="button" :disabled="candidateBatchProcessing" @click="enrichVisibleCandidateMagnets">
          {{ candidateBatchProcessing === 'enrich' ? '补磁力中...' : '补当前磁力' }}
        </button>
        <button class="chip action-chip primary" type="button" :disabled="candidateBatchProcessing" @click="processVisibleCandidates">
          {{ candidateBatchProcessing === 'dry-run' ? '预演中...' : (candidateBatchProcessing === 'process' ? '处理中...' : '按策略处理当前') }}
        </button>
      </div>

      <div v-if="selectingCandidates" class="bulk-toolbar">
        <span>已选 {{ selectedCandidateIds.length }} 个</span>
        <button class="btn btn-ghost" type="button" @click="selectAllVisibleCandidates">选择当前页</button>
        <button class="btn btn-ghost" type="button" @click="clearCandidateSelection">清空</button>
        <button class="btn btn-ghost" type="button" :disabled="selectedCandidateIds.length === 0 || bulkCandidateLoading" @click="bulkRejectCandidates">批量拒绝</button>
        <button class="btn btn-primary" type="button" :disabled="selectedCandidateIds.length === 0 || bulkCandidateLoading" @click="bulkRestoreCandidates">批量恢复</button>
      </div>

      <CandidateRunPanel
        :runs="candidateRuns"
        :loading="candidateRunsLoading"
        :processing="candidateBatchProcessing"
        @refresh="loadCandidateRuns"
        @apply="applyCandidateRunFilters"
        @apply-failed="applyCandidateRunFilters($event, { status: 'failed' })"
        @retry-failed="retryFailedCandidateRun"
      />

      <div v-if="filteredCandidates.length > 0" class="tasks-grid">
        <div
          v-for="candidate in filteredCandidates"
          :key="candidate.id"
          class="task-card av-card candidate-card"
        >
          <label v-if="selectingCandidates" class="candidate-select" @click.stop>
            <input
              type="checkbox"
              :checked="selectedCandidateIds.includes(candidate.id)"
              @change="toggleCandidateSelected(candidate.id)"
            />
          </label>
          <div class="task-cover">
            <img v-if="candidate.jacket_thumb_url" :src="candidate.jacket_thumb_url" :alt="candidate.title || candidate.content_id" />
            <div v-else class="cover-placeholder">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="40" height="40">
                <rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/>
                <line x1="7" y1="2" x2="7" y2="22"/>
                <line x1="17" y1="2" x2="17" y2="22"/>
              </svg>
            </div>
            <div class="cover-overlay">
              <span class="cover-code">{{ candidate.dvd_id || candidate.content_id }}</span>
            </div>
          </div>

          <div class="task-info">
            <h3 class="task-title" :title="candidate.title">{{ candidate.title || candidate.content_id }}</h3>
            <div class="task-meta">
              <span :class="['badge', candidateBadge(candidate.status)]">{{ candidateStatusLabel(candidate.status) }}</span>
              <span class="task-time">{{ candidateSourceLabel(candidate.source) }}</span>
            </div>
            <div class="candidate-subtitle">{{ candidate.actress_name || '未知演员' }} · {{ candidate.release_date || '日期未知' }}</div>
            <div class="candidate-magnet" :class="{ empty: !candidate.magnet }">
              {{ candidate.magnet ? '已有 magnet' : '待补磁力' }}
            </div>
            <div v-if="candidate.reason" class="candidate-reason" :title="candidate.reason">
              {{ candidate.reason }}
            </div>
            <div v-if="candidate.download_task_id" class="candidate-task-link">
              已关联任务 #{{ candidate.download_task_id }}
              <span v-if="candidate.download_task?.status">· {{ statusLabel(candidate.download_task.status) }}</span>
              <span v-if="candidate.download_task?.downloader_name">· {{ candidate.download_task.downloader_name }}</span>
            </div>
            <div v-if="candidate.error_msg" class="task-error" :title="candidate.error_msg">
              {{ candidate.error_msg }}
            </div>
            <div v-if="candidate.events?.length" class="candidate-event">
              最近动作 {{ candidate.events[0].action }}
            </div>
            <div class="candidate-context-actions">
              <button class="link-btn" type="button" @click="openCandidateDetail(candidate)">详情</button>
              <button v-if="candidate.actress_id" class="link-btn" type="button" @click="goCandidateActor(candidate)">演员</button>
              <button v-if="candidate.source === 'supplement' && candidate.actress_id" class="link-btn" type="button" @click="goCandidateSupplement(candidate)">补全</button>
            </div>
          </div>

          <div class="task-actions">
            <button v-if="candidate.status === 'candidate' || candidate.status === 'failed'" class="btn btn-ghost" type="button" :disabled="isCandidateMutating(candidate.id)" @click="editCandidateMagnet(candidate)">填磁力</button>
            <button v-if="(candidate.status === 'candidate' || candidate.status === 'failed') && !candidate.magnet" class="btn btn-ghost" type="button" :disabled="isCandidateMutating(candidate.id)" @click="enrichCandidateMagnet(candidate)">
              {{ candidateMutations[candidate.id] === 'enrich' ? '查找中...' : '补磁力' }}
            </button>
            <button v-if="candidate.status === 'candidate' || candidate.status === 'failed'" class="btn btn-primary" type="button" :disabled="isCandidateMutating(candidate.id)" @click="approveCandidate(candidate)">
              {{ candidateMutations[candidate.id] === 'approve' ? '处理中...' : (candidate.status === 'failed' ? '重试' : '批准') }}
            </button>
            <button v-if="candidate.status === 'candidate' || candidate.status === 'failed'" class="btn btn-primary" type="button" :disabled="isCandidateMutating(candidate.id)" @click="processCandidate(candidate)">
              {{ candidateMutations[candidate.id] === 'process' ? '处理中...' : '策略处理' }}
            </button>
            <button v-if="candidate.status === 'candidate'" class="btn btn-ghost" type="button" :disabled="isCandidateMutating(candidate.id)" @click="rejectCandidate(candidate)">拒绝</button>
          </div>
        </div>
      </div>

      <div v-else class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
          <polyline points="7 10 12 15 17 10"/>
          <line x1="12" y1="15" x2="12" y2="3"/>
        </svg>
        <p>暂无下载候选</p>
        <p class="text-secondary empty-state-hint">订阅检查和库存对比会把缺失影片写到这里</p>
      </div>
    </div>

    <div v-else-if="activeTab === 'downloaders'" class="downloaders-panel apple-reveal">
      <div class="downloader-toolbar apple-surface">
        <div class="downloader-toolbar-copy">
          <strong>下载源</strong>
          <span>默认 {{ defaultDownloaderLabel }} · {{ enabledDownloaderCount }} 个已启用</span>
        </div>
        <div class="downloader-toolbar-actions">
          <button class="icon-action" type="button" title="刷新下载源" aria-label="刷新下载源" @click="loadDownloaders">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
              <polyline points="23 4 23 10 17 10"/>
              <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/>
            </svg>
          </button>
          <button class="icon-action primary" type="button" title="新增下载源" aria-label="新增下载源" @click="openNewDownloader">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
              <line x1="12" y1="5" x2="12" y2="19"/>
              <line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
          </button>
        </div>
      </div>

      <div class="downloaders-list apple-surface">
        <article
          v-for="client in downloaderClients"
          :key="client.id"
          class="downloader-row"
          :class="{ disabled: !client.enabled, default: client.id === downloaders.default_id }"
          role="button"
          tabindex="0"
          @click="editDownloader(client)"
          @keyup.enter="editDownloader(client)"
        >
          <div class="downloader-row-main">
            <div class="downloader-avatar" :class="{ muted: !client.enabled }">
              {{ downloaderTypeMark(client.type) }}
            </div>
            <div class="downloader-copy">
              <div class="downloader-title-line">
                <strong>{{ client.name || downloaderTypeLabel(client.type) }}</strong>
                <span>{{ downloaderTypeLabel(client.type) }}</span>
              </div>
              <div class="downloader-summary">
                <span :title="client.address || ''">{{ shortDownloaderAddress(client.address) || '未配置地址' }}</span>
                <span :title="client.default_path || ''">{{ downloaderPathSummary(client) }}</span>
              </div>
            </div>
          </div>

          <div class="downloader-status-group">
            <span v-if="client.id === downloaders.default_id" class="downloader-pill default">默认</span>
            <span class="downloader-pill" :class="client.enabled ? 'enabled' : 'muted'">{{ client.enabled ? '启用' : '停用' }}</span>
            <span
              v-if="downloaderTestMessages[client.id]"
              class="downloader-pill test"
              :class="{ ok: downloaderTestMessages[client.id].ok }"
              :title="downloaderTestMessages[client.id].message"
            >
              {{ downloaderTestMessages[client.id].ok ? '已连接' : '失败' }}
            </span>
          </div>

          <label class="switch-mini switch-apple" title="启用下载源" @click.stop>
            <input type="checkbox" v-model="client.enabled" />
            <span></span>
          </label>

          <div class="downloader-row-actions" @click.stop>
            <button class="icon-action compact" type="button" :disabled="testingDownloaderId === client.id" title="测试连接" aria-label="测试连接" @click="testDownloader(client)">
              <svg v-if="testingDownloaderId !== client.id" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <path d="M22 12h-4l-3 8-6-16-3 8H2"/>
              </svg>
              <svg v-else class="spin-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
                <path d="M21 12a9 9 0 11-6.2-8.56"/>
              </svg>
            </button>
            <button class="icon-action compact" type="button" :disabled="client.id === downloaders.default_id" title="设为默认" aria-label="设为默认" @click="setDefaultDownloader(client.id)">
              <svg viewBox="0 0 24 24" :fill="client.id === downloaders.default_id ? 'currentColor' : 'none'" stroke="currentColor" stroke-width="1.7">
                <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>
              </svg>
            </button>
            <button class="icon-action compact" type="button" title="编辑" aria-label="编辑" @click="editDownloader(client)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
                <path d="M12 20h9"/>
                <path d="M16.5 3.5a2.12 2.12 0 013 3L7 19l-4 1 1-4Z"/>
              </svg>
            </button>
            <button class="icon-action compact danger" type="button" :disabled="downloaderClients.length <= 1" title="删除" aria-label="删除" @click="removeDownloader(client.id)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
                <polyline points="3 6 5 6 21 6"/>
                <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6"/>
                <path d="M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
              </svg>
            </button>
          </div>
        </article>

        <div v-if="downloaderClients.length === 0" class="downloaders-empty">
          <strong>还没有下载源</strong>
          <span>添加一个下载器后就可以作为默认下载目标。</span>
        </div>
      </div>

      <div class="downloaders-footer apple-surface">
        <span>{{ downloaderClients.length }} 个下载源 · {{ enabledDownloaderCount }} 个启用</span>
        <button class="btn btn-primary" type="button" :disabled="savingDownloaders" @click="saveDownloaders">
          {{ savingDownloaders ? '保存中...' : '保存更改' }}
        </button>
      </div>

      <div v-if="downloaderEditor.open" class="inline-dialog-overlay downloader-sheet-overlay" @click.self="closeDownloaderEditor">
        <div class="inline-dialog downloader-sheet">
          <div class="inline-dialog-header">
            <div>
              <h2>{{ downloaderEditor.mode === 'new' ? '新增下载源' : '编辑下载源' }}</h2>
              <p>{{ downloaderEditor.draft?.name || downloaderTypeLabel(downloaderEditor.draft?.type) }}</p>
            </div>
            <button class="dialog-close-btn" type="button" aria-label="关闭" @click="closeDownloaderEditor">×</button>
          </div>

          <div v-if="downloaderEditor.draft" class="downloader-sheet-body">
            <section class="downloader-sheet-section">
              <div class="sheet-section-title">
                <strong>基础信息</strong>
                <span>名称、类型、地址、路径</span>
              </div>
              <div class="downloader-sheet-grid">
                <label>
                  名称
                  <input class="input" v-model="downloaderEditor.draft.name" placeholder="家庭 qBittorrent" />
                </label>
                <label>
                  类型
                  <select class="input" v-model="downloaderEditor.draft.type" @change="syncDownloaderDraftDefaults">
                    <option v-for="type in downloaderTypes" :key="type.value" :value="type.value">{{ type.label }}</option>
                  </select>
                </label>
                <label class="wide-field">
                  地址
                  <input class="input" v-model="downloaderEditor.draft.address" :placeholder="downloaderAddressPlaceholder(downloaderEditor.draft.type)" />
                </label>
                <label class="wide-field">
                  下载路径
                  <input class="input" v-model="downloaderEditor.draft.default_path" :placeholder="downloaderPathPlaceholder(downloaderEditor.draft.type)" />
                </label>
              </div>
            </section>

            <section class="downloader-sheet-section">
              <div class="sheet-section-title">
                <strong>连接与选项</strong>
                <span>凭据、标签、超时、偏好</span>
              </div>
              <div class="downloader-sheet-grid">
                <label>
                  用户名
                  <input class="input" v-model="downloaderEditor.draft.username" autocomplete="off" />
                </label>
                <label>
                  密码
                  <input class="input" type="password" v-model="downloaderEditor.draft.password" autocomplete="new-password" :placeholder="downloaderEditor.draft.password_configured ? '留空不覆盖已有密码' : ''" />
                </label>
                <label v-if="downloaderEditor.draft.type === 'openlist' || downloaderEditor.draft.type === 'aria2'">
                  Token
                  <input class="input" type="password" v-model="downloaderEditor.draft.token" autocomplete="new-password" :placeholder="downloaderEditor.draft.token_configured ? '留空不覆盖已有 Token' : tokenPlaceholder(downloaderEditor.draft.type)" />
                </label>
                <label v-if="downloaderEditor.draft.type === 'qbittorrent'">
                  分类
                  <input class="input" v-model="downloaderEditor.draft.category" placeholder="可选" />
                </label>
                <label v-if="supportsDownloaderTags(downloaderEditor.draft.type)">
                  标签
                  <input class="input" v-model="downloaderEditor.draft.tags" placeholder="javhub,auto" />
                </label>
                <label>
                  超时
                  <input class="input" type="number" min="1" v-model.number="downloaderEditor.draft.timeout" />
                </label>
              </div>
              <div class="downloader-sheet-options">
                <label>
                  <input type="checkbox" v-model="downloaderEditor.draft.enabled" />
                  启用
                </label>
                <label>
                  <input type="checkbox" v-model="downloaderEditor.draft.paused" />
                  添加后暂停
                </label>
              </div>
            </section>
          </div>

          <div class="inline-dialog-actions">
            <button class="btn btn-ghost" type="button" @click="closeDownloaderEditor">取消</button>
            <button class="btn btn-primary" type="button" @click="applyDownloaderEditor">完成</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="activeTab === 'tasks'" class="empty-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
        <polyline points="7 10 12 15 17 10"/>
        <line x1="12" y1="15" x2="12" y2="3"/>
      </svg>
      <p>暂无{{ filterStatus ? statusLabel(filterStatus) : '' }}任务</p>
      <p class="text-secondary empty-state-hint">去搜索页面添加下载吧</p>
    </div>

    <div v-if="magnetEditor.open" class="inline-dialog-overlay" @click.self="closeMagnetEditor">
      <div class="inline-dialog">
        <div class="inline-dialog-header">
          <div>
            <h2>填磁力</h2>
            <p>{{ magnetEditor.candidate?.dvd_id || magnetEditor.candidate?.content_id || '下载候选' }}</p>
          </div>
          <button class="dialog-close-btn" type="button" @click="closeMagnetEditor">×</button>
        </div>
        <textarea
          v-model="magnetEditor.value"
          class="magnet-editor-input"
          placeholder="magnet:?xt=urn:btih:..."
          @keyup.meta.enter="submitMagnetEditor"
          @keyup.ctrl.enter="submitMagnetEditor"
        ></textarea>
        <div class="inline-dialog-actions">
          <button class="btn btn-ghost" type="button" @click="closeMagnetEditor">取消</button>
          <button
            class="btn btn-primary"
            type="button"
            :disabled="!magnetEditor.value.trim() || isCandidateMutating(magnetEditor.candidate?.id)"
            @click="submitMagnetEditor"
          >
            {{ isCandidateMutating(magnetEditor.candidate?.id) ? '保存中...' : '保存磁力' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="candidateDetail.open" class="inline-dialog-overlay" @click.self="closeCandidateDetail">
      <div class="inline-dialog candidate-detail-dialog">
        <div class="inline-dialog-header">
          <div>
            <h2>{{ candidateDetail.data?.dvd_id || candidateDetail.data?.content_id || '候选详情' }}</h2>
            <p>{{ candidateDetail.data?.title || candidateDetail.data?.actress_name || '' }}</p>
          </div>
          <button class="dialog-close-btn" type="button" @click="closeCandidateDetail">×</button>
        </div>
        <div v-if="candidateDetail.loading" class="candidate-detail-loading">加载中...</div>
        <template v-else-if="candidateDetail.data">
          <div class="candidate-detail-grid">
            <div><span>状态</span><strong>{{ candidateStatusLabel(candidateDetail.data.status) }}</strong></div>
            <div><span>来源</span><strong>{{ candidateSourceLabel(candidateDetail.data.source) }}</strong></div>
            <div><span>磁力</span><strong>{{ candidateDetail.data.magnet ? '已有' : '待补' }}</strong></div>
            <div><span>下载任务</span><strong>{{ candidateDetail.data.download_task_id || '未下发' }}</strong></div>
          </div>
          <div v-if="candidateDetail.data.error_msg" class="candidate-detail-error">{{ candidateDetail.data.error_msg }}</div>
          <div v-if="candidateDetail.data.magnet" class="candidate-detail-magnet">{{ candidateDetail.data.magnet }}</div>
          <div class="event-timeline">
            <div v-for="event in candidateDetail.data.events || []" :key="event.id" class="event-row">
              <span class="event-dot"></span>
              <div>
                <strong>{{ eventActionLabel(event.action) }}</strong>
                <p>{{ event.detail || '无详情' }}</p>
                <small>{{ event.operator || 'system' }} · {{ formatTime(event.created_at) }}</small>
              </div>
            </div>
            <small v-if="!(candidateDetail.data.events || []).length">暂无事件记录</small>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<script>
import api from '../api'
import { requestConfirm } from '../utils/confirmDialog'
import CandidateRunPanel from '../features/candidates/CandidateRunPanel.vue'

export default {
  name: 'Home',
  components: { CandidateRunPanel },
  data() {
    return {
      activeTab: ['candidates', 'downloaders'].includes(this.$route.query.tab) ? this.$route.query.tab : 'tasks',
      tasks: [],
      candidates: [],
      downloaders: { default_id: '', clients: [], types: [] },
      downloaderTypes: [
        { value: 'openlist', label: 'OpenList / 115' },
        { value: 'qbittorrent', label: 'qBittorrent' },
        { value: 'transmission', label: 'Transmission' },
        { value: 'synology', label: 'Synology Download Station' },
        { value: 'aria2', label: 'Aria2' },
        { value: 'deluge', label: 'Deluge' },
        { value: 'flood', label: 'Flood' },
        { value: 'rutorrent', label: 'ruTorrent' },
        { value: 'utorrent', label: 'µTorrent / uTorrent' },
      ],
      savingDownloaders: false,
      testingDownloaderId: '',
      downloaderTestMessages: {},
      stats: { pending: 0, downloading: 0, completed: 0, failed: 0 },
      candidateStats: {
        candidate: 0,
        approved: 0,
        rejected: 0,
        sent: 0,
        failed: 0,
        needs_magnet: 0,
        by_source: {},
        candidate_by_source: {},
      },
      filterStatus: null,
      candidateFilter: {
        status: this.$route.query.status || 'candidate',
        source: this.$route.query.source || '',
        actress_id: this.$route.query.actress_id || '',
        q: this.$route.query.q || '',
        needs_magnet: this.$route.query.needs_magnet === '1' ? true : (this.$route.query.needs_magnet === '0' ? false : null)
      },
      timer: null,
      selectingCandidates: false,
      selectedCandidateIds: [],
      bulkCandidateLoading: false,
      candidateBatchProcessing: '',
      candidateRuns: [],
      candidateRunsLoading: false,
      candidateMutations: {},
      retryingTasks: {},
      statsLoaded: false,
      magnetEditor: {
        open: false,
        candidate: null,
        value: ''
      },
      candidateDetail: {
        open: false,
        loading: false,
        data: null
      },
      downloaderEditor: {
        open: false,
        mode: 'new',
        originalId: '',
        draft: null,
        previousType: ''
      },
      downloaderIdSeed: 1
    }
  },
  computed: {
    filteredTasks() {
      if (!this.filterStatus) return this.tasks
      return this.tasks.filter(t => t.status === this.filterStatus)
    },
    filteredCandidates() {
      return this.candidates
    },
    readyCandidateCount() {
      return Math.max((this.candidateStats.candidate || 0) - (this.candidateStats.needs_magnet || 0), 0)
    },
    downloaderClients() {
      return this.downloaders.clients || []
    },
    enabledDownloaderCount() {
      return this.downloaderClients.filter(client => client.enabled).length
    },
    defaultDownloaderLabel() {
      const client = this.downloaderClients.find(item => item.id === this.downloaders.default_id)
      return client?.name || this.downloaderTypeLabel(client?.type) || '未设置'
    }
  },
  mounted() {
    this.loadTasks()
    this.loadCandidates()
    if (this.activeTab === 'candidates') this.loadCandidateRuns()
    if (this.activeTab === 'downloaders') this.loadDownloaders()
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
        this.statsLoaded = true
      } catch (e) {
        console.error('Failed to load tasks:', e)
      }
    },
    async loadCandidates() {
      try {
        const params = {}
        if (this.candidateFilter.status) params.status = this.candidateFilter.status
        if (this.candidateFilter.source) params.source = this.candidateFilter.source
        if (this.candidateFilter.actress_id) params.actress_id = this.candidateFilter.actress_id
        if (this.candidateFilter.q) params.q = this.candidateFilter.q
        if (this.candidateFilter.needs_magnet !== null) params.needs_magnet = this.candidateFilter.needs_magnet
        const resp = await api.listDownloadCandidates(params)
        this.candidates = resp.data.data || []
        this.candidateStats = resp.data.stats || this.candidateStats
        this.selectedCandidateIds = this.selectedCandidateIds.filter(id => this.candidates.some(c => c.id === id))
        this.syncCandidateRoute()
      } catch (e) {
        console.error('Failed to load candidates:', e)
      }
    },
    async loadCandidateRuns() {
      this.candidateRunsLoading = true
      try {
        const resp = await api.listDownloadCandidateRuns(5)
        this.candidateRuns = resp.data.data || []
      } catch (e) {
        console.error('Failed to load candidate runs:', e)
      } finally {
        this.candidateRunsLoading = false
      }
    },
    openCandidateTab() {
      this.activeTab = 'candidates'
      this.loadCandidates()
      this.loadCandidateRuns()
    },
    openDownloaderTab() {
      this.activeTab = 'downloaders'
      this.loadDownloaders()
      if (this.$route.query.tab !== 'downloaders') {
        this.$router.replace({ query: { tab: 'downloaders' } }).catch(() => {})
      }
    },
    async loadDownloaders() {
      try {
        const resp = await api.listDownloaders()
        const data = resp.data || {}
        this.downloaders = {
          default_id: data.default_id || '',
          clients: (data.clients || []).map(client => ({ ...client })),
          types: data.types || this.downloaderTypes,
        }
        this.downloaderTypes = this.downloaders.types.length ? this.downloaders.types : this.downloaderTypes
        if (!this.downloaders.default_id && this.downloaders.clients[0]) {
          this.downloaders.default_id = this.downloaders.clients[0].id
        }
      } catch (e) {
        console.error('Failed to load downloaders:', e)
      }
    },
    makeDownloaderId(type = 'qbittorrent') {
      let id = `${type}-${this.downloaderIdSeed++}`
      while (this.downloaderClients.some(client => client.id === id)) {
        id = `${type}-${this.downloaderIdSeed++}`
      }
      return id
    },
    createDownloaderDraft(type = 'qbittorrent') {
      return {
        id: this.makeDownloaderId(type),
        type,
        name: this.downloaderTypeLabel(type),
        enabled: true,
        address: this.downloaderAddressPlaceholder(type),
        username: '',
        password: '',
        token: '',
        default_path: '',
        category: '',
        tags: '',
        paused: false,
        timeout: 30,
      }
    },
    normalizeDownloaderDraft(draft) {
      return {
        id: draft.id,
        type: draft.type || 'qbittorrent',
        name: draft.name || this.downloaderTypeLabel(draft.type),
        enabled: Boolean(draft.enabled),
        address: draft.address || '',
        username: draft.username || '',
        password: draft.password || '',
        token: draft.token || '',
        default_path: draft.default_path || '',
        category: draft.category || '',
        tags: draft.tags || '',
        paused: Boolean(draft.paused),
        timeout: Number(draft.timeout || 30),
        password_configured: Boolean(draft.password_configured),
        token_configured: Boolean(draft.token_configured),
      }
    },
    openNewDownloader() {
      this.downloaderEditor = {
        open: true,
        mode: 'new',
        originalId: '',
        draft: this.createDownloaderDraft('qbittorrent'),
        previousType: 'qbittorrent'
      }
    },
    editDownloader(client) {
      this.downloaderEditor = {
        open: true,
        mode: 'edit',
        originalId: client.id,
        draft: this.normalizeDownloaderDraft({ ...client }),
        previousType: client.type
      }
    },
    closeDownloaderEditor() {
      this.downloaderEditor = { open: false, mode: 'new', originalId: '', draft: null, previousType: '' }
    },
    applyDownloaderEditor() {
      const draft = this.downloaderEditor.draft
      if (!draft) return
      const client = this.normalizeDownloaderDraft(draft)
      if (this.downloaderEditor.mode === 'new') {
        this.downloaders.clients = [...this.downloaderClients, client]
        if (!this.downloaders.default_id) this.downloaders.default_id = client.id
      } else {
        this.downloaders.clients = this.downloaderClients.map(item => (
          item.id === this.downloaderEditor.originalId ? client : item
        ))
        if (this.downloaders.default_id === this.downloaderEditor.originalId) {
          this.downloaders.default_id = client.id
        }
      }
      this.closeDownloaderEditor()
    },
    syncDownloaderDraftDefaults() {
      const draft = this.downloaderEditor.draft
      if (!draft) return
      const previousType = this.downloaderEditor.previousType
      const previousPlaceholder = this.downloaderAddressPlaceholder(previousType)
      if (!draft.name || this.downloaderTypes.some(type => type.label === draft.name)) {
        draft.name = this.downloaderTypeLabel(draft.type)
      }
      if (!draft.address || draft.address === previousPlaceholder) {
        draft.address = this.downloaderAddressPlaceholder(draft.type)
      }
      this.downloaderEditor.previousType = draft.type
    },
    removeDownloader(id) {
      this.downloaders.clients = this.downloaderClients.filter(client => client.id !== id)
      if (this.downloaders.default_id === id) {
        this.downloaders.default_id = this.downloaderClients[0]?.id || ''
      }
    },
    setDefaultDownloader(id) {
      this.downloaders.default_id = id
    },
    downloaderTypeLabel(type) {
      return this.downloaderTypes.find(item => item.value === type)?.label || type || '下载器'
    },
    downloaderTypeMark(type) {
      const map = {
        openlist: '115',
        qbittorrent: 'QB',
        transmission: 'TR',
        synology: 'SY',
        aria2: 'A2',
        deluge: 'DE',
        flood: 'FL',
        rutorrent: 'RU',
        utorrent: 'µT',
      }
      return map[type] || String(type || 'DL').slice(0, 2).toUpperCase()
    },
    downloaderAddressPlaceholder(type) {
      const map = {
        openlist: 'https://fox.oplist.org',
        qbittorrent: 'http://localhost:8080',
        transmission: 'http://localhost:9091',
        synology: 'http://nas:5000',
        aria2: 'http://localhost:6800',
        deluge: 'http://localhost:8112',
        flood: 'http://localhost:3000',
        rutorrent: 'https://myrut.com/rutorrent',
        utorrent: 'http://127.0.0.1:8080/gui/',
      }
      return map[type] || 'http://localhost'
    },
    downloaderPathPlaceholder(type) {
      if (type === 'synology') return 'video/downloads'
      if (type === 'qbittorrent') return '/downloads 或 category:Movies'
      if (type === 'openlist') return '/115/AV'
      if (type === 'utorrent') return 'movie\\ 或留空'
      return '/downloads'
    },
    supportsDownloaderTags(type) {
      return ['qbittorrent', 'transmission', 'deluge', 'flood', 'rutorrent', 'utorrent'].includes(type)
    },
    shortDownloaderAddress(address) {
      const value = String(address || '').trim()
      if (!value) return ''
      try {
        const url = new URL(value)
        return `${url.host}${url.pathname === '/' ? '' : url.pathname}`.replace(/\/$/, '')
      } catch (_) {
        return value.replace(/^https?:\/\//, '').replace(/\/$/, '')
      }
    },
    downloaderPathSummary(client) {
      if (client.default_path) return client.default_path
      if (client.category) return `分类 ${client.category}`
      return '默认路径'
    },
    tokenPlaceholder(type) {
      return type === 'aria2' ? 'rpc-secret，可选' : '可选'
    },
    normalizedDownloaderPayload() {
      return {
        default_id: this.downloaders.default_id,
        clients: this.downloaderClients.map(client => ({
          id: client.id,
          type: client.type,
          name: client.name,
          enabled: Boolean(client.enabled),
          address: client.address || '',
          username: client.username || '',
          password: client.password || '',
          token: client.token || '',
          default_path: client.default_path || '',
          category: client.category || '',
          tags: client.tags || '',
          paused: Boolean(client.paused),
          timeout: Number(client.timeout || 30),
        }))
      }
    },
    async saveDownloaders() {
      if (this.savingDownloaders) return
      this.savingDownloaders = true
      try {
        const resp = await api.updateDownloaders(this.normalizedDownloaderPayload())
        this.downloaders = {
          default_id: resp.data.default_id || '',
          clients: (resp.data.clients || []).map(client => ({ ...client })),
          types: resp.data.types || this.downloaderTypes,
        }
        this.$message?.success?.('下载源已保存')
      } catch (e) {
        console.error('Save downloaders failed:', e)
      } finally {
        this.savingDownloaders = false
      }
    },
    async testDownloader(client) {
      if (this.testingDownloaderId) return
      this.testingDownloaderId = client.id
      try {
        const resp = await api.testDownloader(client)
        this.downloaderTestMessages = {
          ...this.downloaderTestMessages,
          [client.id]: { ok: Boolean(resp.data.ok), message: resp.data.ok ? `连接正常：${resp.data.message || 'OK'}` : `连接失败：${resp.data.message || '未知错误'}` }
        }
      } catch (e) {
        this.downloaderTestMessages = {
          ...this.downloaderTestMessages,
          [client.id]: { ok: false, message: `连接失败：${e.response?.data?.detail || e.message}` }
        }
      } finally {
        this.testingDownloaderId = ''
      }
    },
    syncCandidateRoute() {
      if (this.activeTab !== 'candidates') return
      const query = { tab: 'candidates' }
      if (this.candidateFilter.status) query.status = this.candidateFilter.status
      if (this.candidateFilter.source) query.source = this.candidateFilter.source
      if (this.candidateFilter.actress_id) query.actress_id = this.candidateFilter.actress_id
      if (this.candidateFilter.q) query.q = this.candidateFilter.q
      if (this.candidateFilter.needs_magnet === true) query.needs_magnet = '1'
      if (this.candidateFilter.needs_magnet === false) query.needs_magnet = '0'
      if (JSON.stringify(query) !== JSON.stringify(this.$route.query)) {
        this.$router.replace({ query }).catch(() => {})
      }
    },
    setCandidateStatus(status) {
      this.candidateFilter.status = status
      this.candidateFilter.needs_magnet = null
      this.loadCandidates()
    },
    setNeedsMagnet(needs) {
      this.candidateFilter.status = 'candidate'
      this.candidateFilter.needs_magnet = needs
      this.loadCandidates()
    },
    setCandidateSource(source) {
      this.candidateFilter.source = source
      this.loadCandidates()
    },
    openCandidatePreset({ status = 'candidate', source = '', needs_magnet = null } = {}) {
      this.activeTab = 'candidates'
      this.candidateFilter.status = status
      this.candidateFilter.source = source
      this.candidateFilter.needs_magnet = needs_magnet
      this.loadCandidates()
      this.loadCandidateRuns()
    },
    applyCandidateRunFilters(run, overrides = {}) {
      const filters = { ...(run.filters || {}), ...overrides }
      this.activeTab = 'candidates'
      this.candidateFilter.status = filters.status || 'candidate'
      this.candidateFilter.source = filters.source || ''
      this.candidateFilter.actress_id = filters.actress_id || ''
      this.candidateFilter.q = filters.q || ''
      this.candidateFilter.needs_magnet = filters.needs_magnet === undefined ? null : filters.needs_magnet
      this.loadCandidates()
    },
    toggleCandidateSelection() {
      this.selectingCandidates = !this.selectingCandidates
      if (!this.selectingCandidates) this.selectedCandidateIds = []
    },
    toggleCandidateSelected(id) {
      if (this.selectedCandidateIds.includes(id)) {
        this.selectedCandidateIds = this.selectedCandidateIds.filter(item => item !== id)
      } else {
        this.selectedCandidateIds = [...this.selectedCandidateIds, id]
      }
    },
    selectAllVisibleCandidates() {
      this.selectedCandidateIds = [...new Set([...this.selectedCandidateIds, ...this.candidates.map(c => c.id)])]
    },
    clearCandidateSelection() {
      this.selectedCandidateIds = []
    },
    isCandidateMutating(id) {
      return Boolean(this.candidateMutations[id]) || this.bulkCandidateLoading || Boolean(this.candidateBatchProcessing)
    },
    setCandidateMutation(id, action) {
      this.candidateMutations = { ...this.candidateMutations, [id]: action }
    },
    clearCandidateMutation(id) {
      const next = { ...this.candidateMutations }
      delete next[id]
      this.candidateMutations = next
    },
    setTaskRetrying(id, loading) {
      if (loading) {
        this.retryingTasks = { ...this.retryingTasks, [id]: true }
        return
      }
      const next = { ...this.retryingTasks }
      delete next[id]
      this.retryingTasks = next
    },
    async bulkRejectCandidates() {
      if (this.selectedCandidateIds.length === 0 || this.bulkCandidateLoading) return
      const confirmed = await requestConfirm({
        title: '批量拒绝候选',
        message: `确认拒绝 ${this.selectedCandidateIds.length} 个下载候选？`,
        details: '拒绝后可在已拒绝筛选中批量恢复。',
        confirmText: '拒绝',
        tone: 'danger'
      })
      if (!confirmed) return
      this.bulkCandidateLoading = true
      try {
        await api.bulkRejectDownloadCandidates(this.selectedCandidateIds)
        this.selectedCandidateIds = []
        await this.loadCandidates()
      } catch (e) {
        console.error('Bulk reject candidates failed:', e)
      } finally {
        this.bulkCandidateLoading = false
      }
    },
    async bulkRestoreCandidates() {
      if (this.selectedCandidateIds.length === 0 || this.bulkCandidateLoading) return
      this.bulkCandidateLoading = true
      try {
        await api.bulkRestoreDownloadCandidates(this.selectedCandidateIds)
        this.selectedCandidateIds = []
        await this.loadCandidates()
      } catch (e) {
        console.error('Bulk restore candidates failed:', e)
      } finally {
        this.bulkCandidateLoading = false
      }
    },
    async editCandidateMagnet(candidate) {
      if (this.isCandidateMutating(candidate.id)) return
      this.magnetEditor = {
        open: true,
        candidate,
        value: candidate.magnet || ''
      }
    },
    closeMagnetEditor() {
      if (this.magnetEditor.candidate && this.isCandidateMutating(this.magnetEditor.candidate.id)) return
      this.magnetEditor = { open: false, candidate: null, value: '' }
    },
    async submitMagnetEditor() {
      const candidate = this.magnetEditor.candidate
      const magnet = this.magnetEditor.value.trim()
      if (!candidate || !magnet || this.isCandidateMutating(candidate.id)) return
      this.setCandidateMutation(candidate.id, 'magnet')
      try {
        await api.updateDownloadCandidateMagnet(candidate.id, magnet)
        this.closeMagnetEditor()
        await this.loadCandidates()
      } catch (e) {
        console.error('Update candidate magnet failed:', e)
      } finally {
        this.clearCandidateMutation(candidate.id)
      }
    },
    candidateFilterPayload(overrides = {}) {
      const payload = {
        status: this.candidateFilter.status || 'candidate',
        source: this.candidateFilter.source || undefined,
        actress_id: this.candidateFilter.actress_id ? Number(this.candidateFilter.actress_id) : undefined,
        q: this.candidateFilter.q || undefined,
        needs_magnet: this.candidateFilter.needs_magnet,
        limit: this.candidates.length || 50,
        ...overrides,
      }
      Object.keys(payload).forEach((key) => {
        if (payload[key] === undefined || payload[key] === '') delete payload[key]
      })
      return payload
    },
    async enrichCandidateMagnet(candidate) {
      if (this.isCandidateMutating(candidate.id)) return
      this.setCandidateMutation(candidate.id, 'enrich')
      try {
        const resp = await api.enrichDownloadCandidateMagnet(candidate.id)
        const action = resp.data?.action
        if (action === 'magnet_enriched') this.$message?.success?.('已补充 magnet')
        else if (action === 'magnet_not_found') this.$message?.warning?.('未找到可用 magnet')
        else if (action === 'already_has_magnet') this.$message?.info?.('候选已有 magnet')
        await this.loadCandidates()
      } catch (e) {
        console.error('Enrich candidate magnet failed:', e)
      } finally {
        this.clearCandidateMutation(candidate.id)
      }
    },
    async processCandidate(candidate) {
      if (this.isCandidateMutating(candidate.id)) return
      this.setCandidateMutation(candidate.id, 'process')
      try {
        const resp = await api.processDownloadCandidate(candidate.id, { enrich: true })
        const action = resp.data?.action
        if (action === 'sent') this.$message?.success?.('候选已下发下载')
        else if (action === 'manual_required') this.$message?.info?.('当前为人工批准策略')
        else if (action?.startsWith('skipped')) this.$message?.info?.('候选未满足策略条件')
        else if (action?.startsWith('failed')) this.$message?.error?.('候选处理失败')
        await this.loadCandidates()
        await this.loadTasks()
      } catch (e) {
        console.error('Process candidate failed:', e)
      } finally {
        this.clearCandidateMutation(candidate.id)
      }
    },
    async enrichVisibleCandidateMagnets() {
      if (this.candidateBatchProcessing) return
      this.candidateBatchProcessing = 'enrich'
      try {
        const targets = this.candidates.filter(candidate => (
          (candidate.status === 'candidate' || candidate.status === 'failed') && !candidate.magnet
        ))
        let enriched = 0
        for (const candidate of targets) {
          const resp = await api.enrichDownloadCandidateMagnet(candidate.id)
          if (resp.data?.action === 'magnet_enriched') enriched += 1
        }
        this.$message?.success?.(`已检查 ${targets.length} 个，补磁力 ${enriched} 个`)
        await this.loadCandidates()
      } catch (e) {
        console.error('Batch enrich candidates failed:', e)
      } finally {
        this.candidateBatchProcessing = ''
      }
    },
    async processVisibleCandidates() {
      if (this.candidateBatchProcessing) return
      this.candidateBatchProcessing = 'dry-run'
      let preview
      try {
        const resp = await api.processDownloadCandidates(this.candidateFilterPayload({ enrich: true, dry_run: true }))
        preview = resp.data || {}
      } catch (e) {
        console.error('Preview candidate processing failed:', e)
        this.candidateBatchProcessing = ''
        return
      }
      const previewCounts = preview.counts || {}
      const confirmed = await requestConfirm({
        title: '按策略处理候选',
        message: this.processPreviewMessage(preview),
        details: this.processPreviewDetails(previewCounts, preview.limits || {}),
        confirmText: '处理',
      })
      if (!confirmed) return
      this.candidateBatchProcessing = 'process'
      try {
        const resp = await api.processDownloadCandidates(this.candidateFilterPayload({ enrich: true }))
        const counts = resp.data?.counts || {}
        const skipped = (counts.manual_required || 0) + (counts.skipped_source || 0) + (counts.skipped_missing_magnet || 0) + (counts.skipped_status || 0)
        this.$message?.success?.(`处理 ${resp.data?.total || 0} 个：下发 ${counts.sent || 0}，跳过 ${skipped}`)
        await this.loadCandidates()
        await this.loadCandidateRuns()
        await this.loadTasks()
      } catch (e) {
        console.error('Batch process candidates failed:', e)
      } finally {
        this.candidateBatchProcessing = ''
      }
    },
    processPreviewMessage(preview = {}) {
      const counts = preview.counts || {}
      const wouldSend = counts.would_send || 0
      const wouldEnrich = counts.would_enrich_magnet || 0
      const skippedLimit = counts.would_skip_limit || 0
      return `预演 ${preview.total || 0} 个：可直接下发 ${wouldSend}，需补磁力 ${wouldEnrich}，受上限跳过 ${skippedLimit}。`
    },
    processPreviewDetails(counts = {}, limits = {}) {
      const skipped = Object.entries(counts)
        .filter(([action]) => action.startsWith('skipped') || action === 'manual_required')
        .reduce((sum, [, value]) => sum + Number(value || 0), 0)
      const remaining = limits.remaining === null || limits.remaining === undefined ? '不限' : limits.remaining
      const perRun = limits.per_run || 0
      const per24h = limits.per_24h || 0
      return `策略跳过 ${skipped}。单次上限 ${perRun || '不限'}，24 小时上限 ${per24h || '不限'}，当前剩余额度 ${remaining}。`
    },
    async retryFailedCandidateRun(run) {
      if (!run?.id || this.candidateBatchProcessing) return
      const confirmed = await requestConfirm({
        title: '重试失败候选',
        message: `确认重试本次处理中的 ${run.failed || 0} 个失败候选？`,
        details: '会复用当时策略并重新补磁力/下发，仍失败的候选会留在失败队列。',
        confirmText: '重试',
      })
      if (!confirmed) return
      this.candidateBatchProcessing = 'retry-run'
      try {
        const resp = await api.retryDownloadCandidateRunFailed(run.id, { enrich: true })
        const counts = resp.data?.counts || {}
        this.$message?.success?.(`已重试 ${resp.data?.total || 0} 个：下发 ${counts.sent || 0}，失败 ${counts.failed_downloader || 0}`)
        await this.loadCandidates()
        await this.loadCandidateRuns()
        await this.loadTasks()
      } catch (e) {
        console.error('Retry failed candidate run failed:', e)
      } finally {
        this.candidateBatchProcessing = ''
      }
    },
    async openCandidateDetail(candidate) {
      this.candidateDetail = { open: true, loading: true, data: candidate }
      try {
        const resp = await api.getDownloadCandidate(candidate.id)
        this.candidateDetail = { open: true, loading: false, data: resp.data.data }
      } catch (e) {
        console.error('Load candidate detail failed:', e)
        this.candidateDetail = { open: true, loading: false, data: candidate }
      }
    },
    closeCandidateDetail() {
      this.candidateDetail = { open: false, loading: false, data: null }
    },
    eventActionLabel(action) {
      const map = {
        upsert: '写入候选',
        magnet_updated: '手动更新磁力',
        magnet_enriched: '自动补充磁力',
        magnet_enrich_failed: '磁力补充失败',
        magnet_enrich_skipped: '跳过补磁力',
        policy_skipped: '策略跳过',
        auto_approved: '自动下发',
        approved: '人工批准',
        approve_failed: '批准失败',
        process_failed: '处理失败',
        rejected: '拒绝候选',
        bulk_rejected: '批量拒绝',
        bulk_restored: '批量恢复',
      }
      return map[action] || action
    },
    candidateRunPolicyLabel(policy) {
      const map = { manual: '人工批准', rules: '规则自动', auto: '全自动' }
      return map[policy] || '人工批准'
    },
    candidateRunTriggerLabel(trigger) {
      const map = { manual: '人工触发', system: '系统触发' }
      return map[trigger] || trigger || '未知触发'
    },
    async approveCandidate(candidate) {
      if (this.isCandidateMutating(candidate.id)) return
      this.setCandidateMutation(candidate.id, 'approve')
      try {
        await api.approveDownloadCandidate(candidate.id)
        await this.loadCandidates()
        await this.loadTasks()
      } catch (e) {
        console.error('Approve candidate failed:', e)
      } finally {
        this.clearCandidateMutation(candidate.id)
      }
    },
    async rejectCandidate(candidate) {
      if (this.isCandidateMutating(candidate.id)) return
      const confirmed = await requestConfirm({
        title: '拒绝下载候选',
        message: `确认拒绝 ${candidate.dvd_id || candidate.content_id}？`,
        details: candidate.title || '',
        confirmText: '拒绝',
        tone: 'danger'
      })
      if (!confirmed) return
      this.setCandidateMutation(candidate.id, 'reject')
      try {
        await api.rejectDownloadCandidate(candidate.id)
        await this.loadCandidates()
      } catch (e) {
        console.error('Reject candidate failed:', e)
      } finally {
        this.clearCandidateMutation(candidate.id)
      }
    },
    goCandidateActor(candidate) {
      if (!candidate.actress_id) return
      const name = candidate.actress_name || candidate.actress_id
      this.$router.push({
        path: `/actor/${encodeURIComponent(name)}`,
        query: { name, actress_id: candidate.actress_id },
      })
    },
    goCandidateSupplement(candidate) {
      if (!candidate.actress_id) return
      this.$router.push({
        path: '/supplement',
        query: { tab: 'movies', actress_id: candidate.actress_id, q: candidate.dvd_id || candidate.content_id || '' },
      })
    },
    async remove(id) {
      try {
        await api.deleteDownload(id)
        this.loadTasks()
      } catch (e) {
        console.error('Failed to delete:', e)
      }
    },
    async retry(task) {
      if (this.retryingTasks[task.id]) return
      this.setTaskRetrying(task.id, true)
      try {
        await api.createDownload({
          content_id: task.content_id || task.code,
          title: task.title,
          magnet: task.magnet,
          path: task.path,
          downloader_id: task.downloader_id || ''
        })
        await this.loadTasks()
      } catch (e) {
        console.error('Failed to retry download:', e)
      } finally {
        this.setTaskRetrying(task.id, false)
      }
    },
    statusBadge(status) {
      const map = { pending: 'badge-pending', downloading: 'badge-info', completed: 'badge-success', failed: 'badge-error' }
      return map[status] || 'badge-pending'
    },
    statusLabel(status) {
      const map = { pending: '待处理', downloading: '下载中', completed: '已完成', failed: '失败' }
      return map[status] || status
    },
    candidateBadge(status) {
      const map = { candidate: 'badge-pending', approved: 'badge-info', sent: 'badge-success', failed: 'badge-error', rejected: 'badge-pending' }
      return map[status] || 'badge-pending'
    },
    candidateStatusLabel(status) {
      const map = { candidate: '待确认', approved: '已批准', sent: '已下发', failed: '失败', rejected: '已拒绝' }
      return map[status] || status
    },
    candidateSourceLabel(source) {
      const map = { subscription: '订阅', inventory: '库存', supplement: '补全', manual: '手动' }
      return map[source] || source || '未知来源'
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
.home {}

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
.page-header h1 { font-size: var(--type-workbench-title); font-weight: 700; color: var(--text-primary); letter-spacing: 0; }
.header-subtitle { font-size: var(--type-control); color: var(--text-muted); }
.downloading-hint { color: var(--text-secondary); }
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
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid var(--border);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05); /* Top highlight */
  border-radius: var(--radius-lg);
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  animation: statEntrance 0.5s cubic-bezier(0.32, 0.72, 0, 1) both;
}
.stat-card:nth-child(1) { animation-delay: 0.05s; }
.stat-card:nth-child(2) { animation-delay: 0.1s; }
.stat-card:nth-child(3) { animation-delay: 0.15s; }
.stat-card:nth-child(4) { animation-delay: 0.2s; }
@keyframes statEntrance {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
.stat-card:hover {
  transform: translateY(-4px) !important;
  border-color: var(--border-light);
}

.stat-icon {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  background: rgba(255, 255, 255, 0.05) !important;
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: var(--text-secondary) !important;
}
.stat-icon svg { width: 24px; height: 24px; }

.stat-info { min-width: 0; }
.stat-num {
  font-family: var(--font-mono);
  font-size: var(--type-entity-title);
  letter-spacing: -0.04em;
  font-weight: 600;
  color: var(--text-primary);
  line-height: 1;
  animation: statPop 0.5s cubic-bezier(0.32, 0.72, 0, 1) both;
}
.stat-num.animate-in { animation: statPop 0.5s cubic-bezier(0.32, 0.72, 0, 1) both; }
@keyframes statPop {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}
.stat-card:nth-child(1) .stat-num { animation-delay: 0.05s; }
.stat-card:nth-child(2) .stat-num { animation-delay: 0.1s; }
.stat-card:nth-child(3) .stat-num { animation-delay: 0.15s; }
.stat-card:nth-child(4) .stat-num { animation-delay: 0.2s; }
.stat-label { font-size: 13px; color: var(--text-secondary); margin-top: 4px; }

.candidate-overview {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
  margin: -8px 0 18px;
}
.candidate-metric {
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 12px 14px;
  background: var(--bg-card);
  color: var(--text-primary);
  text-align: left;
  cursor: pointer;
}
.candidate-metric:hover {
  border-color: var(--border-light);
  background: var(--surface-control-hover);
}
.metric-value {
  display: block;
  font-family: var(--font-mono);
  font-size: var(--type-section-title);
  font-weight: 700;
}
.metric-label {
  display: block;
  margin-top: 3px;
  color: var(--text-secondary);
  font-size: 12px;
}

/* ===== Filter Bar ===== */
.filter-bar {
  background: var(--surface-control);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  padding: 10px 16px;
  margin-bottom: 16px;
  cursor: pointer;
  transition: var(--transition);
}
.filter-bar:hover {
  background: var(--surface-control-hover);
  border-color: var(--border-light);
}
.filter-hint { font-size: 13px; color: var(--text-secondary); }
.filter-hint strong { color: var(--text-primary); }

.download-tabs {
  display: inline-flex;
  gap: 4px;
  padding: 4px;
  margin-bottom: 16px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--bg-card);
}
.tab-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 0;
  border-radius: 8px;
  padding: 8px 14px;
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
}
.tab-btn.active {
  color: var(--text-primary);
  background: rgba(255, 255, 255, 0.08);
}
.tab-badge {
  min-width: 18px;
  padding: 1px 6px;
  border-radius: 999px;
  background: #ff375f;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
}
.tab-badge.subtle {
  background: rgba(82, 196, 26, 0.18);
  color: #52c41a;
}
.candidate-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}
.candidate-search-input {
  min-width: min(260px, 100%);
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 6px 12px;
  background: var(--bg-card);
  color: var(--text-primary);
  font-size: 13px;
}
.candidate-search-input:focus {
  outline: none;
  border-color: var(--accent);
}
.bulk-toolbar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--bg-card);
  color: var(--text-secondary);
  font-size: 12px;
}
.bulk-toolbar .btn { font-size: 12px; padding: 5px 10px; }
.link-btn.danger {
  color: #ef5350;
}
.chip {
  border: 1px solid var(--border);
  border-radius: 999px;
  padding: 6px 12px;
  background: var(--bg-card);
  color: var(--text-secondary);
  cursor: pointer;
}
.chip.active {
  color: var(--text-primary);
  border-color: var(--active-border);
  background: var(--active-bg);
  box-shadow: inset 0 -2px 0 var(--active-indicator);
}
.chip:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}
.action-chip {
  border-color: rgba(82, 196, 26, 0.35);
  color: #52c41a;
}
.action-chip.primary {
  background: var(--accent);
  border-color: var(--accent);
  color: var(--text-on-accent);
}
.candidate-card .task-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.candidate-card { position: relative; }
.candidate-select {
  position: absolute;
  z-index: 3;
  top: 8px;
  left: 8px;
  width: 26px;
  height: 26px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.56);
  border: 1px solid rgba(255, 255, 255, 0.18);
}
.candidate-select input { width: 16px; height: 16px; accent-color: var(--accent); }
.candidate-subtitle,
.candidate-magnet,
.candidate-reason,
.candidate-task-link,
.candidate-event {
  margin-top: 6px;
  font-size: 11px;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.candidate-magnet.empty { color: #fa8c16; }
.candidate-reason { color: var(--text-secondary); }
.candidate-task-link { color: #52c41a; }
.candidate-event { color: var(--text-secondary); }
.task-downloader {
  margin-top: 6px;
  color: var(--text-muted);
  font-size: 11px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.candidate-context-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}
.link-btn {
  border: 0;
  padding: 0;
  background: transparent;
  color: var(--link-text);
  font-size: 12px;
  cursor: pointer;
  text-decoration: underline;
  text-decoration-color: var(--link-underline);
  text-underline-offset: 3px;
}
.link-btn:hover { text-decoration-color: var(--link-underline-hover); }

.downloaders-panel {
  display: grid;
  gap: 16px;
}
.downloader-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px;
}
.downloader-toolbar-copy strong {
  display: block;
  color: var(--text-primary);
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0;
}
.downloader-toolbar-copy span {
  display: block;
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 13px;
}
.downloader-toolbar-actions {
  display: flex;
  gap: 8px;
}
.icon-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border: 1px solid var(--border);
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.055);
  color: var(--text-primary);
  cursor: pointer;
  transition: transform var(--motion-fast), background var(--motion-fast), border-color var(--motion-fast), opacity var(--motion-fast);
}
.icon-action svg {
  width: 17px;
  height: 17px;
}
.icon-action:hover:not(:disabled) {
  transform: translateY(-1px);
  border-color: var(--border-light);
  background: rgba(255, 255, 255, 0.09);
}
.icon-action.primary {
  background: var(--accent);
  color: var(--text-on-accent);
  border-color: var(--accent);
}
.icon-action.compact {
  width: 38px;
  height: 38px;
  background: transparent;
}
.icon-action.danger {
  color: var(--badge-error-text);
}
.icon-action:disabled {
  opacity: 0.38;
  cursor: not-allowed;
}
.downloaders-list {
  display: grid;
  overflow: hidden;
}
.downloader-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto auto;
  align-items: center;
  gap: 14px;
  min-height: 86px;
  padding: 14px 16px;
  border: 0;
  border-bottom: 1px solid var(--border);
  background: transparent;
  cursor: pointer;
  transition: background var(--motion-fast), opacity var(--motion-fast);
}
.downloader-row:last-child {
  border-bottom: 0;
}
.downloader-row:hover,
.downloader-row:focus-visible {
  background: rgba(255, 255, 255, 0.045);
  outline: none;
}
.downloader-row.disabled {
  opacity: 0.68;
}
.downloader-row-main {
  display: flex;
  align-items: center;
  gap: 13px;
  min-width: 0;
}
.downloader-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 46px;
  height: 46px;
  flex: 0 0 auto;
  border-radius: 14px;
  border: 1px solid var(--border-light);
  background:
    radial-gradient(circle at 30% 20%, rgba(255,255,255,0.18), transparent 36%),
    rgba(255, 255, 255, 0.08);
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.01em;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.08);
}
.downloader-avatar.muted {
  color: var(--text-muted);
  background: rgba(255, 255, 255, 0.035);
}
.downloader-copy {
  min-width: 0;
}
.downloader-title-line {
  display: flex;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
}
.downloader-title-line strong {
  min-width: 0;
  color: var(--text-primary);
  font-size: 15px;
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.downloader-title-line span {
  flex: 0 0 auto;
  color: var(--text-muted);
  font-size: 12px;
}
.downloader-summary {
  display: flex;
  gap: 10px;
  margin-top: 6px;
  min-width: 0;
  color: var(--text-muted);
  font-size: 12px;
}
.downloader-summary span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.downloader-summary span + span::before {
  content: '';
  display: inline-block;
  width: 3px;
  height: 3px;
  margin: 0 9px 2px 0;
  border-radius: 50%;
  background: var(--text-muted);
}
.downloader-status-group {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
}
.downloader-pill {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 3px 9px;
  border: 1px solid var(--badge-pending-border);
  border-radius: 999px;
  background: var(--badge-pending-bg);
  color: var(--badge-pending-text);
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
}
.downloader-pill.default,
.downloader-pill.enabled,
.downloader-pill.test.ok {
  border-color: var(--badge-success-border);
  background: var(--badge-success-bg);
  color: var(--badge-success-text);
}
.downloader-pill.test {
  max-width: 88px;
  border-color: var(--badge-error-border);
  background: var(--badge-error-bg);
  color: var(--badge-error-text);
  overflow: hidden;
  text-overflow: ellipsis;
}
.downloaders-empty {
  display: grid;
  gap: 6px;
  padding: 34px 18px;
  text-align: center;
}
.downloaders-empty strong {
  color: var(--text-primary);
  font-size: 15px;
}
.downloaders-empty span {
  color: var(--text-muted);
  font-size: 13px;
}
.switch-mini {
  position: relative;
  width: 44px;
  height: 44px;
  flex: 0 0 auto;
}
.switch-mini input {
  position: absolute;
  opacity: 0;
}
.switch-mini span {
  position: absolute;
  inset: 9px 0;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.08);
  cursor: pointer;
}
.switch-mini span::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--text-secondary);
  transition: transform 160ms ease, background 160ms ease;
}
.switch-mini input:checked + span {
  border-color: var(--badge-success-border);
  background: var(--badge-success-bg);
}
.switch-mini input:checked + span::after {
  transform: translateX(20px);
  background: var(--badge-success-text);
}
.switch-apple {
  align-self: center;
}
.downloader-row-actions {
  display: flex;
  justify-content: flex-end;
  gap: 4px;
}
.downloaders-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 16px;
}
.downloaders-footer span {
  color: var(--text-muted);
  font-size: 12px;
}
.downloader-sheet {
  display: flex;
  flex-direction: column;
  width: min(720px, 100%);
  max-height: min(820px, calc(100vh - 48px));
}
.downloader-sheet-body {
  display: grid;
  gap: 14px;
  min-height: 0;
  overflow: auto;
  padding-right: 4px;
}
.downloader-sheet-section {
  display: grid;
  gap: 12px;
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.035);
}
.sheet-section-title strong {
  display: block;
  color: var(--text-primary);
  font-size: 14px;
}
.sheet-section-title span {
  display: block;
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 12px;
}
.downloader-sheet-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.downloader-sheet-grid label {
  display: grid;
  gap: 6px;
  color: var(--text-secondary);
  font-size: 12px;
}
.downloader-sheet-grid .wide-field {
  grid-column: 1 / -1;
}
.downloader-sheet-grid .input {
  width: 100%;
  min-height: 44px;
}
.downloader-sheet-options {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  color: var(--text-secondary);
  font-size: 12px;
}
.downloader-sheet-options label {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.spin-icon {
  animation: spin 0.9s linear infinite;
}
@keyframes spin {
  to { transform: rotate(360deg); }
}

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
.progress-bar-fill-demo { width: 60%; }
.empty-state-hint {
  margin-top: 6px;
  font-size: 13px;
}

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

.inline-dialog-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding: 20px;
  background: rgba(0, 0, 0, 0.58);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
}
.inline-dialog {
  width: min(560px, 100%);
  border: 1px solid var(--border-light);
  border-radius: 20px;
  background: var(--material-glass-sheet);
  box-shadow: var(--shadow-sheet);
  padding: 18px;
}
.inline-dialog-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}
.inline-dialog-header h2 {
  margin: 0;
  font-size: var(--type-panel-title);
  color: var(--text-primary);
  letter-spacing: 0;
}
.inline-dialog-header p {
  margin: 4px 0 0;
  color: var(--text-muted);
  font-size: 13px;
}
.dialog-close-btn {
  width: 44px;
  height: 44px;
  border: 1px solid var(--border);
  border-radius: 50%;
  background: var(--white-06);
  color: var(--text-primary);
  cursor: pointer;
  font-size: 24px;
}
.magnet-editor-input {
  width: 100%;
  min-height: 150px;
  resize: vertical;
  border: 1px solid var(--border);
  border-radius: 14px;
  padding: 12px;
  background: var(--bg-card);
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: 13px;
  outline: none;
}
.magnet-editor-input:focus {
  border-color: var(--accent);
}
.inline-dialog-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 14px;
}
.inline-dialog-actions .btn {
  min-height: 44px;
}
.candidate-detail-dialog {
  max-height: min(780px, 86vh);
  overflow: auto;
}
.candidate-detail-loading {
  padding: 28px;
  text-align: center;
  color: var(--text-secondary);
}
.candidate-detail-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}
.candidate-detail-grid > div {
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 10px;
  background: var(--bg-card);
}
.candidate-detail-grid span {
  display: block;
  color: var(--text-muted);
  font-size: 11px;
}
.candidate-detail-grid strong {
  display: block;
  margin-top: 4px;
  color: var(--text-primary);
  font-size: 13px;
}
.candidate-detail-error {
  margin-bottom: 12px;
  padding: 10px;
  border-radius: 10px;
  background: rgba(239, 83, 80, 0.1);
  color: #ef5350;
  font-size: 12px;
}
.candidate-detail-magnet {
  margin-bottom: 12px;
  padding: 10px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--bg-card);
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: 11px;
  overflow-wrap: anywhere;
}
.event-timeline {
  display: grid;
  gap: 10px;
}
.event-row {
  display: grid;
  grid-template-columns: 14px 1fr;
  gap: 10px;
}
.event-dot {
  width: 10px;
  height: 10px;
  margin-top: 4px;
  border-radius: 50%;
  background: var(--accent);
}
.event-row strong {
  color: var(--text-primary);
  font-size: 13px;
}
.event-row p {
  margin: 3px 0;
  color: var(--text-secondary);
  font-size: 12px;
}
.event-row small {
  color: var(--text-muted);
  font-size: 11px;
}

/* ===== Responsive ===== */
@media (max-width: 768px) {
  .stats-bar { grid-template-columns: repeat(2, 1fr); gap: 10px; }
  .stat-card { padding: 14px; gap: 12px; }
  .stat-num { font-size: var(--type-section-title); }
  .stat-icon { width: 40px; height: 40px; }
  .tasks-grid { grid-template-columns: repeat(auto-fill, minmax(160px, 1fr)); gap: 12px; }
  .header-actions .btn,
  .tab-btn,
  .chip,
  .task-actions .btn,
  .candidate-search-input,
  .bulk-toolbar .btn {
    min-height: 44px;
  }
  .candidate-toolbar {
    align-items: stretch;
  }
  .candidate-run-head,
  .candidate-run-row {
    align-items: flex-start;
    flex-direction: column;
  }
  .candidate-run-stats,
  .candidate-run-actions {
    justify-content: flex-start;
  }
  .candidate-search-input {
    width: 100%;
    flex: 1 0 100%;
  }
  .candidate-select {
    width: 44px;
    height: 44px;
  }
  .candidate-select input {
    width: 22px;
    height: 22px;
  }
  .inline-dialog-overlay {
    padding: 12px 12px calc(82px + env(safe-area-inset-bottom, 0px));
  }
  .inline-dialog {
    border-radius: 22px;
  }
  .inline-dialog-actions {
    flex-direction: column-reverse;
  }
  .inline-dialog-actions .btn {
    width: 100%;
    justify-content: center;
  }
  .candidate-detail-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  .downloader-toolbar,
  .downloaders-footer,
  .downloader-toolbar-actions {
    align-items: stretch;
    flex-direction: column;
  }
  .downloader-row {
    grid-template-columns: minmax(0, 1fr) auto;
    gap: 10px;
    min-height: 118px;
    align-items: start;
  }
  .downloader-row-main {
    grid-column: 1 / -1;
  }
  .downloader-status-group {
    justify-content: flex-start;
  }
  .switch-apple {
    grid-column: 2;
    grid-row: 2;
  }
  .downloader-row-actions {
    grid-column: 1 / -1;
    justify-content: flex-start;
    flex-wrap: wrap;
  }
  .downloaders-footer .btn {
    width: 100%;
  }
  .downloader-sheet {
    width: 100%;
    max-height: calc(100vh - 96px);
  }
  .downloader-sheet-grid {
    grid-template-columns: 1fr;
  }
  .downloader-sheet-grid .wide-field {
    grid-column: auto;
  }
}
</style>

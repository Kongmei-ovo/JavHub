<template>
  <div class="translation-page page-shell page-shell--workspace">
    <header class="translation-header">
      <div>
        <h1>翻译作业</h1>
      </div>
      <div class="header-actions">
        <button class="btn btn-ghost" type="button" :disabled="loading || statsLoading" @click="refreshOverview">
          {{ loading || statsLoading ? '刷新中...' : '刷新' }}
        </button>
        <button class="btn btn-primary" type="button" @click="setActiveSegment('create')">创建作业</button>
      </div>
    </header>

    <nav class="segmented-control apple-surface" aria-label="翻译作业视图">
      <button
        v-for="segment in segments"
        :key="segment.key"
        type="button"
        :class="{ active: activeSegment === segment.key }"
        @click="setActiveSegment(segment.key)"
      >{{ segment.label }}</button>
    </nav>

    <section v-if="activeSegment === 'overview'" class="workspace-panel apple-surface">
      <div class="panel-header">
        <div>
          <h2>总览</h2>
        </div>
      </div>

      <div class="overview-dashboard">
        <section class="coverage-hero" :class="{ loading: overviewLoading }" aria-label="标题覆盖">
          <template v-if="overviewLoading || overviewNeedsRefresh">
            <div class="coverage-donut skeleton-donut" aria-hidden="true"></div>
            <div class="coverage-hero-copy">
              <span class="overview-kicker">标题覆盖</span>
              <div class="coverage-placeholder-title">{{ overviewLoading ? '加载中' : '待刷新' }}</div>
              <p>{{ overviewLoading ? '正在计算覆盖率' : '未加载覆盖统计' }}</p>
              <div class="overview-track skeleton-track" aria-label="标题翻译覆盖率加载中">
                <div></div>
              </div>
            </div>
          </template>
          <template v-else>
            <div class="coverage-donut" :style="{ '--coverage-angle': `${percentValue(coverageTitle) * 3.6}deg` }">
              <div>
                <strong>{{ coveragePercent(coverageTitle) }}</strong>
                <span>标题覆盖</span>
              </div>
            </div>
            <div class="coverage-hero-copy">
              <span class="overview-kicker">标题覆盖</span>
              <div class="coverage-count">
                <strong>{{ formatNumber(coverageTitle.translated || 0) }}</strong>
                <span>/ {{ formatNumber(coverageTitle.total || 0) }}</span>
              </div>
              <p>剩余 {{ formatNumber(coverageTitle.untranslated || 0) }} 条标题需要翻译</p>
              <div class="overview-track" aria-label="标题翻译覆盖率">
                <div :style="{ width: `${percentValue(coverageTitle)}%` }"></div>
              </div>
            </div>
          </template>
        </section>

        <section class="metadata-overview" :class="{ loading: overviewLoading }" aria-label="元数据覆盖">
          <div class="overview-section-head">
            <div>
              <span class="overview-kicker">元数据覆盖</span>
              <strong>{{ overviewLoading ? '加载中' : (overviewNeedsRefresh ? '待刷新' : coveragePercent(metadataCoverage)) }}</strong>
            </div>
            <small>{{ overviewLoading ? '统计中' : (overviewNeedsRefresh ? '未加载' : `${formatNumber(metadataCoverage.untranslated || 0)} 未翻译`) }}</small>
          </div>
          <div class="coverage-row-list">
            <div v-for="row in coverageRows" :key="row.key" class="coverage-row" :class="{ 'coverage-row--loading': overviewLoading || overviewNeedsRefresh }">
              <div class="coverage-row-label">
                <strong>{{ row.label }}</strong>
                <span>{{ overviewLoading ? '加载中' : (overviewNeedsRefresh ? '等待刷新' : `${formatNumber(row.translated)} / ${formatNumber(row.total)}`) }}</span>
              </div>
              <div class="overview-track compact" :class="{ 'skeleton-track': overviewLoading || overviewNeedsRefresh }" :aria-label="`${row.label}覆盖率`">
                <div :style="{ width: (overviewLoading || overviewNeedsRefresh) ? '52%' : `${row.percent}%` }"></div>
              </div>
              <span class="coverage-percent">{{ (overviewLoading || overviewNeedsRefresh) ? '...' : `${row.percent}%` }}</span>
            </div>
          </div>
        </section>

        <section class="overview-signals" aria-label="工作台和缓存">
          <div class="signal-card" :class="{ loading: overviewLoading || overviewNeedsRefresh }">
            <span class="overview-kicker">待处理工作台</span>
            <strong>{{ overviewLoading ? '加载中' : (overviewNeedsRefresh ? '待刷新' : formatNumber(workbenchPendingCount)) }}</strong>
            <small>{{ overviewLoading ? '校对状态统计中' : (overviewNeedsRefresh ? '未加载统计' : `机翻 ${formatNumber(reviewStatsByStatus.machine_translated || 0)} · 未翻译 ${formatNumber(reviewStatsByStatus.untranslated || 0)}`) }}</small>
          </div>
          <div class="signal-card" :class="{ quiet: !(reviewStatsByStatus.failed || 0), loading: overviewLoading || overviewNeedsRefresh }">
            <span class="overview-kicker">失败条目</span>
            <strong>{{ overviewLoading ? '加载中' : (overviewNeedsRefresh ? '待刷新' : formatNumber(reviewStatsByStatus.failed || 0)) }}</strong>
            <small>{{ overviewLoading ? '风险统计中' : (overviewNeedsRefresh ? '未加载统计' : `已校对 ${formatNumber(reviewStatsByStatus.reviewed || 0)} · 人工 ${formatNumber(reviewStatsByStatus.manual_edited || 0)}`) }}</small>
          </div>
          <div class="signal-card" :class="{ loading: overviewLoading || overviewNeedsRefresh }">
            <span class="overview-kicker">缓存与映射</span>
            <strong>{{ overviewLoading ? '加载中' : (overviewNeedsRefresh ? '待刷新' : formatNumber(stats.ai_cache || 0)) }}</strong>
            <small>{{ overviewLoading ? '缓存统计中' : (overviewNeedsRefresh ? '未加载统计' : `标题缓存 ${formatNumber(coverageTitle.cached || 0)} · 正式映射 ${formatNumber(coverageTitle.mapped || stats.title || 0)}`) }}</small>
          </div>
        </section>

        <aside class="job-control-card" :class="{ empty: !jobControlJob }" aria-label="任务状态">
          <div class="job-control-head">
            <div>
              <span class="overview-kicker">任务状态</span>
              <strong>{{ jobControlJob ? `#${jobControlJob.id} · ${jobTypeLabel(jobControlJob.job_type)}` : '暂无作业' }}</strong>
            </div>
            <span class="status-pill" :class="jobStatusClass(jobControlJob?.status)">{{ statusLabel(jobControlJob?.status) }}</span>
          </div>

          <div class="job-control-progress">
            <div class="job-progress-label">
              <span>进度</span>
              <strong>{{ jobProgressValue(jobControlJob) }}%</strong>
            </div>
            <div class="overview-track" aria-label="当前作业进度">
              <div :style="{ width: `${jobProgressValue(jobControlJob)}%` }"></div>
            </div>
          </div>

          <div class="job-control-metrics">
            <div>
              <span>处理</span>
              <strong>{{ formatNumber(jobControlJob?.processed || 0) }} / {{ formatNumber(jobControlJob?.total || 0) }}</strong>
            </div>
            <div>
              <span>翻译</span>
              <strong>{{ formatNumber(jobControlJob?.translated || 0) }}</strong>
            </div>
            <div>
              <span>跳过</span>
              <strong>{{ formatNumber(jobControlJob?.skipped || 0) }}</strong>
            </div>
            <div :class="{ danger: (jobControlJob?.failed || 0) > 0 }">
              <span>失败</span>
              <strong>{{ formatNumber(jobControlJob?.failed || 0) }}</strong>
            </div>
          </div>

          <div class="job-control-meta">
            <span>创建 {{ formatTime(jobControlJob?.created_at) }}</span>
            <span>耗时 {{ durationText(jobControlJob?.duration_seconds) }}</span>
            <span>源 {{ providerOrderLabel(jobControlJob?.provider_order) }}</span>
          </div>

          <div v-if="jobControlJob?.error_msg" class="job-error">{{ jobControlJob.error_msg }}</div>

          <div class="job-control-actions">
            <button v-if="canPauseCurrentJob" class="btn btn-ghost btn-sm" type="button" :disabled="pausingJob" @click="pauseJob">
              {{ pausingJob ? '暂停中...' : '暂停作业' }}
            </button>
            <button class="btn btn-primary btn-sm" type="button" :disabled="!canStartContinuationJob" @click="continueJobFromLatest">
              {{ startingJob ? '继续中...' : '继续翻译' }}
            </button>
            <button class="btn btn-ghost btn-sm" type="button" @click="setActiveSegment('history')">历史记录</button>
          </div>

          <small v-if="!jobControlJob" class="muted">会按当前默认字段从剩余内容继续处理。</small>
        </aside>
      </div>
    </section>

    <section v-else-if="activeSegment === 'create'" class="workspace-panel apple-surface">
      <div class="panel-header">
        <div>
          <h2>创建作业</h2>
        </div>
        <span class="chain-pill">{{ selectedProviderOrderLabel }}</span>
      </div>

      <div class="notice-row">
        <strong>批量作业默认不使用智能兜底</strong>
        <span>默认先查正式映射，再走低成本翻译源；简介仍由实时链路处理。</span>
      </div>

      <div class="form-grid">
        <label class="field">
          <span>翻译字段</span>
          <GlassSelect
            v-model="jobForm.job_type"
            :options="jobTypeOptions"
            aria-label="翻译字段"
          />
        </label>
        <label class="field">
          <span>作业模式</span>
          <GlassSelect
            v-model="jobForm.mode"
            :options="jobModeOptions"
            aria-label="作业模式"
          />
        </label>
      </div>

      <div class="notice-row secondary">
        <strong>{{ jobModeLabel }}</strong>
        <span>{{ jobModeHint }}</span>
      </div>

      <div class="provider-list">
        <label
          v-for="provider in providerOptions"
          :key="provider.key"
          class="provider-row"
          :class="{ enabled: selectedProvider === provider.key }"
        >
          <input v-model="selectedProvider" type="radio" name="translation-provider" :value="provider.key" />
          <div>
            <strong>{{ provider.label }}</strong>
            <small>{{ provider.hint }}</small>
          </div>
          <span class="provider-status">{{ providerStatusLabel(provider.key) }}</span>
        </label>
      </div>

      <div class="panel-footer-actions">
        <button class="btn btn-primary" type="button" :disabled="startingJob || !selectedProvider" @click="startJob">
          {{ startingJob ? '启动中...' : '开始翻译作业' }}
        </button>
      </div>
      <div v-if="jobMessage" class="message-line" :class="jobMessageType">{{ jobMessage }}</div>
    </section>

    <section v-else-if="activeSegment === 'sources'" class="workspace-panel apple-surface">
      <div class="panel-header">
        <div>
          <h2>翻译源</h2>
        </div>
        <div class="panel-actions">
          <label class="mini-toggle">
            <input v-model="translationConfig.enabled" type="checkbox" />
            <span>启用翻译</span>
          </label>
          <button class="btn btn-primary btn-sm" type="button" :disabled="savingConfig" @click="saveTranslationConfig">
            {{ savingConfig ? '保存中...' : '保存翻译源' }}
          </button>
        </div>
      </div>

      <div class="source-layout">
        <section class="source-section">
          <div class="source-section-head">
            <div>
              <strong>低成本批量源</strong>
              <span>用于标题、演员、题材、系列和厂商名。</span>
            </div>
          </div>
          <div class="form-grid">
            <label class="field">
              <span>目标语言</span>
              <input v-model="translationConfig.target_language" class="input" placeholder="zh-CN" />
            </label>
            <label class="field">
              <span>实时模式</span>
              <input v-model="translationConfig.realtime_mode" class="input" disabled />
            </label>
            <label class="field">
              <span>批量并发</span>
              <input v-model.number="translationConfig.batch_concurrency" class="input" type="number" min="1" max="64" />
            </label>
            <label class="field">
              <span>单批行数</span>
              <input v-model.number="translationConfig.batch_size" class="input" type="number" min="1" max="200" />
            </label>
            <label class="field">
              <span>单批字符</span>
              <input v-model.number="translationConfig.batch_char_limit" class="input" type="number" min="500" max="24000" />
            </label>
            <label class="field">
              <span>源页大小</span>
              <input v-model.number="translationConfig.source_page_size" class="input" type="number" min="20" max="1000" />
            </label>
            <label class="field">
              <span>扫描页组</span>
              <input v-model.number="translationConfig.scan_pages_per_batch" class="input" type="number" min="1" max="64" />
            </label>
          </div>
          <div class="source-settings">
            <label class="check-row boxed">
              <input v-model="translationConfig.google_free.enabled" type="checkbox" />
              <span>Google 免费接口</span>
            </label>
            <input v-model="translationConfig.google_free.base_url" class="input" placeholder="https://translate.googleapis.com/translate_a/single" />
            <div class="form-grid">
              <label class="check-row boxed">
                <input v-model="translationConfig.baidu.enabled" type="checkbox" />
                <span>启用百度翻译</span>
              </label>
              <input v-model.number="translationConfig.baidu.timeout" class="input" type="number" min="1" placeholder="超时（秒）" />
              <input v-model.number="translationConfig.baidu.qps" class="input" type="number" min="0" step="0.5" placeholder="每秒请求数" />
            </div>
            <input v-model="translationConfig.baidu.app_id" class="input" placeholder="百度翻译 APP ID" autocomplete="off" />
            <input v-model="translationConfig.baidu.secret" class="input" :type="showBaiduSecret ? 'text' : 'password'" placeholder="百度翻译 Secret，空白保存不覆盖现有密钥" autocomplete="off" />
            <input v-model="translationConfig.baidu.endpoint" class="input" placeholder="https://fanyi-api.baidu.com/api/trans/vip/translate" />
            <div class="form-grid">
              <label class="check-row boxed">
                <input v-model="translationConfig.deepl.enabled" type="checkbox" />
                <span>启用 DeepL</span>
              </label>
              <label class="check-row boxed">
                <input v-model="translationConfig.deepl.free_api" type="checkbox" />
                <span>免费接口</span>
              </label>
            </div>
            <input v-model="translationConfig.deepl.api_key" class="input" :type="showDeeplKey ? 'text' : 'password'" placeholder="DeepL 密钥，可选" autocomplete="off" />
            <div class="form-grid">
              <label class="check-row boxed">
                <input v-model="translationConfig.microsoft.enabled" type="checkbox" />
                <span>启用 Microsoft</span>
              </label>
              <input v-model="translationConfig.microsoft.region" class="input" placeholder="Azure 区域，例如 eastasia" />
            </div>
            <input v-model="translationConfig.microsoft.api_key" class="input" :type="showMicrosoftKey ? 'text' : 'password'" placeholder="Microsoft 密钥，可选" autocomplete="off" />
          </div>
          <div class="key-actions left">
            <button class="btn btn-ghost btn-sm" type="button" @click="showBaiduSecret = !showBaiduSecret">{{ showBaiduSecret ? '隐藏百度 Secret' : '显示百度 Secret' }}</button>
            <button class="btn btn-ghost btn-sm" type="button" @click="showDeeplKey = !showDeeplKey">{{ showDeeplKey ? '隐藏 DeepL 密钥' : '显示 DeepL 密钥' }}</button>
            <button class="btn btn-ghost btn-sm" type="button" @click="showMicrosoftKey = !showMicrosoftKey">{{ showMicrosoftKey ? '隐藏 Microsoft 密钥' : '显示 Microsoft 密钥' }}</button>
          </div>
        </section>

        <section class="source-section">
          <div class="source-section-head">
            <div>
              <strong>实时兜底</strong>
              <span>公共智能翻译参数在设置页维护，这里只用于状态检测和手动测试。</span>
            </div>
            <span class="provider-status">{{ providerStatusLabel('ai') }}</span>
          </div>
          <div class="source-settings">
            <textarea v-model="translationTestText" class="input test-textarea" rows="3" placeholder="输入一小段文本测试实时翻译"></textarea>
            <div class="key-actions left">
              <button class="btn btn-primary btn-sm" type="button" :disabled="testingTranslation || !translationTestText.trim()" @click="testTranslation">
                {{ testingTranslation ? '测试中...' : '测试实时翻译' }}
              </button>
            </div>
            <div v-if="translationTestMsg" class="message-line" :class="translationTestType">{{ translationTestMsg }}</div>
          </div>
        </section>
      </div>
    </section>

    <section v-else-if="activeSegment === 'review'" class="workspace-panel apple-surface">
      <div class="panel-header">
        <div>
          <h2>校对台</h2>
        </div>
        <div class="panel-actions">
          <button class="btn btn-ghost btn-sm" type="button" :disabled="reviewLoading" @click="loadTranslationItems(reviewPage)">
            {{ reviewLoading ? '加载中...' : '刷新条目' }}
          </button>
          <button class="btn btn-primary btn-sm" type="button" :disabled="retryingItems" @click="retryReviewItems">
            {{ retryingItems ? '提交中...' : '重试当前筛选' }}
          </button>
        </div>
      </div>

      <div class="review-toolbar">
        <label class="field">
          <span>类型</span>
          <GlassSelect
            v-model="reviewType"
            :options="translationTypeOptions"
            aria-label="校对类型"
            @change="loadTranslationItems(1)"
          />
        </label>
        <label class="field">
          <span>状态</span>
          <GlassSelect
            v-model="reviewStatus"
            :options="reviewStatusOptions"
            aria-label="校对状态"
            @change="loadTranslationItems(1)"
          />
        </label>
        <label class="field search-field">
          <span>检索</span>
          <input
            v-model="reviewQuery"
            class="input"
            placeholder="演员名、日文、中文、番号或标题"
            @keyup.enter="loadTranslationItems(1)"
          />
        </label>
        <button class="btn btn-ghost review-search-btn" type="button" @click="loadTranslationItems(1)">搜索</button>
      </div>

      <div class="review-stats">
        <div><strong>{{ reviewTotal }}</strong><span>索引条目</span></div>
        <div><strong>{{ reviewStatsByStatus.untranslated || 0 }}</strong><span>未翻译</span></div>
        <div><strong>{{ reviewStatsByStatus.failed || 0 }}</strong><span>失败</span></div>
        <div><strong>{{ reviewUnreviewed }}</strong><span>待校对</span></div>
      </div>

      <div v-if="reviewMessage" class="message-line" :class="reviewMessageType">{{ reviewMessage }}</div>

      <div class="review-table">
        <div class="review-head">
          <span>原文</span>
          <span>当前译文</span>
          <span>状态</span>
          <span>来源</span>
          <span>操作</span>
        </div>
        <div v-if="reviewLoading && !reviewItems.length" class="empty-panel compact">加载中...</div>
        <div v-else-if="!reviewItems.length" class="empty-panel compact">暂无工作台条目</div>
        <div v-for="item in reviewItems" :key="`${item.item_type}:${item.item_id}`" class="review-row">
          <div class="review-source">
            <strong>{{ item.source_text || '—' }}</strong>
            <small>{{ translationTypeLabels[item.item_type] || item.item_type }} · {{ item.item_id }}</small>
          </div>
          <textarea v-model="item.edit_text" class="input review-edit" rows="2"></textarea>
          <span class="status-pill" :class="workbenchStatusClass(item.status)">{{ workbenchStatusLabel(item.status) }}</span>
          <div class="review-meta">
            <span>{{ providerLabel(item.provider) || '本地' }}</span>
            <small>{{ formatTime(item.updated_at) }}</small>
            <small v-if="item.last_error" class="error-text">{{ item.last_error }}</small>
          </div>
          <div class="review-actions">
            <button class="btn btn-primary btn-sm" type="button" @click="saveReviewItem(item)">保存</button>
            <button class="btn btn-ghost btn-sm" type="button" @click="markReviewItem(item)">标记已校对</button>
            <button class="btn btn-ghost btn-sm" type="button" @click="showItemHistory(item)">历史</button>
            <button class="btn btn-ghost btn-sm danger" type="button" @click="resetReviewItem(item)">重置</button>
          </div>
        </div>
      </div>

      <div class="review-pagination">
        <button class="btn btn-ghost btn-sm" type="button" :disabled="reviewPage <= 1" @click="loadTranslationItems(reviewPage - 1)">上一页</button>
        <span>共 {{ reviewTotalCount }} 条 · 第 {{ reviewPage }} / {{ reviewTotalPages }} 页</span>
        <label class="page-size-field">
          <span>每页</span>
          <GlassSelect
            v-model="reviewPageSize"
            :options="reviewPageSizeOptions"
            size="compact"
            aria-label="校对台每页条数"
            @change="loadTranslationItems(1)"
          />
        </label>
        <button class="btn btn-ghost btn-sm" type="button" :disabled="reviewPage >= reviewTotalPages" @click="loadTranslationItems(reviewPage + 1)">下一页</button>
      </div>

      <aside v-if="reviewHistoryItem" class="review-history-panel">
        <div class="recent-head">
          <strong>{{ reviewHistoryItem.source_text }} 的修改历史</strong>
          <button class="btn btn-ghost btn-sm" type="button" @click="reviewHistoryItem = null">关闭</button>
        </div>
        <div v-if="reviewHistoryLoading" class="empty-panel compact">加载中...</div>
        <div v-else-if="!reviewHistory.length" class="empty-panel compact">暂无修改历史</div>
        <div v-for="history in reviewHistory" :key="history.id" class="history-row review-history-row">
          <div>
            <strong>{{ history.action }}</strong>
            <span>{{ history.old_text || '空' }} -> {{ history.new_text || '空' }}</span>
          </div>
          <button class="btn btn-ghost btn-sm" type="button" @click="restoreHistoryItem(history)">恢复</button>
        </div>
      </aside>
    </section>

    <section v-else-if="activeSegment === 'mappings'" class="workspace-panel apple-surface">
      <div class="panel-header">
        <div>
          <h2>映射导入</h2>
        </div>
      </div>
      <div class="mapping-layout">
        <label class="field">
          <span>映射类型</span>
          <GlassSelect
            v-model="translationType"
            :options="translationTypeOptions"
            aria-label="映射类型"
          />
        </label>
        <div class="mapping-stat">
          <strong>{{ currentCoverage.translated || stats[translationType] || 0 }}</strong>
          <span>当前 {{ translationTypeLabels[translationType] }} 已翻译 · 未翻译 {{ currentCoverage.untranslated || 0 }}</span>
        </div>
        <div class="mapping-actions">
          <button class="btn btn-ghost" type="button" @click="exportTranslation">导出 {{ translationTypeLabels[translationType] }}</button>
          <label class="btn btn-ghost import-button">
            导入 {{ translationTypeLabels[translationType] }}
            <input type="file" accept=".json" @change="importTranslation" />
          </label>
        </div>
      </div>
      <div v-if="mappingMessage" class="message-line" :class="mappingMessageType">{{ mappingMessage }}</div>
    </section>

    <section v-else-if="activeSegment === 'history'" class="workspace-panel apple-surface">
      <div class="panel-header">
        <div>
          <h2>历史记录</h2>
        </div>
        <button class="btn btn-ghost btn-sm" type="button" @click="loadJobs">刷新历史</button>
      </div>
      <div class="history-layout">
        <div v-if="jobs.length" class="history-list">
          <button
            v-for="job in jobs"
            :key="job.id"
            class="history-row"
            type="button"
            :class="{ active: selectedJob?.id === job.id }"
            @click="selectJob(job)"
          >
            <div>
              <strong>#{{ job.id }} · {{ jobTypeLabel(job.job_type) }}</strong>
              <span>{{ statusLabel(job.status) }} · {{ formatTime(job.created_at) }}</span>
            </div>
            <small>{{ job.progress_percent || 0 }}% · 成功 {{ job.translated || 0 }} · 失败 {{ job.failed || 0 }}</small>
          </button>
        </div>
        <div v-else class="empty-panel">暂无历史作业</div>

        <aside v-if="selectedJob" class="result-summary">
          <strong>结果摘要</strong>
          <span>处理 {{ selectedJob.processed || 0 }} / {{ selectedJob.total || 0 }}</span>
          <span>翻译 {{ selectedJob.translated || 0 }} · 跳过 {{ selectedJob.skipped || 0 }} · 失败 {{ selectedJob.failed || 0 }}</span>
          <span>耗时 {{ durationText(selectedJob.duration_seconds) }}</span>
          <span>源 {{ providerOrderLabel(selectedJob.provider_order) }}</span>
          <span v-if="selectedJob.error_msg" class="error-text">{{ selectedJob.error_msg }}</span>
        </aside>
      </div>
    </section>
  </div>
</template>

<script>
import { ElMessage } from '../utils/message.js'
import api from '../api'
import { requestConfirm } from '../utils/confirmDialog'
import GlassSelect from '../components/GlassSelect.vue'
import { DEFAULT_CONFIG, TRANSLATION_TYPE_LABELS } from '../features/config/configDefaults.js'

const BASE_BATCH_ORDER = ['cache', 'mapping']
const TRANSLATION_STATS_CACHE_KEY = 'javhub_translation_stats_cache'
let cachedTranslationStats = null
const JOB_TYPE_OPTIONS = [
  { value: 'library_titles', label: '库内影片标题', hint: '独立处理片库标题，默认走低成本源。' },
  { value: 'metadata_categories', label: '题材名称', hint: '只翻译题材名称。' },
  { value: 'metadata_series', label: '系列名称', hint: '只翻译系列名称。' },
  { value: 'metadata_makers', label: '厂商名称', hint: '只翻译厂商名称。' },
  { value: 'metadata_labels', label: '厂牌名称', hint: '只翻译厂牌名称。' },
  { value: 'metadata_actresses', label: '演员名称', hint: '只翻译演员名称。' },
  { value: 'metadata_names', label: '全部元数据名称', hint: '题材、系列、厂商、厂牌、演员一起处理。' },
]
const JOB_MODE_OPTIONS = [
  { value: 'remaining', label: '补剩余', hint: '跳过已有正式映射，优先处理失败项，适合中断后继续。' },
  { value: 'refresh_all', label: '全量重翻', hint: '忽略已有译文，用新的翻译结果覆盖。' },
]
const TRANSLATION_TYPE_OPTIONS = Object.entries(TRANSLATION_TYPE_LABELS)
  .map(([value, label]) => ({ value, label }))
const WORKBENCH_STATUS_OPTIONS = [
  { value: 'all', label: '全部状态' },
  { value: 'untranslated', label: '未翻译' },
  { value: 'failed', label: '失败' },
  { value: 'machine_translated', label: '机翻' },
  { value: 'reviewed', label: '已校对' },
  { value: 'manual_edited', label: '人工修改' },
  { value: 'invalid', label: '无效' },
]
const PROVIDER_META = {
  google_free: { label: 'Google 免费接口', hint: '无密钥，适合标题和短名称批量翻译。' },
  baidu: { label: '百度翻译', hint: '使用百度通用文本翻译 API，适合已有免费 key 的低成本翻译。' },
  deepl: { label: 'DeepL', hint: '质量更高，需要配置密钥。' },
  microsoft: { label: 'Microsoft 翻译', hint: 'Azure 翻译接口，需要密钥和可选区域。' },
  ai: { label: '智能兜底', hint: '使用设置页当前公共智能模型，适合低成本源效果不好时补充。' },
}
const PROVIDER_KEYS = Object.keys(PROVIDER_META)

function cloneTranslationConfig() {
  return JSON.parse(JSON.stringify(DEFAULT_CONFIG.translation))
}

export default {
  name: 'TranslationJobs',
  components: { GlassSelect },
  data() {
    return {
      activeSegment: 'overview',
      segments: [
        { key: 'overview', label: '总览' },
        { key: 'create', label: '创建作业' },
        { key: 'sources', label: '翻译源' },
        { key: 'review', label: '校对台' },
        { key: 'mappings', label: '映射导入' },
        { key: 'history', label: '历史记录' },
      ],
      loading: false,
      statsLoading: false,
      statsLoaded: false,
      savingConfig: false,
      startingJob: false,
      pausingJob: false,
      testingTranslation: false,
      stats: {},
      jobs: [],
      currentJob: null,
      selectedJob: null,
      jobTypeOptions: JOB_TYPE_OPTIONS,
      jobModeOptions: JOB_MODE_OPTIONS,
      pollTimer: null,
      translationConfig: cloneTranslationConfig(),
      translationType: 'title',
      translationTypeLabels: TRANSLATION_TYPE_LABELS,
      translationTypeOptions: TRANSLATION_TYPE_OPTIONS,
      reviewType: 'actress',
      reviewStatus: 'all',
      reviewStatusOptions: WORKBENCH_STATUS_OPTIONS,
      reviewQuery: '',
      reviewPage: 1,
      reviewPageSize: 30,
      reviewPageSizeOptions: [
        { value: 30, label: '30' },
        { value: 50, label: '50' },
        { value: 100, label: '100' },
        { value: 200, label: '200' },
      ],
      reviewTotalCount: 0,
      reviewTotalPages: 1,
      reviewItems: [],
      reviewStats: {},
      reviewLoading: false,
      retryingItems: false,
      reviewMessage: '',
      reviewMessageType: 'info',
      reviewHistoryItem: null,
      reviewHistory: [],
      reviewHistoryLoading: false,
      translationTestText: 'これは翻訳テストです。',
      translationTestMsg: '',
      translationTestType: 'info',
      mappingMessage: '',
      mappingMessageType: 'info',
      jobMessage: '',
      jobMessageType: 'info',
      selectedProvider: 'google_free',
      showBaiduSecret: false,
      showDeeplKey: false,
      showMicrosoftKey: false,
      providerOptions: PROVIDER_KEYS.map(key => ({ key, ...PROVIDER_META[key] })),
      jobForm: {
        job_type: 'library_titles',
        mode: 'remaining',
      },
    }
  },
  computed: {
    coverage() {
      return this.stats.coverage || {}
    },
    coverageTitle() {
      return this.coverage.title || {}
    },
    currentCoverage() {
      return this.coverage[this.translationType] || {}
    },
    workbenchStats() {
      return this.reviewStats.total !== undefined ? this.reviewStats : (this.stats.workbench || {})
    },
    reviewStatsByStatus() {
      return this.workbenchStats.by_status || {}
    },
    reviewTotal() {
      return this.workbenchStats.total || this.reviewTotalCount || 0
    },
    reviewUnreviewed() {
      return (this.reviewStatsByStatus.machine_translated || 0) + (this.reviewStatsByStatus.untranslated || 0) + (this.reviewStatsByStatus.failed || 0)
    },
    metadataCoverage() {
      return ['actress', 'category', 'series', 'maker', 'label'].reduce((acc, key) => {
        const item = this.coverage[key] || {}
        acc.total += item.total || 0
        acc.translated += item.translated || 0
        acc.untranslated += item.untranslated || 0
        return acc
      }, { total: 0, translated: 0, untranslated: 0 })
    },
    coverageRows() {
      return [
        { key: 'actress', label: '演员' },
        { key: 'category', label: '题材' },
        { key: 'series', label: '系列' },
        { key: 'maker', label: '厂商' },
        { key: 'label', label: '厂牌' },
      ].map(row => {
        const item = this.coverage[row.key] || {}
        return {
          ...row,
          total: item.total || 0,
          translated: item.translated || 0,
          untranslated: item.untranslated || 0,
          percent: this.percentValue(item),
        }
      })
    },
    workbenchPendingCount() {
      return (this.reviewStatsByStatus.machine_translated || 0)
        + (this.reviewStatsByStatus.untranslated || 0)
        + (this.reviewStatsByStatus.failed || 0)
    },
    overviewLoading() {
      return this.statsLoading && !Object.keys(this.coverage || {}).length
    },
    overviewNeedsRefresh() {
      return !this.statsLoading && !this.statsLoaded
    },
    jobControlJob() {
      return this.currentJob || this.jobs[0] || this.selectedJob || null
    },
    selectedProviderOrder() {
      return [...BASE_BATCH_ORDER, this.selectedProvider]
    },
    selectedProviderOrderLabel() {
      return this.providerOrderLabel(this.selectedProviderOrder)
    },
    canPauseCurrentJob() {
      return Boolean(this.currentJob?.id && ['pending', 'running'].includes(this.currentJob.status))
    },
    canStartContinuationJob() {
      const status = this.jobControlJob?.status
      return !this.startingJob
        && Boolean(this.selectedProvider)
        && !['pending', 'running'].includes(status)
    },
    selectedJobMode() {
      return JOB_MODE_OPTIONS.find(option => option.value === this.jobForm.mode) || JOB_MODE_OPTIONS[0]
    },
    jobModeLabel() {
      return this.selectedJobMode.label
    },
    jobModeHint() {
      return this.selectedJobMode.hint
    },
  },
  async mounted() {
    this.loadCachedStats()
    await this.reloadAll()
  },
  beforeUnmount() {
    this.stopPolling()
  },
  methods: {
    async setActiveSegment(segment) {
      this.activeSegment = segment
      if (segment === 'review' && !this.reviewItems.length) {
        await this.loadTranslationItems(1)
      }
    },
    async reloadAll() {
      this.loading = true
      try {
        await Promise.all([this.loadConfig(), this.loadJobs()])
        this.pickCurrentJob()
        if (this.activeSegment === 'review') await this.loadTranslationItems(this.reviewPage)
      } finally {
        this.loading = false
      }
    },
    async refreshOverview() {
      this.loading = true
      try {
        await Promise.all([this.loadConfig(), this.loadJobs()])
        this.pickCurrentJob()
        if (this.activeSegment === 'review') await this.loadTranslationItems(this.reviewPage)
        await this.loadStats()
      } finally {
        this.loading = false
      }
    },
    async loadConfig() {
      try {
        const resp = await api.getConfig()
        const remote = resp.data?.translation || {}
        this.translationConfig = this.mergeTranslationConfig(remote)
        this.syncProvidersFromConfig()
      } catch (error) {
        console.error('Failed to load translation config:', error)
        ElMessage.error('翻译配置加载失败')
      }
    },
    translationStatsStorage() {
      try {
        return typeof window !== 'undefined' ? window.localStorage : null
      } catch (error) {
        return null
      }
    },
    loadCachedStats() {
      try {
        if (cachedTranslationStats) {
          this.stats = cachedTranslationStats
          this.statsLoaded = true
          return
        }
        const storage = this.translationStatsStorage()
        const cached = storage?.getItem(TRANSLATION_STATS_CACHE_KEY)
        if (!cached) return
        const parsed = JSON.parse(cached)
        if (!parsed || typeof parsed !== 'object') return
        cachedTranslationStats = parsed
        this.stats = parsed
        this.statsLoaded = true
      } catch (error) {
        console.warn('Failed to load cached translation stats:', error)
      }
    },
    saveCachedStats(stats) {
      try {
        cachedTranslationStats = stats || {}
        const storage = this.translationStatsStorage()
        storage?.setItem(TRANSLATION_STATS_CACHE_KEY, JSON.stringify(cachedTranslationStats))
      } catch (error) {
        console.warn('Failed to save cached translation stats:', error)
      }
    },
    mergeTranslationConfig(remote = {}) {
      const base = cloneTranslationConfig()
      const merged = { ...base, ...remote }
      for (const key of ['google_free', 'baidu', 'deepl', 'microsoft']) {
        merged[key] = { ...(base[key] || {}), ...((remote && remote[key]) || {}) }
      }
      delete merged.openai_compatible
      merged.provider = this.normalizeProvider(merged.provider || this.firstNetworkProvider(merged.batch_provider_order) || this.firstNetworkProvider(merged.provider_order))
      if (!Array.isArray(merged.provider_order)) merged.provider_order = [...base.provider_order]
      if (!Array.isArray(merged.batch_provider_order)) merged.batch_provider_order = [...base.batch_provider_order]
      if (!merged.realtime_mode || merged.realtime_mode === 'sync') merged.realtime_mode = 'cache_only'
      merged.batch_concurrency = Math.max(1, Math.min(Number(merged.batch_concurrency || 32), 64))
      merged.batch_size = Math.max(1, Math.min(Number(merged.batch_size || 200), 200))
      merged.batch_char_limit = Math.max(500, Math.min(Number(merged.batch_char_limit || 24000), 24000))
      merged.source_page_size = Math.max(20, Math.min(Number(merged.source_page_size || 500), 1000))
      merged.scan_pages_per_batch = Math.max(1, Math.min(Number(merged.scan_pages_per_batch || 8), 64))
      merged.baidu.qps = Math.max(0, Number(merged.baidu.qps ?? 1) || 0)
      merged.baidu.timeout = Math.max(1, Number(merged.baidu.timeout || 15))
      return merged
    },
    async loadStats() {
      this.statsLoading = true
      try {
        const resp = await api.getTranslationStats()
        this.stats = resp.data || {}
        this.saveCachedStats(this.stats)
        this.statsLoaded = true
      } catch (error) {
        console.error('Failed to load translation stats:', error)
        if (!this.statsLoaded) this.stats = {}
      } finally {
        this.statsLoading = false
      }
    },
    async loadJobs() {
      try {
        const resp = await api.listTranslationJobs(50)
        this.jobs = resp.data?.data || []
        if (!this.selectedJob && this.jobs.length) this.selectedJob = this.jobs[0]
        if (this.selectedJob) {
          this.selectedJob = this.jobs.find(job => job.id === this.selectedJob.id) || this.selectedJob
        }
      } catch (error) {
        console.error('Failed to load translation jobs:', error)
        this.jobs = []
      }
    },
    pickCurrentJob() {
      const running = this.jobs.find(job => ['pending', 'running'].includes(job.status))
      this.currentJob = running || this.jobs[0] || null
      if (running) this.startPolling(running.id)
    },
    syncProvidersFromConfig() {
      this.selectedProvider = this.normalizeProvider(this.translationConfig.provider)
      this.syncSelectedProviderToConfig()
    },
    syncSelectedProviderToConfig() {
      this.translationConfig.provider = this.selectedProvider
      this.translationConfig.batch_provider_order = this.selectedProviderOrder
      this.translationConfig.provider_order = this.selectedProviderOrder
    },
    async saveTranslationConfig() {
      this.savingConfig = true
      this.syncSelectedProviderToConfig()
      const payload = {
        translation: {
          ...this.translationConfig,
          provider: this.selectedProvider,
          provider_order: this.selectedProviderOrder,
          batch_provider_order: this.selectedProviderOrder,
          realtime_mode: this.translationConfig.realtime_mode || 'cache_only',
          batch_concurrency: Math.max(1, Math.min(Number(this.translationConfig.batch_concurrency || 32), 64)),
          batch_size: Math.max(1, Math.min(Number(this.translationConfig.batch_size || 200), 200)),
          batch_char_limit: Math.max(500, Math.min(Number(this.translationConfig.batch_char_limit || 24000), 24000)),
          source_page_size: Math.max(20, Math.min(Number(this.translationConfig.source_page_size || 500), 1000)),
          scan_pages_per_batch: Math.max(1, Math.min(Number(this.translationConfig.scan_pages_per_batch || 8), 64)),
          baidu: {
            ...this.translationConfig.baidu,
            qps: Math.max(0, Number(this.translationConfig.baidu.qps ?? 1) || 0),
            timeout: Math.max(1, Number(this.translationConfig.baidu.timeout || 15)),
          },
        },
      }
      try {
        await api.updateConfig(payload)
        ElMessage.success('翻译源配置已保存')
        await this.loadStats()
      } catch (error) {
        console.error('Failed to save translation config:', error)
        ElMessage.error('保存翻译源失败')
      } finally {
        this.savingConfig = false
      }
    },
    async startJob() {
      const confirmed = await requestConfirm({
        title: this.jobForm.mode === 'refresh_all' ? '开始全量重翻' : '开始翻译作业',
        message: this.jobForm.mode === 'refresh_all'
          ? `确认用 ${this.providerLabel(this.selectedProvider)} 重新翻译「${this.jobTypeLabel(this.jobForm.job_type)}」？`
          : `确认用 ${this.providerLabel(this.selectedProvider)} 翻译「${this.jobTypeLabel(this.jobForm.job_type)}」的剩余内容？`,
        details: this.jobForm.mode === 'refresh_all'
          ? '全量重翻会忽略已有译文，并可能覆盖现有正式映射。'
          : '会创建真实翻译作业，消耗当前翻译源配额，并写入翻译缓存或映射。',
        confirmText: this.jobForm.mode === 'refresh_all' ? '开始重翻' : '开始翻译',
        tone: this.jobForm.mode === 'refresh_all' ? 'danger' : 'default',
      })
      if (!confirmed) return
      this.startingJob = true
      this.jobMessage = ''
      this.jobMessageType = 'info'
      try {
        const resp = await api.startTranslationJob({
          job_type: this.jobForm.job_type,
          provider: this.selectedProvider,
          mode: this.jobForm.mode,
        })
        const job = resp.data || {}
        this.currentJob = job
        this.selectedJob = job
        this.activeSegment = 'overview'
        this.jobMessage = `作业 #${job.id || ''} 已启动`
        this.jobMessageType = 'success'
        ElMessage.success('翻译作业已启动')
        await this.loadJobs()
        if (job.id) this.startPolling(job.id)
      } catch (error) {
        console.error('Failed to start translation job:', error)
        this.jobMessage = error.response?.data?.detail || '启动翻译作业失败'
        this.jobMessageType = 'error'
      } finally {
        this.startingJob = false
      }
    },
    async continueJobFromLatest() {
      if (!this.canStartContinuationJob) return
      const job = this.jobControlJob
      if (job?.job_type) this.jobForm.job_type = job.job_type
      this.jobForm.mode = 'remaining'
      await this.startJob()
    },
    startPolling(jobId) {
      this.stopPolling()
      this.pollTimer = setInterval(() => this.refreshCurrentJob(jobId), 2000)
      this.refreshCurrentJob(jobId)
    },
    stopPolling() {
      if (this.pollTimer) {
        clearInterval(this.pollTimer)
        this.pollTimer = null
      }
    },
    async pauseJob() {
      if (!this.canPauseCurrentJob) return
      this.pausingJob = true
      try {
        const resp = await api.pauseTranslationJob(this.currentJob.id)
        const job = resp.data || {}
        this.currentJob = job
        this.selectedJob = job
        this.jobs = [job, ...this.jobs.filter(item => item.id !== job.id)]
        this.stopPolling()
        ElMessage.success('翻译作业已暂停')
        this.loadStats()
        await this.loadJobs()
      } catch (error) {
        console.error('Failed to pause translation job:', error)
        ElMessage.error(error.response?.data?.detail || '暂停翻译作业失败')
      } finally {
        this.pausingJob = false
      }
    },
    async refreshCurrentJob(jobId) {
      try {
        const resp = await api.getTranslationJob(jobId)
        const job = resp.data || null
        if (!job) return
        this.currentJob = job
        this.jobs = [job, ...this.jobs.filter(item => item.id !== job.id)]
        if (this.selectedJob?.id === job.id) this.selectedJob = job
        if (['completed', 'failed', 'paused'].includes(job.status)) {
          this.stopPolling()
          this.loadStats()
          await this.loadJobs()
          this.pickCurrentJob()
        }
      } catch (error) {
        console.error('Failed to refresh translation job:', error)
        this.stopPolling()
      }
    },
    selectJob(job) {
      this.selectedJob = job
      this.activeSegment = 'history'
    },
    async testTranslation() {
      this.testingTranslation = true
      this.translationTestMsg = ''
      this.translationTestType = 'info'
      try {
        const resp = await api.testTranslation(this.translationTestText.trim(), this.selectedProvider)
        const translated = resp.data?.translated_text || ''
        this.translationTestMsg = translated ? `译文：${translated}` : '测试完成，但没有返回译文'
        this.translationTestType = translated ? 'success' : 'error'
      } catch (error) {
        console.error('Failed to test translation:', error)
        this.translationTestMsg = error.response?.data?.detail || '实时翻译测试失败，请检查兜底配置'
        this.translationTestType = 'error'
      } finally {
        this.testingTranslation = false
      }
    },
    async exportTranslation() {
      this.mappingMessage = ''
      try {
        const resp = await api.exportTranslations(this.translationType)
        const blob = new Blob([resp.data], { type: 'application/json;charset=utf-8' })
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `translations_${this.translationType}.json`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(url)
        this.mappingMessage = '导出已开始'
        this.mappingMessageType = 'success'
      } catch (error) {
        console.error('Failed to export translations:', error)
        this.mappingMessage = '导出失败'
        this.mappingMessageType = 'error'
      }
    },
    async importTranslation(event) {
      const file = event.target.files?.[0]
      if (!file) return
      const confirmed = await requestConfirm({
        title: '导入翻译映射',
        message: `确认导入 ${file.name} 到「${this.translationTypeLabels[this.translationType] || this.translationType}」？`,
        details: '导入会写入正式映射，已有同源文本可能被更新。',
        confirmText: '导入',
      })
      if (!confirmed) {
        event.target.value = ''
        return
      }
      this.mappingMessage = ''
      try {
        const resp = await api.importTranslations(this.translationType, file)
        this.mappingMessage = `导入完成：${resp.data?.imported || 0} 条`
        this.mappingMessageType = 'success'
        await this.loadStats()
      } catch (error) {
        console.error('Failed to import translations:', error)
        this.mappingMessage = error.response?.data?.detail || '导入失败，请确认 JSON 格式'
        this.mappingMessageType = 'error'
      } finally {
        event.target.value = ''
      }
    },
    async loadTranslationItems(page = 1) {
      this.reviewLoading = true
      this.reviewMessage = ''
      this.reviewPage = Math.max(1, Number(page) || 1)
      try {
        const params = {
          type: this.reviewType,
          page: this.reviewPage,
          page_size: this.reviewPageSize,
        }
        if (this.reviewStatus && this.reviewStatus !== 'all') params.status = this.reviewStatus
        if (this.reviewQuery.trim()) params.q = this.reviewQuery.trim()
        const resp = await api.listTranslationItems(params)
        const data = resp.data || {}
        this.reviewItems = (data.data || []).map(item => ({
          ...item,
          edit_text: item.translated_text || '',
        }))
        this.reviewTotalCount = data.total_count || 0
        this.reviewTotalPages = data.total_pages || 1
        this.reviewStats = data.stats || {}
      } catch (error) {
        console.error('Failed to load translation workbench:', error)
        this.reviewMessage = error.response?.data?.detail || '校对台加载失败'
        this.reviewMessageType = 'error'
      } finally {
        this.reviewLoading = false
      }
    },
    async saveReviewItem(item) {
      try {
        const resp = await api.updateTranslationItem(item.item_type, item.item_id, {
          action: 'save',
          source_text: item.source_text,
          translated_text: item.edit_text,
        })
        Object.assign(item, resp.data || {}, { edit_text: resp.data?.translated_text || item.edit_text })
        this.reviewMessage = '译文已保存'
        this.reviewMessageType = 'success'
        await Promise.all([this.loadStats(), this.loadTranslationItems(this.reviewPage)])
      } catch (error) {
        console.error('Failed to save translation item:', error)
        this.reviewMessage = error.response?.data?.detail || '保存失败'
        this.reviewMessageType = 'error'
      }
    },
    async markReviewItem(item) {
      try {
        const resp = await api.updateTranslationItem(item.item_type, item.item_id, {
          action: 'proofread',
          source_text: item.source_text,
        })
        Object.assign(item, resp.data || {}, { edit_text: resp.data?.translated_text || item.edit_text })
        this.reviewMessage = '已标记为已校对'
        this.reviewMessageType = 'success'
        await this.loadTranslationItems(this.reviewPage)
      } catch (error) {
        console.error('Failed to review translation item:', error)
        this.reviewMessage = error.response?.data?.detail || '标记失败'
        this.reviewMessageType = 'error'
      }
    },
    async resetReviewItem(item) {
      const confirmed = await requestConfirm({
        title: '重置译文',
        message: `确认清除「${item.source_text || item.item_id}」的译文？`,
        details: '会移除当前正式映射，并回到未翻译状态。',
        confirmText: '重置',
        tone: 'danger',
      })
      if (!confirmed) return
      try {
        const resp = await api.updateTranslationItem(item.item_type, item.item_id, {
          action: 'reset',
          source_text: item.source_text,
          clear_mapping: true,
        })
        Object.assign(item, resp.data || {}, { edit_text: '' })
        this.reviewMessage = '已重置为未翻译'
        this.reviewMessageType = 'success'
        await Promise.all([this.loadStats(), this.loadTranslationItems(this.reviewPage)])
      } catch (error) {
        console.error('Failed to reset translation item:', error)
        this.reviewMessage = error.response?.data?.detail || '重置失败'
        this.reviewMessageType = 'error'
      }
    },
    async showItemHistory(item) {
      this.reviewHistoryItem = item
      this.reviewHistoryLoading = true
      try {
        const resp = await api.getTranslationItemHistory(item.item_type, item.item_id, 50)
        this.reviewHistory = resp.data?.data || []
      } catch (error) {
        console.error('Failed to load translation item history:', error)
        this.reviewHistory = []
        this.reviewMessage = '历史加载失败'
        this.reviewMessageType = 'error'
      } finally {
        this.reviewHistoryLoading = false
      }
    },
    async restoreHistoryItem(history) {
      if (!this.reviewHistoryItem) return
      const confirmed = await requestConfirm({
        title: '恢复历史译文',
        message: '确认用这条历史记录覆盖当前译文？',
        details: history.translated_text || '',
        confirmText: '恢复',
      })
      if (!confirmed) return
      try {
        await api.updateTranslationItem(this.reviewHistoryItem.item_type, this.reviewHistoryItem.item_id, {
          action: 'restore',
          history_id: history.id,
        })
        this.reviewMessage = '已恢复历史版本'
        this.reviewMessageType = 'success'
        await Promise.all([
          this.loadStats(),
          this.loadTranslationItems(this.reviewPage),
          this.showItemHistory(this.reviewHistoryItem),
        ])
      } catch (error) {
        console.error('Failed to restore translation history:', error)
        this.reviewMessage = error.response?.data?.detail || '恢复失败'
        this.reviewMessageType = 'error'
      }
    },
    async retryReviewItems() {
      const confirmed = await requestConfirm({
        title: '重试当前筛选项',
        message: `确认重试「${this.reviewStatus === 'all' ? '全部状态' : this.reviewStatus}」筛选下的翻译项？`,
        details: this.reviewQuery.trim() ? `关键词：${this.reviewQuery.trim()}` : '会按当前类型和状态筛选批量创建重试作业。',
        confirmText: '开始重试',
      })
      if (!confirmed) return
      this.retryingItems = true
      try {
        const payload = {
          type: this.reviewType,
          provider: this.selectedProvider,
        }
        if (this.reviewStatus && this.reviewStatus !== 'all') payload.status = this.reviewStatus
        if (this.reviewQuery.trim()) payload.q = this.reviewQuery.trim()
        const resp = await api.retryTranslationItems(payload)
        const job = resp.data || {}
        this.currentJob = job
        this.selectedJob = job
        this.reviewMessage = `重试作业 #${job.id || ''} 已启动`
        this.reviewMessageType = 'success'
        if (job.id) this.startPolling(job.id)
        await this.loadJobs()
      } catch (error) {
        console.error('Failed to retry translation items:', error)
        this.reviewMessage = error.response?.data?.detail || '重试提交失败'
        this.reviewMessageType = 'error'
      } finally {
        this.retryingItems = false
      }
    },
    providerStatusLabel(key) {
      const state = this.stats.providers?.[key]
      if (!state) return '未检测'
      if (!state.enabled) return '未启用'
      return state.ready ? '可用' : '待配置'
    },
    providerLabel(key) {
      return {
        cache: '缓存',
        mapping: '映射',
        google_free: 'Google 免费接口',
        baidu: '百度翻译',
        deepl: 'DeepL',
        microsoft: 'Microsoft 翻译',
        ai: '智能兜底',
        openai_compatible: '智能兜底',
        translation_service: '批量源',
        import: '导入',
        manual: '人工',
      }[key] || key || ''
    },
    providerOrderLabel(order) {
      const labels = (order || []).map(key => this.providerLabel(key)).filter(Boolean)
      return labels.length ? labels.join(' -> ') : '未记录'
    },
    normalizeProvider(provider) {
      const key = provider === 'openai_compatible' ? 'ai' : provider
      return PROVIDER_META[key] ? key : 'google_free'
    },
    firstNetworkProvider(order) {
      if (!Array.isArray(order)) return ''
      const found = order.find(key => PROVIDER_META[key === 'openai_compatible' ? 'ai' : key])
      return found ? this.normalizeProvider(found) : ''
    },
    percentValue(item = {}) {
      const total = Number(item.total || 0)
      if (!total) return 0
      const translated = Number(item.translated || 0)
      return Math.max(0, Math.min(100, Math.round((translated / total) * 100)))
    },
    coveragePercent(item = {}) {
      return `${this.percentValue(item)}%`
    },
    formatNumber(value) {
      return new Intl.NumberFormat('zh-CN').format(Number(value || 0))
    },
    jobTypeLabel(type) {
      return {
        library_titles: '库内影片标题',
        workbench_retry: '工作台重试',
        metadata_names: '全部元数据名称',
        metadata_categories: '题材名称',
        metadata_series: '系列名称',
        metadata_makers: '厂商名称',
        metadata_labels: '厂牌名称',
        metadata_actresses: '演员名称',
      }[type] || type || '未知作业'
    },
    workbenchStatusLabel(status) {
      return {
        untranslated: '未翻译',
        machine_translated: '机翻',
        reviewed: '已校对',
        manual_edited: '人工修改',
        failed: '失败',
        invalid: '无效',
      }[status] || '未翻译'
    },
    workbenchStatusClass(status) {
      return `status-${status || 'untranslated'}`
    },
    statusLabel(status) {
      return {
        pending: '等待中',
        running: '运行中',
        paused: '已暂停',
        completed: '已完成',
        failed: '失败',
        idle: '空闲',
      }[status] || '空闲'
    },
    jobStatusClass(status) {
      return `status-${status || 'idle'}`
    },
    durationText(value) {
      if (value === null || value === undefined) return '—'
      const seconds = Math.max(0, Number(value) || 0)
      if (seconds < 60) return `${seconds}s`
      const minutes = Math.floor(seconds / 60)
      const rest = seconds % 60
      if (minutes < 60) return rest ? `${minutes}m ${rest}s` : `${minutes}m`
      const hours = Math.floor(minutes / 60)
      const minuteRest = minutes % 60
      return minuteRest ? `${hours}h ${minuteRest}m` : `${hours}h`
    },
    jobProgressValue(job = null) {
      const value = Number(job?.progress_percent || 0)
      if (!Number.isFinite(value)) return 0
      return Math.max(0, Math.min(100, Math.round(value)))
    },
    formatTime(value) {
      if (!value) return '—'
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return String(value)
      return date.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      })
    },
  },
}
</script>

<style scoped>
.translation-page {
  display: flex;
  flex-direction: column;
  gap: 10px;
  letter-spacing: 0;
}

.translation-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 2px 0 8px;
}

.translation-header h1,
.panel-header h2 {
  margin: 0;
  color: var(--text-primary);
  letter-spacing: 0;
}

.translation-header h1 {
  font-size: var(--type-page-title);
  line-height: 1.1;
  font-weight: 600;
  letter-spacing: 0;
}

.eyebrow {
  margin: 0 0 4px;
  color: var(--text-muted);
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.header-actions,
.panel-actions,
.panel-footer-actions,
.key-actions,
.mapping-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-actions,
.panel-actions {
  flex-wrap: wrap;
  justify-content: flex-end;
}

.btn-sm {
  min-height: 36px;
  padding: 7px 12px;
  font-size: 12px;
}

.muted,
.provider-row small,
.source-section-head span,
.history-row span,
.result-summary span,
.notice-row span {
  color: var(--text-secondary);
}

.segmented-control {
  display: grid;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 3px;
  padding: 3px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.045);
}

.segmented-control button {
  min-height: 32px;
  border: 0;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: background var(--motion-fast), color var(--motion-fast), box-shadow var(--motion-fast);
}

.segmented-control button:hover {
  background: var(--accent-bg);
  color: var(--text-primary);
}

.segmented-control button.active {
  background: rgba(255, 255, 255, 0.12);
  color: var(--text-primary);
  box-shadow: inset 0 0 0 1px var(--border-light), 0 4px 12px var(--black-20);
}

.workspace-panel {
  padding: 14px;
}

.panel-header {
  min-height: 36px;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
}

.panel-header h2 {
  font-size: var(--type-panel-title);
  line-height: 1.25;
  font-weight: 600;
  letter-spacing: 0;
}

.overview-grid,
.source-layout,
.history-layout {
  display: grid;
  grid-template-columns: minmax(0, 1.5fr) minmax(280px, 0.85fr);
  gap: 16px;
}

.overview-dashboard {
  display: grid;
  grid-template-columns: minmax(0, 1.3fr) minmax(320px, 0.8fr);
  grid-template-areas:
    "hero metadata"
    "signals metadata"
    "control control";
  gap: 14px;
}

.coverage-hero,
.metadata-overview,
.overview-signals,
.job-control-card {
  min-width: 0;
}

.coverage-hero,
.metadata-overview,
.signal-card,
.job-control-card {
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  background: rgba(255, 255, 255, 0.035);
}

.coverage-hero {
  grid-area: hero;
  min-height: 252px;
  padding: 18px;
  display: grid;
  grid-template-columns: minmax(180px, 0.36fr) minmax(0, 1fr);
  align-items: center;
  gap: 28px;
}

.coverage-donut {
  --coverage-angle: 0deg;
  --donut-progress: var(--translation-donut-progress, var(--accent));
  --donut-track: var(--translation-donut-track, rgba(var(--accent-rgb), 0.12));
  --donut-hole-bg: var(--translation-donut-hole-bg, rgba(255, 255, 255, 0.94));
  --donut-hole-border: var(--translation-donut-hole-border, rgba(29, 29, 31, 0.10));
  --donut-edge: var(--translation-donut-edge, var(--border-light));
  --donut-glow: var(--translation-donut-glow, rgba(var(--accent-rgb), 0.08));
  width: clamp(132px, 13vw, 160px);
  aspect-ratio: 1;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background:
    radial-gradient(circle at 50% 50%, transparent 60%, rgba(255, 255, 255, 0.24) 61%, transparent 62%),
    conic-gradient(var(--donut-progress) 0 var(--coverage-angle), var(--donut-track) var(--coverage-angle) 360deg);
  box-shadow: inset 0 0 0 1px var(--donut-edge), 0 18px 34px var(--donut-glow);
}

.coverage-donut div {
  width: 68%;
  aspect-ratio: 1;
  display: grid;
  place-items: center;
  align-content: center;
  border-radius: 50%;
  background: var(--donut-hole-bg);
  border: 1px solid var(--donut-hole-border);
  box-shadow: var(--glass-inner-shadow);
}

:global(:root[data-theme='dark']) {
  --translation-donut-track: rgba(255, 255, 255, 0.13);
  --translation-donut-hole-bg: #1C1C1E;
  --translation-donut-hole-border: rgba(255, 255, 255, 0.16);
  --translation-donut-edge: rgba(255, 255, 255, 0.18);
  --translation-donut-glow: rgba(0, 0, 0, 0.34);
}

.coverage-donut strong {
  color: var(--text-primary);
  font-size: clamp(28px, 4vw, 42px);
  font-weight: 650;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.coverage-donut span,
.overview-kicker,
.coverage-row-label span,
.signal-card small,
.overview-section-head small {
  color: var(--text-secondary);
  font-size: 12px;
}

.coverage-donut span {
  margin-top: 6px;
}

.skeleton-donut,
.skeleton-line,
.skeleton-track div,
.coverage-row--loading .coverage-percent {
  background: linear-gradient(90deg, var(--skeleton-base), var(--skeleton-highlight), var(--skeleton-base));
  background-size: 200% 100%;
  animation: apple-skeleton-shimmer 1.4s ease-in-out infinite;
}

.skeleton-donut {
  box-shadow: none;
}

.skeleton-line {
  height: 14px;
  border-radius: var(--radius-control);
}

.skeleton-line.large {
  width: min(260px, 100%);
  height: 42px;
  margin-top: 8px;
}

.skeleton-line.medium {
  width: min(210px, 86%);
  margin: 12px 0 17px;
}

.skeleton-track div {
  background-color: transparent;
}

.coverage-row--loading .coverage-percent {
  height: 14px;
  overflow: hidden;
  border-radius: var(--radius-control);
  color: transparent;
}

.coverage-hero-copy {
  min-width: 0;
}

.overview-kicker {
  display: block;
  margin-bottom: 6px;
  font-weight: 600;
}

.coverage-count {
  display: flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 8px;
  font-variant-numeric: tabular-nums;
}

.coverage-count strong {
  color: var(--text-primary);
  font-size: clamp(28px, 4.2vw, 44px);
  font-weight: 650;
  line-height: 1.02;
}

.coverage-count span {
  color: var(--text-secondary);
  font-size: 15px;
}

.coverage-hero-copy p {
  margin: 8px 0 16px;
  color: var(--text-secondary);
  font-size: 13px;
}

.overview-track {
  height: 10px;
  overflow: hidden;
  border-radius: var(--radius-control);
  background: rgba(var(--accent-rgb), 0.11);
}

.overview-track.compact {
  height: 7px;
}

.overview-track div {
  height: 100%;
  border-radius: inherit;
  background: var(--accent);
  transition: width 0.28s ease;
}

.metadata-overview {
  grid-area: metadata;
  padding: 16px;
}

.overview-section-head {
  margin-bottom: 14px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}

.overview-section-head strong {
  color: var(--text-primary);
  font-size: 24px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.coverage-row-list {
  display: grid;
  gap: 13px;
}

.coverage-row {
  display: grid;
  grid-template-columns: minmax(92px, 0.75fr) minmax(120px, 1fr) 44px;
  align-items: center;
  gap: 10px;
}

.coverage-row-label {
  min-width: 0;
}

.coverage-row-label strong {
  display: block;
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 500;
}

.coverage-row-label span {
  display: block;
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}

.coverage-percent {
  color: var(--text-primary);
  font-size: 12px;
  font-weight: 600;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.overview-signals {
  grid-area: signals;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}

.signal-card {
  min-height: 106px;
  padding: 13px;
  display: grid;
  align-content: center;
  gap: 4px;
}

.signal-card strong {
  color: var(--text-primary);
  font-size: 24px;
  font-weight: 600;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}

.signal-card small {
  line-height: 1.35;
}

.signal-card.quiet strong {
  color: var(--text-secondary);
}

.job-control-card {
  grid-area: control;
  padding: 15px;
  display: grid;
  gap: 14px;
}

.job-control-card.empty {
  background: rgba(255, 255, 255, 0.025);
}

.job-control-head,
.job-progress-label,
.job-control-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.job-control-head strong {
  display: block;
  color: var(--text-primary);
  font-size: 17px;
  font-weight: 600;
  line-height: 1.25;
}

.job-control-progress {
  display: grid;
  gap: 8px;
}

.job-progress-label {
  color: var(--text-secondary);
  font-size: 12px;
}

.job-progress-label strong {
  color: var(--text-primary);
  font-size: 13px;
  font-variant-numeric: tabular-nums;
}

.job-control-metrics {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.job-control-metrics div {
  min-height: 68px;
  padding: 10px 11px;
  display: grid;
  align-content: center;
  gap: 5px;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.04);
}

.job-control-metrics span,
.job-control-meta,
.job-error {
  color: var(--text-secondary);
  font-size: 12px;
}

.job-control-metrics strong {
  color: var(--text-primary);
  font-size: 17px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.job-control-metrics .danger strong,
.job-error {
  color: #ff6b78;
}

.job-control-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 14px;
}

.job-control-meta span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.job-error {
  padding: 9px 10px;
  border: 1px solid rgba(255, 80, 90, 0.18);
  border-radius: var(--radius-md);
  background: rgba(255, 80, 90, 0.08);
}

.job-control-actions {
  justify-content: flex-end;
  flex-wrap: wrap;
}

.recent-panel,
.source-section,
.result-summary {
  min-width: 0;
}

.result-summary {
  padding-left: 16px;
  border-left: 1px solid var(--border);
}

.recent-head strong,
.history-row strong,
.result-summary strong {
  font-weight: 500;
}

.compact-job-row,
.history-row {
  width: 100%;
  border: 0;
  border-bottom: 1px solid var(--border);
  background: transparent;
  color: var(--text-primary);
  cursor: pointer;
  text-align: left;
}

.compact-job-row {
  min-height: 52px;
  padding: 10px 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.compact-job-row span {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.compact-job-row small,
.history-row small {
  color: var(--text-secondary);
  white-space: nowrap;
}

.history-row {
  min-height: 58px;
  padding: 10px 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
}

.history-row div {
  display: grid;
  gap: 4px;
}

.history-row.active strong {
  color: var(--text-primary);
}

.notice-row {
  margin-bottom: 12px;
  padding: 10px 12px;
  display: grid;
  gap: 3px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.035);
}

.notice-row strong {
  color: var(--text-primary);
  font-weight: 500;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.field {
  display: grid;
  gap: 6px;
}

.field span {
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 500;
}

.input {
  width: 100%;
  min-height: 40px;
  padding: 8px 11px;
  border: 1px solid transparent;
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-primary);
  outline: none;
  font: inherit;
  transition: border-color 0.18s ease, background 0.18s ease;
}

.input:focus {
  border-color: var(--accent);
  background: rgba(255, 255, 255, 0.08);
}

.input:disabled {
  opacity: 0.72;
  cursor: not-allowed;
}

.check-row,
.mini-toggle {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  color: var(--text-primary);
  font-weight: 500;
}

.check-row input,
.mini-toggle input,
.provider-row input {
  width: 16px;
  height: 16px;
  accent-color: var(--accent);
}

.standalone {
  margin-top: 12px;
}

.boxed {
  min-height: 40px;
  padding: 8px 11px;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  background: rgba(255, 255, 255, 0.035);
}

.provider-list {
  margin-top: 14px;
  border-top: 1px solid var(--border);
}

.provider-row {
  min-height: 56px;
  padding: 10px 0;
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid var(--border);
}

.provider-row strong {
  display: block;
  margin-bottom: 3px;
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 500;
}

.provider-row:not(.enabled) {
  opacity: 0.62;
}

.provider-status,
.chain-pill,
.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 26px;
  padding: 4px 9px;
  border-radius: var(--radius-control);
  border: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 600;
  white-space: nowrap;
}

.chain-pill {
  max-width: min(520px, 100%);
  overflow: hidden;
  color: var(--text-primary);
  text-overflow: ellipsis;
}

.status-running,
.status-pending,
.status-paused {
  color: var(--badge-warning-text);
  background: var(--badge-warning-bg);
  border-color: rgba(245, 181, 80, 0.28);
}

.status-completed {
  color: var(--badge-success-text);
  background: var(--badge-success-bg);
  border-color: rgba(90, 200, 150, 0.28);
}

.status-failed {
  color: #ff6b78;
  background: rgba(255, 80, 90, 0.12);
  border-color: rgba(255, 80, 90, 0.22);
}

.status-untranslated {
  color: var(--text-secondary);
}

.status-machine_translated {
  color: var(--badge-warning-text);
  background: var(--badge-warning-bg);
  border-color: rgba(245, 181, 80, 0.28);
}

.status-reviewed,
.status-manual_edited {
  color: var(--badge-success-text);
  background: var(--badge-success-bg);
  border-color: rgba(90, 200, 150, 0.28);
}

.status-invalid {
  color: var(--text-secondary);
  background: rgba(255, 255, 255, 0.035);
}

.panel-footer-actions {
  margin-top: 16px;
  justify-content: flex-end;
}

.source-section + .source-section {
  padding-left: 16px;
  border-left: 1px solid var(--border);
}

.source-section-head {
  margin-bottom: 12px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.source-section-head strong {
  display: block;
  margin-bottom: 4px;
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 500;
}

.source-section-head span {
  display: block;
  font-size: 12px;
}

.source-settings {
  display: grid;
  gap: 10px;
}

.source-section {
  min-width: 0;
}

.test-textarea {
  min-height: 84px;
  resize: vertical;
}

.left {
  margin-top: 10px;
  justify-content: flex-start;
  flex-wrap: wrap;
}

.mapping-layout {
  display: grid;
  grid-template-columns: minmax(220px, 0.8fr) minmax(220px, 1fr) auto;
  align-items: end;
  gap: 14px;
}

.review-toolbar {
  display: grid;
  grid-template-columns: minmax(140px, 0.7fr) minmax(150px, 0.7fr) minmax(260px, 1.4fr) auto;
  align-items: end;
  gap: 12px;
}

.review-search-btn {
  min-height: 40px;
}

.review-stats {
  margin-top: 12px;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
}

.review-stats div {
  min-height: 50px;
  padding: 9px 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.035);
}

.review-stats strong {
  display: block;
  color: var(--text-primary);
  font-size: 15px;
  font-weight: 500;
}

.review-stats span {
  display: block;
  margin-top: 3px;
  color: var(--text-secondary);
  font-size: 11px;
}

.review-table {
  margin-top: 12px;
  border-top: 1px solid var(--border);
}

.review-head,
.review-row {
  display: grid;
  grid-template-columns: minmax(180px, 1.2fr) minmax(220px, 1.4fr) minmax(92px, 0.45fr) minmax(120px, 0.65fr) minmax(250px, 0.9fr);
  gap: 10px;
  align-items: center;
}

.review-head {
  min-height: 36px;
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 600;
}

.review-row {
  min-height: 74px;
  padding: 10px 0;
  border-top: 1px solid var(--border);
}

.review-source {
  min-width: 0;
  display: grid;
  gap: 4px;
}

.review-source strong {
  color: var(--text-primary);
  font-size: 13px;
  font-weight: 500;
  line-height: 1.35;
}

.review-source small,
.review-meta small,
.review-meta span {
  color: var(--text-secondary);
  font-size: 11px;
}

.review-edit {
  min-height: 54px;
  resize: vertical;
}

.review-meta {
  min-width: 0;
  display: grid;
  gap: 3px;
}

.review-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 6px;
}

.review-actions .danger {
  color: #ff6b78;
}

.review-pagination {
  margin-top: 12px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  flex-wrap: wrap;
  gap: 10px;
  color: var(--text-secondary);
  font-size: 12px;
}

.page-size-field {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.page-size-field :deep(.glass-select) {
  width: 82px;
}

.review-history-panel {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

.review-history-row {
  grid-template-columns: minmax(0, 1fr) auto;
}

.mapping-stat {
  min-height: 52px;
  display: grid;
  align-content: center;
  gap: 3px;
}

.mapping-stat strong {
  color: var(--text-primary);
  font-size: 16px;
  font-weight: 500;
}

.mapping-stat span {
  color: var(--text-secondary);
  font-size: 12px;
}

.import-button {
  position: relative;
  overflow: hidden;
}

.import-button input {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.history-list {
  min-width: 0;
}

.result-summary {
  display: grid;
  align-content: start;
  gap: 8px;
}

.result-summary strong {
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 500;
}

.empty-panel {
  min-height: 120px;
  display: grid;
  place-items: center;
  color: var(--text-secondary);
  border: 1px dashed var(--border);
  border-radius: var(--radius-lg);
}

.empty-panel.compact {
  min-height: 136px;
}

.message-line {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--border);
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-secondary);
  font-size: 12px;
}

.message-line.success {
  color: var(--badge-success-text);
  background: var(--badge-success-bg);
}

.message-line.error,
.error-text {
  color: #ff6b78;
}

@media (max-width: 920px) {
  .translation-header,
  .panel-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .header-actions,
  .panel-actions {
    width: 100%;
    justify-content: flex-start;
  }

  .overview-dashboard,
  .overview-dashboard {
    grid-template-columns: 1fr;
    grid-template-areas:
      "hero"
      "metadata"
      "signals"
      "control";
  }

  .segmented-control {
    grid-template-columns: repeat(6, max-content);
    overflow-x: auto;
    scrollbar-width: none;
  }

  .segmented-control::-webkit-scrollbar {
    display: none;
  }

  .segmented-control button {
    min-width: 88px;
    min-height: 38px;
  }

  .overview-grid,
  .source-layout,
  .history-layout,
  .form-grid,
  .review-toolbar,
  .review-head,
  .review-row,
  .mapping-layout {
    grid-template-columns: 1fr;
  }

  .review-stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .review-head {
    display: none;
  }

  .review-actions {
    justify-content: flex-start;
  }

  .result-summary,
  .source-section + .source-section {
    padding-left: 0;
    border-left: 0;
    padding-top: 14px;
    border-top: 1px solid var(--border);
  }

  .overview-signals {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .job-control-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 560px) {
  .translation-page {
    gap: 10px;
  }

  .workspace-panel {
    padding: 12px;
  }

  .translation-header h1 {
    font-size: var(--type-page-title-mobile);
    line-height: 1.1;
  }

  .coverage-hero {
    grid-template-columns: 1fr;
    justify-items: center;
    text-align: center;
    padding: 16px;
    gap: 18px;
  }

  .coverage-hero-copy {
    width: 100%;
  }

  .coverage-count {
    justify-content: center;
  }

  .coverage-row {
    grid-template-columns: 1fr 42px;
  }

  .coverage-row .overview-track {
    grid-column: 1 / -1;
    grid-row: 2;
  }

  .overview-signals {
    grid-template-columns: 1fr;
  }

  .job-control-head,
  .job-control-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .job-control-head .status-pill,
  .job-control-actions .btn {
    width: 100%;
    justify-content: center;
  }

  .provider-row {
    grid-template-columns: auto minmax(0, 1fr);
    min-height: 70px;
  }

  .provider-status {
    grid-column: 2;
    justify-self: start;
  }

  .history-row,
  .compact-job-row {
    grid-template-columns: 1fr;
    align-items: start;
  }

  .header-actions,
  .panel-actions,
  .panel-footer-actions,
  .key-actions,
  .review-actions,
  .mapping-actions {
    align-items: stretch;
  }

  .header-actions .btn,
  .panel-actions .btn,
  .panel-footer-actions .btn,
  .key-actions .btn,
  .review-actions .btn,
  .review-search-btn,
  .mapping-actions .btn,
  .job-control-actions .btn,
  .mapping-actions .import-button {
    width: 100%;
    justify-content: center;
  }
}
</style>

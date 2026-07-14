<template>
  <section class="source-panel apple-reveal" aria-label="下载源管理" :aria-busy="loading">
    <div class="source-toolbar apple-surface">
      <div class="source-toolbar-copy">
        <strong>下载源</strong>
        <span>默认自动优选 · {{ enabledSourceCount }} 个已启用</span>
      </div>
      <div class="source-toolbar-actions">
        <button
          class="source-icon-action"
          type="button"
          title="刷新下载源" aria-label="刷新下载源"
          :disabled="loading"
          @click="$emit('refresh')"
        >
          <svg :class="{ 'is-spinning': loading }" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
            <polyline points="23 4 23 10 17 10"/>
            <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/>
          </svg>
        </button>
        <button
          class="source-icon-action primary"
          type="button"
          title="新增下载源" aria-label="新增下载源"
          @click="$emit('create')"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
        </button>
      </div>
    </div>

    <div class="source-list apple-surface">
      <article
        v-for="builtin in snapshot.builtins"
        :key="builtin.id"
        class="source-row is-builtin"
        :data-source-id="builtin.id"
      >
        <div class="source-row-main">
          <span class="source-mark">{{ sourceTypeMark(builtin) }}</span>
          <div class="source-copy">
            <div class="source-title-line">
              <strong>{{ builtin.name || '在线 M3U8' }}</strong>
              <span>内置</span>
            </div>
            <div class="source-summary">
              <span>内置在线播放来源</span>
              <span>无需配置</span>
            </div>
          </div>
        </div>
        <div class="source-status-group">
          <span class="source-pill builtin">内置</span>
          <span class="source-pill enabled">可用</span>
        </div>
      </article>

      <article
        v-for="item in snapshot.sources"
        :key="item.id"
        class="source-row"
        :class="{ disabled: !item.enabled, busy: isBusy(item) }"
        :data-source-id="item.id"
        :aria-busy="isBusy(item)"
      >
        <div class="source-row-main">
          <span class="source-mark" :class="{ muted: !item.enabled }">{{ sourceTypeMark(item) }}</span>
          <div class="source-copy">
            <div class="source-title-line">
              <strong>{{ item.type === 'avdb' ? 'AVDB 公开库' : item.name }}</strong>
              <span>{{ sourceTypeLabel(item) }}</span>
            </div>
            <div v-if="item.type === 'torznab'" class="source-summary">
              <span>{{ sourceTypeLabel(item) }}</span>
              <span :title="item.base_url || ''">{{ sourceHost(item) }}</span>
            </div>
            <div v-else class="source-summary">
              <span>本地 PostgreSQL 磁力索引</span>
              <span>{{ avdbSummary(item) }}</span>
            </div>
          </div>
        </div>

        <div class="source-status-group">
          <span
            class="source-pill"
            :class="item.type === 'avdb' ? avdbLifecycle(item).tone : (item.enabled ? 'enabled' : 'muted')"
          >
            {{ item.type === 'avdb' ? avdbLifecycle(item).label : (item.enabled ? '已启用' : '已停用') }}
          </span>
        </div>

        <div v-if="item.type === 'torznab'" class="source-row-actions">
          <button
            class="source-icon-action compact"
            type="button"
            title="编辑下载源" aria-label="编辑下载源"
            :disabled="isBusy(item)"
            data-action="edit"
            @click="$emit('edit', item)"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
              <path d="M12 20h9"/><path d="M16.5 3.5a2.12 2.12 0 013 3L7 19l-4 1 1-4Z"/>
            </svg>
          </button>
          <button
            class="source-icon-action compact"
            type="button"
            :title="toggleTitle(item)" :aria-label="toggleTitle(item)"
            :disabled="isBusy(item)"
            data-action="toggle"
            @click="$emit('toggle', item)"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
              <path d="M18.36 6.64a9 9 0 11-12.73 0"/><line x1="12" y1="2" x2="12" y2="12"/>
            </svg>
          </button>
          <button
            class="source-icon-action compact danger"
            type="button"
            title="删除下载源" aria-label="删除下载源"
            :disabled="isBusy(item)"
            data-action="remove"
            @click="$emit('remove', item)"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
              <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6"/><path d="M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
            </svg>
          </button>
        </div>

        <div v-else-if="item.type === 'avdb'" class="source-row-actions">
          <button
            class="source-icon-action compact"
            type="button"
            :title="toggleTitle(item)" :aria-label="toggleTitle(item)"
            :disabled="avdbToggleDisabled(item)"
            data-action="toggle"
            @click="$emit('toggle', item)"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
              <path d="M18.36 6.64a9 9 0 11-12.73 0"/><line x1="12" y1="2" x2="12" y2="12"/>
            </svg>
          </button>
          <button
            v-if="canViewAvdbJob(item)"
            class="source-icon-action compact"
            type="button"
            title="查看 AVDB 同步作业" aria-label="查看 AVDB 同步作业"
            :disabled="isBusy(item)"
            data-action="view-job"
            @click="$emit('view-avdb-job')"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
              <path d="M3 12h4l2.5-7 5 14 2.5-7h4"/>
            </svg>
          </button>
          <button
            class="source-icon-action compact danger"
            type="button"
            title="移除 AVDB 来源" aria-label="移除 AVDB 来源"
            :disabled="isBusy(item) || !avdbStatusKnown(item)"
            data-action="remove"
            @click="$emit('remove', item)"
          >
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7">
              <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6"/><path d="M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
            </svg>
          </button>
        </div>

        <div v-if="item.type === 'avdb'" class="source-avdb-facts">
          <span><small>数据版本</small><strong>{{ avdbVersion(item) }}</strong></span>
          <span><small>索引记录</small><strong>{{ formatCount(avdbDetails(item).recordCount) }}</strong></span>
          <span><small>来源计数</small><strong>{{ avdbSourceCounts(item) || '—' }}</strong></span>
          <span><small>上次同步</small><strong>{{ avdbLastSync(item) }}</strong></span>
          <p v-if="avdbDetails(item).lastError" class="source-avdb-error" :title="avdbDetails(item).lastError">
            {{ avdbDetails(item).lastError }}
          </p>
        </div>
      </article>
    </div>

    <footer class="source-footer apple-surface" aria-live="polite">
      <span>{{ totalSourceCount }} 个来源 · {{ enabledSourceCount }} 个启用</span>
      <span v-if="loading">正在刷新来源状态…</span>
      <span v-else>启用的磁力来源会参与自动优选</span>
    </footer>

    <div
      v-if="editor.open"
      class="source-sheet-overlay downloader-sheet-overlay"
      @click.self="$emit('close-editor')"
    >
      <div class="source-sheet" role="dialog" aria-modal="true" aria-labelledby="source-editor-title">
        <header class="source-sheet-header">
          <div>
            <h2 id="source-editor-title">{{ editor.mode === 'new' ? '新增下载源' : '编辑下载源' }}</h2>
            <p>{{ editor.mode === 'new' ? '添加磁力索引或 AVDB 公开库' : (editor.draft?.name || '磁力索引') }}</p>
          </div>
          <button
            class="source-dialog-close"
            type="button"
            title="关闭编辑器" aria-label="关闭编辑器"
            @click="$emit('close-editor')"
          >×</button>
        </header>

        <div v-if="editor.draft" class="source-sheet-body">
          <section v-if="editor.mode === 'new'" class="source-sheet-section">
            <div class="source-section-title">
              <strong>来源类型</strong>
              <span>AVDB 是单例；磁力索引可添加多个实例。</span>
            </div>
            <div class="source-type-grid" role="group" aria-label="下载源类型">
              <button
                type="button"
                data-source-type="torznab"
                :class="{ active: editor.draft.type !== 'avdb' }"
                :aria-pressed="editor.draft.type !== 'avdb'"
                @click="selectSourceType('torznab')"
              >
                <strong>磁力索引</strong>
                <span>Prowlarr、Jackett 或通用 Torznab</span>
              </button>
              <button
                type="button"
                data-source-type="avdb"
                :class="{ active: editor.draft.type === 'avdb' }"
                :aria-pressed="editor.draft.type === 'avdb'"
                :disabled="avdbAlreadyAdded"
                @click="selectSourceType('avdb')"
              >
                <strong>AVDB 公开库</strong>
                <span>{{ avdbAlreadyAdded ? '已添加，不能重复添加' : '固定公开库，本地建立索引' }}</span>
              </button>
            </div>
          </section>

          <template v-if="isTorznabDraft">
            <section class="source-sheet-section">
              <div class="source-section-title">
                <strong>基础信息</strong>
                <span>名称、提供方与服务地址</span>
              </div>
              <div class="source-form-grid">
                <label>
                  名称
                  <input
                    class="input"
                    v-model="editor.draft.name"
                    autocomplete="off"
                    placeholder="家庭 Prowlarr"
                    :aria-invalid="Boolean(fieldErrors.name)"
                    aria-describedby="source-error-name"
                    @input="clearFieldError('name')"
                  />
                  <span v-if="fieldErrors.name" id="source-error-name" class="source-field-error">{{ fieldErrors.name }}</span>
                </label>
                <label>
                  提供方
                  <select class="input" v-model="editor.draft.kind">
                    <option v-for="option in kindOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                  </select>
                </label>
                <label class="wide-field">
                  服务地址
                  <input
                    class="input"
                    v-model="editor.draft.base_url"
                    type="url"
                    autocomplete="url"
                    placeholder="http://localhost:9696"
                    :aria-invalid="Boolean(fieldErrors.base_url)"
                    aria-describedby="source-error-base-url"
                    @input="clearFieldError('base_url')"
                  />
                  <span v-if="fieldErrors.base_url" id="source-error-base-url" class="source-field-error">{{ fieldErrors.base_url }}</span>
                </label>
              </div>
            </section>

            <section class="source-sheet-section">
              <div class="source-section-title">
                <strong>连接与查询</strong>
                <span>密钥、索引器、分类、上限与超时</span>
              </div>
              <div class="source-form-grid">
                <label class="wide-field">
                  API Key
                  <span class="source-secret-field">
                    <input
                      class="input"
                      v-model="editor.draft.api_key"
                      :type="showApiKey ? 'text' : 'password'"
                      autocomplete="new-password"
                      :placeholder="editor.draft.api_key_configured ? '留空不覆盖已有 API Key' : '输入 API Key'"
                      :aria-invalid="Boolean(fieldErrors.api_key)"
                      aria-describedby="source-error-api-key"
                      @input="clearFieldError('api_key')"
                    />
                    <button
                      class="source-key-visibility"
                      type="button"
                      :title="showApiKey ? '隐藏 API Key' : '显示 API Key'"
                      :aria-label="showApiKey ? '隐藏 API Key' : '显示 API Key'"
                      @click="showApiKey = !showApiKey"
                    >
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6">
                        <path d="M1 12s4-7 11-7 11 7 11 7-4 7-11 7S1 12 1 12Z"/><circle cx="12" cy="12" r="3"/>
                      </svg>
                    </button>
                  </span>
                  <span v-if="fieldErrors.api_key" id="source-error-api-key" class="source-field-error">{{ fieldErrors.api_key }}</span>
                </label>
                <label>
                  Indexer
                  <input class="input" v-model="editor.draft.indexer" placeholder="all 或索引器 ID" />
                </label>
                <label>
                  Categories
                  <input class="input" v-model="editor.draft.categories" placeholder="可留空；多个分类用逗号分隔" />
                </label>
                <label>
                  返回上限
                  <input
                    class="input"
                    v-model.number="editor.draft.limit"
                    type="number" min="1" max="100" step="1" inputmode="numeric"
                    :aria-invalid="Boolean(fieldErrors.limit)"
                    aria-describedby="source-error-limit"
                    @input="clearFieldError('limit')"
                  />
                  <span v-if="fieldErrors.limit" id="source-error-limit" class="source-field-error">{{ fieldErrors.limit }}</span>
                </label>
                <label>
                  超时（秒）
                  <input
                    class="input"
                    v-model.number="editor.draft.timeout"
                    type="number" min="1" max="60" step="1" inputmode="numeric"
                    :aria-invalid="Boolean(fieldErrors.timeout)"
                    aria-describedby="source-error-timeout"
                    @input="clearFieldError('timeout')"
                  />
                  <span v-if="fieldErrors.timeout" id="source-error-timeout" class="source-field-error">{{ fieldErrors.timeout }}</span>
                </label>
              </div>
              <label class="source-enable-option">
                <input type="checkbox" v-model="editor.draft.enabled" />
                <span>保存后启用此磁力来源</span>
              </label>
            </section>
          </template>

          <section v-else class="source-sheet-section source-avdb-intro">
            <div class="source-section-title">
              <strong>固定公开来源</strong>
              <span>AVDB 的上游地址由系统维护，不提供自定义仓库配置。</span>
            </div>
            <p>添加后会定期下载公开数据并在本地 PostgreSQL 建立磁力索引。首次同步可能耗费较长时间和较多磁盘空间。</p>
            <dl>
              <div><dt>启用门槛</dt><dd>首次同步完成且索引可用后</dd></div>
              <div><dt>当前本地索引</dt><dd>{{ editorAvdbAvailable ? '已有可用索引' : '尚不可用' }}</dd></div>
              <div><dt>移除行为</dt><dd>停止定时检查，但保留本地索引数据</dd></div>
            </dl>
          </section>

          <p v-if="editorError" class="source-editor-error" role="alert">{{ editorError }}</p>
        </div>

        <footer class="source-sheet-actions">
          <button class="btn btn-ghost" type="button" @click="$emit('close-editor')">取消</button>
          <button
            class="btn btn-primary source-editor-submit"
            type="button"
            :disabled="editorBusy || (isAvdbDraft && avdbAlreadyAdded)"
            @click="submitEditor"
          >{{ editorBusy ? '保存中…' : editorPrimaryLabel }}</button>
        </footer>
      </div>
    </div>
  </section>
</template>

<script>
import {
  createSourceDraft,
  sourceHost,
  sourceTypeLabel,
  sourceTypeMark,
  validateSourceDraft,
} from './sourcePresentation'
import {
  avdbSourceCountText,
  avdbState,
  formatAvdbCount,
  normalizeAvdbStatus,
} from './avdbPresentation'

const AVDB_STATUSES = new Set(['never', 'running', 'success', 'failed'])
const KIND_OPTIONS = [
  { value: 'prowlarr', label: 'Prowlarr' },
  { value: 'jackett', label: 'Jackett' },
  { value: 'torznab', label: '通用 Torznab' },
]

export default {
  name: 'IndexerSourcePanel',
  props: {
    snapshot: { type: Object, required: true },
    loading: { type: Boolean, default: false },
    busySourceId: { type: String, default: '' },
    editor: { type: Object, required: true },
    editorError: { type: String, default: '' },
    avdbStatus: { type: Object, default: () => ({}) },
  },
  emits: ['refresh', 'create', 'edit', 'toggle', 'remove', 'save-editor', 'close-editor', 'view-avdb-job'],
  data() {
    return {
      fieldErrors: {},
      kindOptions: KIND_OPTIONS,
      showApiKey: false,
    }
  },
  computed: {
    totalSourceCount() {
      const builtins = Array.isArray(this.snapshot?.builtins) ? this.snapshot.builtins : []
      const sources = Array.isArray(this.snapshot?.sources) ? this.snapshot.sources : []
      return builtins.length + sources.length
    },
    enabledSourceCount() {
      const builtins = Array.isArray(this.snapshot?.builtins) ? this.snapshot.builtins : []
      const sources = Array.isArray(this.snapshot?.sources) ? this.snapshot.sources : []
      return [...builtins, ...sources].filter(item => item?.enabled).length
    },
    avdbAlreadyAdded() {
      return Array.isArray(this.snapshot?.sources)
        && this.snapshot.sources.some(item => item?.type === 'avdb')
    },
    isAvdbDraft() {
      return this.editor?.mode === 'new' && this.editor?.draft?.type === 'avdb'
    },
    isTorznabDraft() {
      return !this.isAvdbDraft
    },
    editorAvdbAvailable() {
      return normalizeAvdbStatus(this.avdbStatus).available
    },
    editorBusy() {
      if (!this.editor?.open) return false
      const draftIsBusy = Boolean(this.editor.draft?.id) && this.busySourceId === this.editor.draft.id
      return draftIsBusy || (this.editor.mode === 'new' && this.busySourceId === 'new')
    },
    editorPrimaryLabel() {
      const defaultLabel = this.editor.mode === 'new' ? '保存并添加' : '保存更改'
      if (!this.isAvdbDraft) return defaultLabel
      return this.editorAvdbAvailable ? '添加来源' : '添加并前往首次同步'
    },
  },
  watch: {
    'editor.open'(open) {
      if (!open) return
      this.fieldErrors = {}
      this.showApiKey = false
    },
  },
  methods: {
    sourceHost,
    sourceTypeLabel,
    sourceTypeMark,
    formatCount: formatAvdbCount,
    isBusy(item) {
      return Boolean(item?.id) && this.busySourceId === item.id
    },
    avdbRaw(item) {
      return { ...(item || {}), ...(this.avdbStatus || {}) }
    },
    avdbStatusKnown(item) {
      return AVDB_STATUSES.has(this.avdbRaw(item).status)
    },
    avdbDetails(item) {
      return normalizeAvdbStatus(this.avdbRaw(item))
    },
    avdbLifecycle(item) {
      return avdbState(this.avdbRaw(item), { known: this.avdbStatusKnown(item) })
    },
    avdbSummary(item) {
      const details = this.avdbDetails(item)
      const state = this.avdbLifecycle(item)
      if (!this.avdbStatusKnown(item)) return '状态读取失败'
      if (state.code === 'syncing') return '正在更新本地索引'
      if (state.code === 'failed') return details.available ? '同步失败，上一版仍可用' : '上次同步失败'
      if (details.available) return `${this.formatCount(details.recordCount)} 条磁力索引`
      return '尚无可用索引'
    },
    avdbVersion(item) {
      const details = this.avdbDetails(item)
      return details.release || details.generation || '—'
    },
    avdbSourceCounts(item) {
      return avdbSourceCountText(this.avdbDetails(item).sourceCounts)
    },
    avdbLastSync(item) {
      const details = this.avdbDetails(item)
      return this.formatTime(details.lastCompletedAt || details.lastStartedAt || details.lastCheckedAt) || '尚未同步'
    },
    formatTime(value) {
      if (!value) return ''
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return String(value)
      const hours = String(date.getHours()).padStart(2, '0')
      const minutes = String(date.getMinutes()).padStart(2, '0')
      return `${date.getMonth() + 1}/${date.getDate()} ${hours}:${minutes}`
    },
    canViewAvdbJob(item) {
      return ['syncing', 'failed'].includes(this.avdbLifecycle(item).code)
    },
    avdbToggleDisabled(item) {
      if (this.isBusy(item) || !this.avdbStatusKnown(item)) return true
      return !item.enabled && !this.avdbDetails(item).available
    },
    toggleTitle(item) {
      if (item?.type === 'avdb' && !item.enabled && !this.avdbDetails(item).available) {
        return '首次同步完成后才能启用 AVDB'
      }
      return item?.enabled ? '停用下载源' : '启用下载源'
    },
    selectSourceType(type) {
      if (this.editor.mode !== 'new' || !this.editor.draft) return
      if (type === 'avdb' && this.avdbAlreadyAdded) return
      const next = createSourceDraft(type)
      for (const key of Object.keys(this.editor.draft)) delete this.editor.draft[key]
      Object.assign(this.editor.draft, next)
      this.fieldErrors = {}
      this.showApiKey = false
    },
    clearFieldError(field) {
      if (!this.fieldErrors[field]) return
      const next = { ...this.fieldErrors }
      delete next[field]
      this.fieldErrors = next
    },
    submitEditor() {
      if (!this.editor?.draft || this.editorBusy) return
      if (this.isAvdbDraft && this.avdbAlreadyAdded) return
      this.fieldErrors = validateSourceDraft(this.editor.draft)
      if (Object.keys(this.fieldErrors).length) return
      const { editor } = this
      this.$emit('save-editor', { ...editor.draft })
    },
  },
}
</script>

<style scoped>
.source-panel {
  display: grid;
  gap: 16px;
  min-width: 0;
  overflow-x: hidden;
}
.source-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px;
  border: 1px solid var(--glass-control-border);
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}
.source-toolbar-copy { min-width: 0; }
.source-toolbar-copy strong {
  display: block;
  color: var(--text-primary);
  font-size: 17px;
  font-weight: 700;
}
.source-toolbar-copy span {
  display: block;
  margin-top: 4px;
  color: var(--text-muted);
  font-size: var(--type-control);
}
.source-toolbar-actions,
.source-row-actions {
  display: flex;
  gap: 6px;
}
.source-icon-action,
.source-dialog-close,
.source-key-visibility {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  flex: 0 0 auto;
  border: 1px solid var(--glass-control-border);
  border-radius: 50%;
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  color: var(--text-primary);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  cursor: pointer;
  transition: transform var(--motion-standard), opacity var(--motion-fast);
}
.source-icon-action svg,
.source-key-visibility svg { width: 17px; height: 17px; }
.source-icon-action:hover:not(:disabled),
.source-dialog-close:hover:not(:disabled),
.source-key-visibility:hover:not(:disabled),
.source-icon-action:focus-visible:not(:disabled),
.source-dialog-close:focus-visible:not(:disabled),
.source-key-visibility:focus-visible:not(:disabled) {
  outline: none;
  transform: translateY(-1px);
  border-color: var(--glass-control-border-hover);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow-hover), var(--focus-ring);
}
.source-icon-action.primary {
  border-color: var(--glass-active-border);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--glass-active-material);
  box-shadow: var(--glass-active-shadow);
}
.source-icon-action.compact { width: 44px; height: 44px; }
.source-icon-action.danger {
  border-color: var(--badge-error-border);
  background: var(--surface-specular-edge), var(--surface-noise), var(--badge-error-bg);
  color: var(--badge-error-text);
}
.source-icon-action:disabled,
.source-dialog-close:disabled { opacity: 0.38; cursor: not-allowed; }
.source-list { display: grid; overflow: hidden; }
.source-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto auto;
  align-items: center;
  gap: 14px;
  min-width: 0;
  min-height: 86px;
  padding: 14px 16px;
  border: 1px solid var(--hairline);
  background: var(--card-2);
  box-shadow: none;
  transition: opacity var(--motion-fast), border-color var(--motion-fast);
}
.source-row:hover { border-color: var(--hairline-strong); background: var(--card-hover); box-shadow: var(--shadow-card); }
.source-row.disabled { opacity: 0.72; }
.source-row.busy { opacity: 0.58; }
.source-row-main { display: flex; align-items: center; gap: 13px; min-width: 0; }
.source-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 46px;
  height: 46px;
  flex: 0 0 auto;
  border: 1px solid var(--glass-control-border);
  border-radius: 14px;
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  color: var(--text-primary);
  font-size: var(--type-control);
  font-weight: 800;
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}
.source-mark.muted { background: var(--card); color: var(--text-muted); }
.source-copy { min-width: 0; }
.source-title-line { display: flex; align-items: baseline; gap: 8px; min-width: 0; }
.source-title-line strong {
  min-width: 0;
  color: var(--text-primary);
  font-size: var(--type-card-title);
  font-weight: 700;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.source-title-line span { flex: 0 0 auto; color: var(--text-muted); font-size: var(--type-caption); }
.source-summary { display: flex; gap: 10px; margin-top: 6px; min-width: 0; color: var(--text-muted); font-size: var(--type-caption); }
.source-summary span { min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.source-summary span + span::before {
  content: '';
  display: inline-block;
  width: 3px;
  height: 3px;
  margin: 0 9px 2px 0;
  border-radius: 50%;
  background: var(--text-muted);
}
.source-status-group { display: flex; justify-content: flex-end; }
.source-pill {
  display: inline-flex;
  align-items: center;
  min-height: 24px;
  padding: 3px 9px;
  border: 1px solid var(--badge-pending-border);
  border-radius: 999px;
  background: var(--surface-specular-edge), var(--surface-noise), var(--badge-pending-bg);
  color: var(--badge-pending-text);
  font-size: var(--type-micro);
  font-weight: 700;
  white-space: nowrap;
}
.source-pill.enabled,
.source-pill.builtin,
.source-pill.is-success {
  border-color: var(--badge-success-border);
  background: var(--surface-specular-edge), var(--surface-noise), var(--badge-success-bg);
  color: var(--badge-success-text);
}
.source-pill.is-running { border-color: var(--glass-active-border); color: var(--accent); }
.source-pill.is-warn {
  border-color: var(--badge-warning-border);
  background: var(--surface-specular-edge), var(--surface-noise), var(--badge-warning-bg);
  color: var(--badge-warning-text);
}
.source-pill.is-failed {
  border-color: var(--badge-error-border);
  background: var(--surface-specular-edge), var(--surface-noise), var(--badge-error-bg);
  color: var(--badge-error-text);
}
.source-avdb-facts {
  grid-column: 1 / -1;
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 1px;
  min-width: 0;
  overflow: hidden;
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  background: var(--hairline);
}
.source-avdb-facts > span { min-width: 0; padding: 9px 11px; background: var(--card); }
.source-avdb-facts small,
.source-avdb-facts strong { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.source-avdb-facts small { color: var(--text-muted); font-size: var(--type-micro); }
.source-avdb-facts strong { margin-top: 3px; color: var(--text-secondary); font-size: var(--type-caption); }
.source-avdb-error {
  grid-column: 1 / -1;
  margin: 0;
  padding: 9px 11px;
  background: var(--surface-specular-edge), var(--surface-noise), var(--badge-error-bg);
  color: var(--badge-error-text);
  font-size: var(--type-caption);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.source-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  padding: 14px 16px;
  color: var(--text-muted);
  font-size: var(--type-caption);
}
.source-sheet-overlay {
  position: fixed;
  inset: 0;
  z-index: var(--z-modal);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding: 20px;
  background: var(--surface-scrim);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}
.source-sheet {
  display: flex;
  flex-direction: column;
  width: min(720px, 100%);
  max-height: min(820px, calc(100vh - 48px));
  min-width: 0;
  padding: 18px;
  border: 1px solid var(--hairline);
  border-radius: 20px;
  background: var(--card);
  box-shadow: var(--shadow-sheet);
}
.source-sheet-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 14px; }
.source-sheet-header h2 { margin: 0; color: var(--text-primary); font-size: var(--type-panel-title); }
.source-sheet-header p { margin: 4px 0 0; color: var(--text-muted); font-size: var(--type-control); }
.source-dialog-close { font-size: var(--type-workbench-title); }
.source-sheet-body { display: grid; gap: 14px; min-height: 0; overflow: auto; overflow-x: hidden; padding-right: 4px; }
.source-sheet-section {
  display: grid;
  gap: 12px;
  min-width: 0;
  padding: 14px;
  border: 1px solid var(--glass-control-border);
  border-radius: 18px;
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}
.source-section-title strong { display: block; color: var(--text-primary); font-size: var(--type-body); }
.source-section-title span { display: block; margin-top: 4px; color: var(--text-muted); font-size: var(--type-caption); }
.source-type-grid,
.source-form-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; min-width: 0; }
.source-type-grid button {
  display: grid;
  gap: 5px;
  min-height: 70px;
  min-width: 0;
  padding: 12px;
  border: 1px solid var(--glass-control-border);
  border-radius: var(--radius-sm);
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  color: var(--text-secondary);
  text-align: left;
  cursor: pointer;
}
.source-type-grid button.active { border-color: var(--glass-active-border); background: var(--surface-specular-edge-strong), var(--surface-noise), var(--glass-active-material); }
.source-type-grid button:focus-visible { outline: none; box-shadow: var(--focus-ring); }
.source-type-grid button:disabled { opacity: 0.45; cursor: not-allowed; }
.source-type-grid strong { color: var(--text-primary); font-size: var(--type-control); }
.source-type-grid span { color: var(--text-muted); font-size: var(--type-caption); line-height: 1.45; }
.source-form-grid label {
  display: grid;
  gap: 6px;
  min-width: 0;
  color: var(--text-secondary);
  font-size: var(--type-caption);
}
.source-form-grid .wide-field { grid-column: 1 / -1; }
.source-form-grid .input { width: 100%; min-width: 0; min-height: 44px; }
.source-field-error,
.source-editor-error { color: var(--badge-error-text); font-size: var(--type-caption); }
.source-editor-error {
  margin: 0;
  padding: 10px 12px;
  border: 1px solid var(--badge-error-border);
  border-radius: var(--radius-sm);
  background: var(--surface-specular-edge), var(--surface-noise), var(--badge-error-bg);
}
.source-secret-field { position: relative; display: block; min-width: 0; }
.source-secret-field .input { padding-right: 48px; }
.source-key-visibility { position: absolute; top: 0; right: 0; border-color: transparent; background: transparent; box-shadow: none; }
.source-enable-option { display: inline-flex; align-items: center; gap: 8px; color: var(--text-secondary); font-size: var(--type-caption); }
.source-enable-option input { width: 20px; height: 20px; }
.source-avdb-intro p { margin: 0; color: var(--text-secondary); font-size: var(--type-control); line-height: 1.65; }
.source-avdb-intro dl { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); margin: 0; border: 1px solid var(--hairline); }
.source-avdb-intro dl > div { min-width: 0; padding: 10px; border-right: 1px solid var(--hairline); }
.source-avdb-intro dl > div:last-child { border-right: none; }
.source-avdb-intro dt { color: var(--text-muted); font-size: var(--type-micro); }
.source-avdb-intro dd { margin: 4px 0 0; color: var(--text-primary); font-size: var(--type-caption); line-height: 1.45; }
.source-sheet-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 14px; }
.source-sheet-actions .btn { min-height: 44px; }
.is-spinning { animation: source-spin 0.9s linear infinite; }
@keyframes source-spin { to { transform: rotate(360deg); } }

@media (max-width: 768px) {
  .source-row { grid-template-columns: minmax(0, 1fr) auto; align-items: start; }
  .source-row-main { grid-column: 1 / -1; }
  .source-status-group { justify-content: flex-start; }
  .source-row-actions { grid-column: 2; grid-row: 2; flex-wrap: wrap; justify-content: flex-end; }
  .source-avdb-facts { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .source-sheet { width: 100%; max-height: calc(100vh - 40px); }
}
@media (max-width: 560px) {
  .source-toolbar { align-items: flex-start; }
  .source-toolbar-actions { flex: 0 0 auto; }
  .source-row { grid-template-columns: minmax(0, 1fr); }
  .source-status-group,
  .source-row-actions { grid-column: 1; grid-row: auto; justify-content: flex-start; }
  .source-footer { align-items: flex-start; flex-direction: column; }
  .source-sheet-overlay { padding: 8px; }
  .source-sheet { max-height: calc(100vh - 16px); padding: 14px; }
  .source-type-grid,
  .source-form-grid,
  .source-avdb-intro dl { grid-template-columns: 1fr; }
  .source-form-grid .wide-field { grid-column: auto; }
  .source-avdb-intro dl > div { border-right: none; border-bottom: 1px solid var(--hairline); }
  .source-avdb-intro dl > div:last-child { border-bottom: none; }
  .source-sheet-actions { display: grid; grid-template-columns: 1fr 1fr; }
}
</style>

<template>
  <div v-if="open" class="overlay" @click.self="close">
    <div class="add-sheet" role="dialog" aria-modal="true" aria-label="添加下载">
      <div class="sheet-head">
        <h2>添加下载</h2>
        <button class="icon-btn" type="button" aria-label="关闭" @click="close">✕</button>
      </div>

      <!-- 下载器选择 / 115 锁死 -->
      <div class="downloader-row">
        <label class="field-label">下载器</label>
        <div v-if="locked" class="locked-downloader" title="115 网盘内只能用 115 离线">
          <span class="lock-dot">●</span>{{ lockedLabel }}
          <span class="lock-hint">已锁定</span>
        </div>
        <select v-else v-model="selectedDownloaderId" class="downloader-select">
          <option v-for="client in selectableDownloaders" :key="client.id" :value="client.id">
            {{ client.name || client.type }}
          </option>
        </select>
        <div v-if="locked && quota" class="quota-chip" :class="{ low: quota.remain <= 0 }">
          本月剩余 <strong>{{ quota.remain }}</strong> / {{ quota.total }} 个离线配额
        </div>
      </div>

      <textarea
        v-model="magnetInput"
        class="magnet-textarea"
        :placeholder="placeholder"
        rows="7"
      ></textarea>

      <div class="parse-summary">
        <div class="summary-item"><strong>{{ inputLineCount }}</strong><span>输入行</span></div>
        <div class="summary-item success"><strong>{{ parsed.length }}</strong><span>可添加</span></div>
        <div class="summary-item warning"><strong>{{ duplicateCount }}</strong><span>重复</span></div>
        <div class="summary-item danger"><strong>{{ invalidLines.length }}</strong><span>无效</span></div>
      </div>

      <div class="sheet-actions">
        <button class="ghost-btn" type="button" :disabled="!hasInput && !hasResults" @click="clearAll">清空</button>
        <button class="ghost-btn" type="button" :disabled="!hasInput" @click="parse">解析</button>
        <button class="primary-btn" type="button" :disabled="busy || !pendingCount" @click="addAll">
          {{ busy ? '添加中…' : (pendingCount ? `添加全部 (${pendingCount})` : '添加全部') }}
        </button>
      </div>

      <div v-if="parsed.length" class="result-list">
        <div v-for="(mag, idx) in parsed" :key="mag.hash + idx" class="result-row" :class="mag.status">
          <div class="result-main">
            <div class="result-name">{{ mag.name || '未命名磁力任务' }}</div>
            <div class="result-hash">{{ mag.hash }}</div>
          </div>
          <span v-if="mag.status === 'added'" class="pill success">已添加</span>
          <span v-else-if="mag.status === 'failed'" class="pill danger" :title="mag.error">失败</span>
          <span v-else-if="mag.status === 'adding'" class="pill">添加中</span>
          <button
            v-else
            class="ghost-btn sm"
            type="button"
            :disabled="busy"
            @click="addOne(mag)"
          >添加</button>
        </div>
      </div>

      <div v-if="invalidLines.length" class="invalid-list">
        <div class="invalid-head">需要检查的行 · {{ invalidLines.length }}</div>
        <div v-for="item in invalidLines" :key="item.index" class="invalid-row">
          <span class="invalid-idx">第 {{ item.index }} 行</span>
          <span class="invalid-text">{{ item.text }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import api from '../../api'
import { ElMessage } from '../../utils/message.js'
import { requestConfirm } from '../../utils/confirmDialog'
import { parseMagnetInput, countInputLines } from './magnetParse'

const NATIVE_115_LABEL = '115 Open（原生）'

export default {
  name: 'AddDownloadSheet',
  props: {
    open: { type: Boolean, default: false },
    // '' = downloader selectable; 'open115' = locked to native 115 offline
    lockedDownloaderType: { type: String, default: '' },
    // 115 offline target folder (the folder being browsed)
    defaultCid: { type: String, default: '0' },
  },
  emits: ['close', 'added'],
  data() {
    return {
      magnetInput: '',
      parsed: [],
      invalidLines: [],
      duplicateCount: 0,
      downloaders: [],
      selectedDownloaderId: '',
      quota: null,
      busy: false,
    }
  },
  computed: {
    locked() {
      return this.lockedDownloaderType === 'open115'
    },
    lockedLabel() {
      return NATIVE_115_LABEL
    },
    selectableDownloaders() {
      return this.downloaders.filter(client => client.enabled)
    },
    hasInput() {
      return Boolean(this.magnetInput.trim())
    },
    hasResults() {
      return this.parsed.length > 0 || this.invalidLines.length > 0 || this.duplicateCount > 0
    },
    inputLineCount() {
      return countInputLines(this.magnetInput)
    },
    pendingCount() {
      return this.parsed.filter(mag => mag.status !== 'added' && mag.status !== 'adding').length
    },
    placeholder() {
      return this.locked
        ? 'magnet:?xt=urn:btih:... （离线下载到当前 115 目录）\n每行一个链接'
        : 'magnet:?xt=urn:btih:...&dn=example-title\n每行一个链接'
    },
  },
  watch: {
    open(value) {
      if (value) this.onOpen()
    },
  },
  methods: {
    async onOpen() {
      this.resetResults()
      this.magnetInput = ''
      if (this.locked) {
        this.loadQuota()
      } else {
        await this.loadDownloaders()
      }
    },
    async loadDownloaders() {
      try {
        const { data } = await api.listDownloaders()
        this.downloaders = (data.clients || []).map(client => ({ ...client }))
        const fallback = this.selectableDownloaders[0]?.id || ''
        this.selectedDownloaderId = data.default_id && this.selectableDownloaders.some(c => c.id === data.default_id)
          ? data.default_id
          : fallback
      } catch {
        this.downloaders = []
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
    resetResults() {
      this.parsed = []
      this.invalidLines = []
      this.duplicateCount = 0
    },
    parse() {
      const { parsed, duplicates, invalid } = parseMagnetInput(this.magnetInput)
      this.parsed = parsed.map(mag => ({ ...mag, status: 'idle', error: '' }))
      this.duplicateCount = duplicates
      this.invalidLines = invalid
    },
    async clearAll() {
      if (this.hasInput || this.hasResults) {
        const ok = await requestConfirm({
          title: '清空',
          message: '确认清空当前输入和解析结果？',
          details: '只会清空面板内容，不影响已经添加的任务。',
          confirmText: '清空',
          tone: 'danger',
        })
        if (!ok) return
      }
      this.magnetInput = ''
      this.resetResults()
    },
    async addOne(mag) {
      if (this.busy) return
      this.busy = true
      try {
        await this.submit([mag])
      } finally {
        this.busy = false
        this.afterAdd()
      }
    },
    async addAll() {
      const pending = this.parsed.filter(mag => mag.status !== 'added')
      if (!pending.length) return
      this.busy = true
      try {
        await this.submit(pending)
      } finally {
        this.busy = false
        this.afterAdd()
      }
    },
    async submit(items) {
      if (this.locked) {
        await this.submitOffline115(items)
      } else {
        await this.submitDownloader(items)
      }
    },
    async submitOffline115(items) {
      items.forEach(mag => { mag.status = 'adding' })
      try {
        const { data } = await api.addOpen115Offline({
          urls: items.map(mag => mag.magnet),
          cid: this.defaultCid || '0',
        })
        const addedHashes = new Set((data.added || []).map(row => String(row.info_hash || '').toLowerCase()))
        const skipped = new Map((data.skipped || []).map(row => [row.url, row.reason]))
        items.forEach(mag => {
          if (addedHashes.has(mag.hash.toLowerCase())) {
            mag.status = 'added'
          } else if (skipped.has(mag.magnet)) {
            mag.status = 'failed'
            mag.error = skipped.get(mag.magnet)
          } else {
            mag.status = 'added' // accepted but hash not echoed back
          }
        })
        if (data.quota) this.quota = data.quota
        ElMessage.success(`已添加 ${data.added?.length ?? items.length} 个离线任务`)
        this.$emit('added', data.added?.length ?? items.length)
      } catch (e) {
        items.forEach(mag => { mag.status = 'failed'; mag.error = '添加失败' })
        ElMessage.error('115 离线添加失败')
      }
    },
    async submitDownloader(items) {
      let okCount = 0
      for (const mag of items) {
        mag.status = 'adding'
        try {
          await api.createDownload({
            content_id: mag.hash.slice(0, 12),
            title: mag.name || '磁力下载',
            magnet: mag.magnet,
            downloader_id: this.selectedDownloaderId || '',
          })
          mag.status = 'added'
          okCount += 1
        } catch {
          mag.status = 'failed'
          mag.error = '添加失败'
        }
      }
      if (okCount) {
        ElMessage.success(`已添加 ${okCount} 个下载任务`)
        this.$emit('added', okCount)
      }
    },
    afterAdd() {
      // 持续添加：清空输入框，保留结果状态，面板不关闭，方便继续粘贴下一批。
      this.magnetInput = ''
    },
    close() {
      this.$emit('close')
    },
  },
}
</script>

<style scoped>
.overlay { position: fixed; inset: 0; z-index: var(--z-confirm); background: var(--surface-scrim, var(--scrim)); display: flex; align-items: center; justify-content: center; padding: 24px; }

.add-sheet {
  width: min(560px, 94vw);
  max-height: 88vh;
  overflow-y: auto;
  background: var(--card);
  border: 1px solid var(--glass-edge);
  border-radius: var(--radius-sheet);
  box-shadow: var(--shadow-sheet);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.sheet-head { display: flex; align-items: center; justify-content: space-between; }
.sheet-head h2 { margin: 0; font-size: var(--type-panel-title); color: var(--text-primary); }
.icon-btn { width: 32px; height: 32px; border-radius: 50%; border: 1px solid var(--hairline); background: var(--card); color: var(--text-secondary); cursor: pointer; }
.icon-btn:hover { background: var(--card-hover); color: var(--text-primary); }

.downloader-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.field-label { font-size: var(--type-caption); color: var(--text-muted); font-weight: 600; }
.downloader-select { flex: 0 1 220px; background: var(--surface-input, var(--card-2)); border: 1px solid var(--hairline); border-radius: var(--radius-control); padding: 7px 10px; color: var(--text-primary); font-size: var(--type-control); outline: none; }
.downloader-select:focus { border-color: var(--accent); }
.locked-downloader { display: inline-flex; align-items: center; gap: 6px; padding: 7px 12px; border: 1px solid var(--hairline); border-radius: var(--radius-control); background: var(--card-2); color: var(--text-secondary); font-size: var(--type-control); }
.lock-dot { color: var(--accent); font-size: var(--type-micro); }
.lock-hint { color: var(--text-muted); font-size: var(--type-micro); }
.quota-chip { margin-left: auto; font-size: var(--type-caption); color: var(--text-secondary); }
.quota-chip strong { color: var(--text-primary); }
.quota-chip.low strong { color: var(--badge-error-text); }

.magnet-textarea {
  width: 100%;
  min-height: 150px;
  resize: vertical;
  background: var(--surface-input, var(--card-2));
  border: 1px solid var(--hairline);
  border-radius: var(--radius-md);
  padding: 12px;
  color: var(--text-primary);
  font-family: var(--font-mono);
  font-size: var(--type-control);
  line-height: 1.6;
  outline: none;
}
.magnet-textarea:focus { border-color: var(--accent); }

.parse-summary { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
.summary-item { padding: 10px; border: 1px solid var(--hairline); border-radius: var(--radius-md); background: var(--card); text-align: center; }
.summary-item strong { display: block; font-size: var(--type-section-title); color: var(--text-primary); line-height: 1; }
.summary-item span { display: block; margin-top: 5px; font-size: var(--type-micro); color: var(--text-muted); font-weight: 600; }
.summary-item.success { background: var(--surface-specular-edge), var(--surface-noise), var(--badge-success-bg); border-color: var(--badge-success-border); }
.summary-item.warning { background: var(--surface-specular-edge), var(--surface-noise), var(--badge-warning-bg); border-color: var(--badge-warning-border); }
.summary-item.danger { background: var(--surface-specular-edge), var(--surface-noise), var(--badge-error-bg); border-color: var(--badge-error-border); }

.sheet-actions { display: flex; justify-content: flex-end; gap: 8px; }
.ghost-btn { background: var(--card-2); border: 1px solid var(--hairline); border-radius: var(--radius-control); padding: 8px 16px; color: var(--text-primary); font-size: var(--type-control); cursor: pointer; }
.ghost-btn:hover:not(:disabled) { background: var(--card-hover); }
.ghost-btn:disabled { opacity: .45; cursor: not-allowed; }
.ghost-btn.sm { padding: 5px 12px; font-size: var(--type-caption); }
.primary-btn { background: var(--accent); border: none; border-radius: var(--radius-control); padding: 8px 18px; color: var(--text-on-accent-solid); font-size: var(--type-control); cursor: pointer; }
.primary-btn:disabled { opacity: .5; cursor: not-allowed; }

.result-list { display: flex; flex-direction: column; gap: 6px; max-height: 260px; overflow-y: auto; }
.result-row { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border: 1px solid var(--hairline); border-radius: var(--radius-md); background: var(--card-2); }
.result-row.added { background: var(--surface-specular-edge), var(--surface-noise), var(--badge-success-bg); border-color: var(--badge-success-border); }
.result-row.failed { border-color: var(--badge-error-border); }
.result-main { min-width: 0; flex: 1; }
.result-name { font-size: var(--type-body); color: var(--text-primary); font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.result-hash { font-family: var(--font-mono); font-size: var(--type-micro); color: var(--text-muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.pill { flex: 0 0 auto; padding: 3px 9px; border-radius: var(--radius-xs); font-size: var(--type-micro); font-weight: 700; border: 1px solid var(--hairline); color: var(--text-muted); background: var(--card); }
.pill.success { color: var(--badge-success-text); border-color: var(--badge-success-border); }
.pill.danger { color: var(--badge-error-text); border-color: var(--badge-error-border); }

.invalid-list { display: flex; flex-direction: column; gap: 6px; padding: 12px; border: 1px solid var(--badge-warning-border); border-radius: var(--radius-md); }
.invalid-head { font-size: var(--type-caption); color: var(--badge-warning-text); font-weight: 700; }
.invalid-row { display: grid; grid-template-columns: 64px 1fr; gap: 8px; font-size: var(--type-caption); color: var(--text-secondary); }
.invalid-idx { color: var(--text-primary); }
.invalid-text { font-family: var(--font-mono); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

@media (max-width: 768px) {
  .overlay { padding: 0; align-items: flex-end; }
  .add-sheet { width: 100%; max-height: 92vh; border-radius: var(--radius-sheet) var(--radius-sheet) 0 0; }
  .parse-summary { grid-template-columns: repeat(2, 1fr); }
}
</style>

<template>
  <div class="parse-page page-shell page-shell--standard">
    <header class="parse-hero">
      <div class="hero-kicker">批量磁链工作台</div>
      <h1>磁链解析</h1>
      <p class="page-desc">把散落的磁力链接整理成可投递的下载任务。</p>
    </header>

    <section class="parse-console" aria-label="磁链解析工具台">
      <div class="console-head">
        <div>
          <h2>批量输入</h2>
          <p>每行一个链接，解析时会自动过滤重复项并标出异常行。</p>
        </div>
        <button class="btn btn-ghost clear-input-btn" type="button" :disabled="!hasInput && !hasResults" @click="clearAll">清空</button>
      </div>

      <textarea
        v-model="magnetInput"
        class="input parse-textarea"
        placeholder="magnet:?xt=urn:btih:ABC123...&dn=example-title&#10;magnet:?xt=urn:btih:DEF456..."
        rows="8"
      ></textarea>

      <div class="parse-summary" aria-label="解析摘要">
        <div class="summary-item">
          <strong>{{ inputLineCount }}</strong>
          <span>输入行</span>
        </div>
        <div class="summary-item success">
          <strong>{{ parsedMagnets.length }}</strong>
          <span>可添加</span>
        </div>
        <div class="summary-item warning">
          <strong>{{ duplicateCount }}</strong>
          <span>重复</span>
        </div>
        <div class="summary-item danger">
          <strong>{{ invalidLines.length }}</strong>
          <span>无效</span>
        </div>
      </div>

      <div class="parse-actions">
        <button class="btn btn-ghost" type="button" :disabled="loading || !hasInput" @click="parseMagnets">
          {{ loading ? '解析中...' : '解析链接' }}
        </button>
        <button class="btn btn-primary" type="button" :disabled="batchLoading || !parsedMagnets.length" @click="downloadAllMagnets">
          <span v-if="batchLoading" class="spinner"></span>
          <span v-else>添加全部</span>
        </button>
      </div>
    </section>

    <section v-if="parsedMagnets.length > 0" class="result-section">
      <div class="magnets-card av-card">
        <div class="magnets-header">
          <div>
            <h2>解析结果</h2>
            <p>{{ resultSummary }}</p>
          </div>
          <button class="btn btn-ghost clear-results-btn" type="button" @click="clearResults">清除结果</button>
        </div>
        <div class="magnets-list">
          <div v-for="(mag, idx) in parsedMagnets" :key="mag.hash + idx" class="magnet-row" :class="mag.status">
            <div class="magnet-index">{{ idx + 1 }}</div>
            <div class="magnet-left">
              <div class="mag-name">{{ mag.name || '未命名磁力任务' }}</div>
              <div class="mag-meta">
                <span class="mag-hash">{{ mag.hash }}</span>
                <span v-if="mag.status === 'added'" class="status-pill success">已添加</span>
                <span v-else-if="mag.status === 'failed'" class="status-pill danger">添加失败</span>
                <span v-else-if="mag.status === 'adding'" class="status-pill">添加中</span>
              </div>
            </div>
            <div class="magnet-right">
              <button class="btn btn-ghost copy-btn" type="button" @click="copyMagnet(mag)">复制</button>
              <button class="btn btn-primary download-btn" type="button" :disabled="mag.status === 'adding' || mag.status === 'added'" @click="downloadMagnet(mag)">
                {{ mag.status === 'added' ? '已添加' : '添加' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section v-if="invalidLines.length > 0" class="issue-panel" aria-label="无效磁链">
      <div class="issue-head">
        <h2>需要检查的行</h2>
        <span>{{ invalidLines.length }} 条</span>
      </div>
      <div class="issue-list">
        <div v-for="item in invalidLines" :key="item.index" class="issue-row">
          <strong>第 {{ item.index }} 行</strong>
          <span>{{ item.text }}</span>
        </div>
      </div>
    </section>

    <div v-else-if="hasParsed && !loading && hasInput && !parsedMagnets.length" class="empty-state">
      <p>没有解析出可添加的磁力链接。</p>
    </div>
  </div>
</template>

<script>
import api from '../api'

export default {
  name: 'MagnetParse',
  data() {
    return {
      magnetInput: '',
      loading: false,
      batchLoading: false,
      parsedMagnets: [],
      invalidLines: [],
      duplicateCount: 0,
      hasParsed: false,
    }
  },
  computed: {
    hasInput() {
      return Boolean(this.magnetInput.trim())
    },
    hasResults() {
      return this.parsedMagnets.length > 0 || this.invalidLines.length > 0 || this.duplicateCount > 0
    },
    inputLineCount() {
      if (!this.hasInput) return 0
      return this.magnetInput.split('\n').filter(line => line.trim()).length
    },
    resultSummary() {
      const added = this.parsedMagnets.filter(mag => mag.status === 'added').length
      if (added) return `${added} 条已加入下载队列，${this.parsedMagnets.length - added} 条待添加`
      return `${this.parsedMagnets.length} 条可添加，已过滤 ${this.duplicateCount} 条重复`
    },
  },
  methods: {
    parseMagnets() {
      const lines = this.magnetInput.split('\n')
      if (!lines.length) return
      this.loading = true
      this.parsedMagnets = []
      this.invalidLines = []
      this.duplicateCount = 0
      this.hasParsed = true

      const magnetRE = /magnet:\?xt=urn:btih:([A-Fa-f0-9]+)(?:&dn=([^&]+))?/i
      const seenHashes = new Set()

      for (const [index, rawLine] of lines.entries()) {
        const line = rawLine.trim()
        if (!line) continue

        const match = magnetRE.exec(line)
        const fallbackHash = line.match(/btih:([A-Za-z0-9]+)/i)?.[1] || ''
        const hash = (match?.[1] || fallbackHash).toUpperCase()

        if (!/^magnet:/i.test(line) || !hash) {
          this.invalidLines.push({ index: index + 1, text: line })
          continue
        }

        if (seenHashes.has(hash)) {
          this.duplicateCount += 1
          continue
        }

        seenHashes.add(hash)
        if (match) {
          this.parsedMagnets.push({
            magnet: line.trim(),
            hash,
            name: this.decodeMagnetName(match[2]),
            status: 'idle',
          })
        } else {
          this.parsedMagnets.push({
            magnet: line.trim(),
            hash,
            name: '',
            status: 'idle',
          })
        }
      }
      this.loading = false
    },
    decodeMagnetName(value) {
      if (!value) return ''
      try {
        return decodeURIComponent(value.replace(/\+/g, ' '))
      } catch {
        return value
      }
    },
    clearResults() {
      this.parsedMagnets = []
      this.invalidLines = []
      this.duplicateCount = 0
      this.hasParsed = false
    },
    clearAll() {
      this.magnetInput = ''
      this.clearResults()
    },
    async downloadMagnet(mag) {
      try {
        mag.status = 'adding'
        await api.createDownload({
          content_id: mag.hash.slice(0, 12),
          title: mag.name || '磁力下载',
          magnet: mag.magnet
        })
        mag.status = 'added'
        this.$message?.success?.('已添加到下载队列')
      } catch (e) {
        mag.status = 'failed'
        this.$message?.error?.('添加失败')
      }
    },
    async downloadAllMagnets() {
      this.batchLoading = true
      for (const mag of this.parsedMagnets) {
        if (mag.status === 'added') continue
        await this.downloadMagnet(mag)
      }
      this.batchLoading = false
    },
    async copyMagnet(mag) {
      try {
        await navigator.clipboard.writeText(mag.magnet)
        this.$message?.success?.('已复制磁力链接')
      } catch {
        this.$message?.error?.('复制失败')
      }
    }
  }
}
</script>

<style scoped>
.parse-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.parse-hero {
  max-width: 680px;
  margin: 12px auto 4px;
  text-align: center;
}

.hero-kicker {
  margin-bottom: 10px;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.parse-hero h1 {
  color: var(--text-primary);
  font-size: clamp(34px, 6vw, 58px);
  font-weight: 700;
  line-height: 1;
  margin-bottom: 14px;
}

.page-desc {
  color: var(--text-secondary);
  font-size: 15px;
  line-height: 1.6;
}

.parse-console {
  width: min(820px, 100%);
  margin-inline: auto;
  padding: clamp(18px, 3vw, 28px);
  background:
    linear-gradient(180deg, rgba(var(--accent-rgb), 0.045), transparent 42%),
    var(--surface-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  box-shadow: var(--shadow-card);
}

.console-head,
.magnets-header,
.issue-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.console-head {
  margin-bottom: 16px;
}

.console-head h2,
.magnets-header h2,
.issue-head h2 {
  margin: 0 0 4px;
  color: var(--text-primary);
  font-size: 17px;
  line-height: 1.2;
}

.console-head p,
.magnets-header p {
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.5;
}

.clear-input-btn,
.clear-results-btn,
.copy-btn,
.download-btn {
  min-height: 36px;
  padding: 7px 12px;
  font-size: 12px;
  white-space: nowrap;
}

.parse-textarea {
  width: 100%;
  min-height: 260px;
  resize: vertical;
  font-family: var(--font-mono);
  font-size: 13px;
  line-height: 1.65;
}

.parse-summary {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-top: 14px;
}

.summary-item {
  min-width: 0;
  padding: 14px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-md);
  background: var(--material-glass-subtle);
}

.summary-item strong {
  display: block;
  color: var(--text-primary);
  font-size: 22px;
  line-height: 1;
}

.summary-item span {
  display: block;
  margin-top: 7px;
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 600;
}

.summary-item.success { background: var(--badge-success-bg); border-color: var(--badge-success-border); }
.summary-item.warning { background: var(--badge-warning-bg); border-color: var(--badge-warning-border); }
.summary-item.danger { background: var(--badge-error-bg); border-color: var(--badge-error-border); }

.parse-actions {
  display: flex;
  justify-content: center;
  gap: 10px;
  margin-top: 18px;
}

.result-section,
.issue-panel {
  width: min(820px, 100%);
  margin-inline: auto;
  animation: slideUp 0.3s ease;
}

.magnets-card { overflow: hidden; }

.magnets-header {
  padding: 18px 20px;
  border-bottom: 1px solid var(--border);
}

.magnets-list { display: flex; flex-direction: column; }

.magnet-row {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
  padding: 14px 20px;
  background: var(--bg-secondary);
  transition: var(--transition);
}

.magnet-row:nth-child(even) { background: var(--bg-card); }
.magnet-row:hover { background: var(--bg-card-hover); }

.magnet-row.added {
  background: var(--badge-success-bg);
}

.magnet-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: var(--radius-sm);
  background: var(--surface-card);
  color: var(--text-muted);
  font-size: 12px;
  font-weight: 700;
}

.magnet-left {
  min-width: 0;
}

.mag-name {
  max-width: 100%;
  overflow: hidden;
  color: var(--text-primary);
  font-size: 14px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.mag-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  margin-top: 5px;
}

.mag-hash {
  min-width: 0;
  overflow: hidden;
  color: var(--text-muted);
  font-family: var(--font-mono);
  font-size: 11px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-pill {
  flex: 0 0 auto;
  padding: 3px 7px;
  border: 1px solid var(--border-light);
  border-radius: var(--radius-xs);
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 700;
}

.status-pill.success { color: var(--badge-success-text); border-color: var(--badge-success-border); background: var(--badge-success-bg); }
.status-pill.danger { color: var(--badge-error-text); border-color: var(--badge-error-border); background: var(--badge-error-bg); }

.magnet-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.issue-panel {
  padding: 18px 20px;
  border: 1px solid var(--badge-warning-border);
  border-radius: var(--radius-card);
  background: var(--badge-warning-bg);
}

.issue-head {
  align-items: center;
  margin-bottom: 12px;
}

.issue-head span {
  color: var(--badge-warning-text);
  font-size: 12px;
  font-weight: 700;
}

.issue-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.issue-row {
  display: grid;
  grid-template-columns: 72px minmax(0, 1fr);
  gap: 10px;
  color: var(--text-secondary);
  font-size: 12px;
}

.issue-row strong {
  color: var(--text-primary);
}

.issue-row span {
  overflow: hidden;
  font-family: var(--font-mono);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-state {
  width: min(820px, 100%);
  margin-inline: auto;
  padding: 44px 20px;
  color: var(--text-muted);
  font-size: 14px;
  text-align: center;
}

@media (max-width: 768px) {
  .parse-hero {
    margin-top: 4px;
  }

  .parse-summary {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .parse-actions,
  .console-head,
  .magnets-header {
    align-items: stretch;
    flex-direction: column;
  }

  .parse-actions .btn,
  .clear-results-btn {
    width: 100%;
  }

  .magnet-row {
    grid-template-columns: 30px minmax(0, 1fr);
    align-items: start;
  }

  .magnet-right {
    grid-column: 2;
    width: 100%;
  }

  .magnet-right .btn {
    flex: 1;
    min-height: 44px;
  }

  .issue-row {
    grid-template-columns: 1fr;
    gap: 4px;
  }
}
</style>

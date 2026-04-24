<template>
  <div class="parse-page">
    <div class="page-header">
      <h1>磁链解析</h1>
      <p class="page-desc">粘贴磁力链接，批量解析并添加到下载队列</p>
    </div>

    <!-- 输入区 -->
    <div class="parse-input-card">
      <textarea
        v-model="magnetInput"
        class="input parse-textarea"
        placeholder="粘贴磁力链接，每行一个&#10;示例：&#10;magnet:?xt=urn:btih:ABC123...&#10;magnet:?xt=urn:btih:DEF456..."
        rows="5"
      ></textarea>
      <div class="parse-actions">
        <button class="btn btn-primary" @click="parseMagnets" :disabled="loading || !magnetInput.trim()">
          <span v-if="loading" class="spinner"></span>
          <span v-else>批量添加</span>
        </button>
      </div>
    </div>

    <!-- 解析结果 -->
    <div v-if="parsedMagnets.length > 0" class="result-section">
      <div class="magnets-card av-card">
        <div class="magnets-header" style="padding:16px;border-bottom:1px solid var(--border);display:flex;justify-content:space-between;align-items:center">
          <span>解析结果 ({{ parsedMagnets.length }} 条)</span>
          <button class="btn btn-ghost" style="font-size:12px;padding:4px 10px" @click="parsedMagnets = []; magnetInput = ''">清空</button>
        </div>
        <div class="magnets-list">
          <div v-for="(mag, idx) in parsedMagnets" :key="idx" class="magnet-row">
            <div class="magnet-left" style="flex-direction:column;align-items:flex-start;gap:4px">
              <div class="mag-hash">{{ mag.hash }}</div>
              <div class="mag-name">{{ mag.name || '未知文件' }}</div>
            </div>
            <div class="magnet-right">
              <button class="btn btn-primary download-btn" @click="downloadMagnet(mag)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                  <polyline points="7 10 12 15 17 10"/>
                  <line x1="12" y1="15" x2="12" y2="3"/>
                </svg>
                添加
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!loading && magnetInput && magnetInput.trim()" class="empty-state">
      <p>未能解析出磁力链接，请检查格式</p>
    </div>
  </div>
</template>

<script>
export default {
  name: 'MagnetParse',
  data() {
    return {
      magnetInput: '',
      loading: false,
      parsedMagnets: [],
    }
  },
  methods: {
    parseMagnets() {
      const lines = this.magnetInput.trim().split('\n').filter(l => l.trim())
      if (!lines.length) return
      this.loading = true
      this.parsedMagnets = []

      const magnetRE = /magnet:\?xt=urn:btih:([A-Fa-f0-9]+)(?:&dn=([^&]+))?/gi

      for (const line of lines) {
        const match = magnetRE.exec(line)
        if (match) {
          this.parsedMagnets.push({
            magnet: line.trim(),
            hash: match[1].toUpperCase(),
            name: match[2] ? decodeURIComponent(match[2]) : ''
          })
        } else if (line.startsWith('magnet:')) {
          const hashMatch = line.match(/btih:([A-Fa-f0-9]+)/i)
          this.parsedMagnets.push({
            magnet: line.trim(),
            hash: hashMatch ? hashMatch[1].toUpperCase() : '未知',
            name: ''
          })
        }
      }
      this.loading = false
    },
    async downloadMagnet(mag) {
      try {
        const { default: api } = await import('../api/index.js')
        await api.createDownload({
          code: mag.hash.slice(0, 12),
          title: mag.name || '磁力下载',
          magnet: mag.magnet
        })
        this.$message.success('已添加到下载队列')
      } catch (e) {
        this.$message.error('添加失败')
      }
    }
  }
}
</script>

<style scoped>
.parse-page { padding: 24px; max-width: 900px; margin: 0 auto; }
.page-header { margin-bottom: 24px; }
.page-header h1 { font-size: 24px; font-weight: 700; color: var(--text-primary); margin-bottom: 6px; }
.page-desc { font-size: 14px; color: var(--text-secondary); }

.parse-input-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 16px;
  margin-bottom: 20px;
}
.parse-textarea { width: 100%; resize: vertical; min-height: 400px; font-family: monospace; font-size: 13px; }
.parse-actions { display: flex; justify-content: flex-end; margin-top: 12px; }

/* Magnets */
.result-section { animation: slideUp 0.3s ease; }
.magnets-card { overflow: hidden; }
.magnets-header { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.magnets-list { display: flex; flex-direction: column; }
.magnet-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 16px; background: var(--bg-secondary);
  gap: 12px; transition: var(--transition);
}
.magnet-row:nth-child(even) { background: var(--bg-card); }
.magnet-row:hover { background: var(--bg-card-hover); }
.magnet-left { display: flex; align-items: center; gap: 8px; min-width: 0; flex: 1; }
.mag-hash { font-size: 11px; color: var(--accent); font-family: monospace; }
.mag-name { font-size: 12px; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 400px; }
.magnet-right { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
.download-btn { font-size: 12px; padding: 5px 12px; }

/* Empty */
.empty-state { text-align: center; padding: 40px 20px; color: var(--text-muted); font-size: 14px; }

@media (max-width: 768px) {
  .parse-page { padding: 16px; }
  .mag-name { max-width: 200px; }
}
</style>

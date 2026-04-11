<template>
  <div class="parse-page">
    <div class="page-header">
      <h1>磁链解析</h1>
      <p class="page-desc">输入番号或磁力链接，自动解析并添加下载</p>
    </div>

    <!-- 输入区 -->
    <div class="parse-input-card">
      <div class="input-tabs">
        <button
          :class="['tab', { active: inputMode === 'code' }]"
          @click="inputMode = 'code'"
        >番号搜索</button>
        <button
          :class="['tab', { active: inputMode === 'magnet' }]"
          @click="inputMode = 'magnet'"
        >磁力解析</button>
      </div>

      <div v-if="inputMode === 'code'" class="input-group">
        <input
          v-model="codeInput"
          class="input parse-input"
          placeholder="输入番号，如 MIDV-595"
          @keyup.enter="searchCode"
        />
        <button class="btn btn-primary" @click="searchCode" :disabled="loading">
          <span v-if="loading" class="spinner"></span>
          <span v-else>搜索</span>
        </button>
      </div>

      <div v-else class="input-group">
        <textarea
          v-model="magnetInput"
          class="input parse-textarea"
          placeholder="粘贴磁力链接，每行一个"
          rows="3"
        ></textarea>
        <button class="btn btn-primary" @click="parseMagnets" :disabled="loading || !magnetInput.trim()">
          <span v-if="loading" class="spinner"></span>
          <span v-else>解析</span>
        </button>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <div class="spinner" style="margin: 0 auto"></div>
      <p>解析中...</p>
    </div>

    <!-- 番号搜索结果（卡片网格） -->
    <div v-else-if="searchResults.length > 0" class="results-section">
      <div class="results-header">
        <span>搜索结果 ({{ searchResults.length }} 个)</span>
      </div>
      <!-- 分页控制 -->
      <div v-if="totalPages > 1" class="pagination-bar">
        <button class="btn btn-ghost" :disabled="currentPage <= 1" @click="changePage(currentPage - 1)">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
          上一页
        </button>
        <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
        <button class="btn btn-ghost" :disabled="currentPage >= totalPages" @click="changePage(currentPage + 1)">
          下一页
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
            <polyline points="9 18 15 12 9 6"/>
          </svg>
        </button>
      </div>
      <div class="results-grid">
        <div
          v-for="item in searchResults"
          :key="item.code"
          class="movie-card av-card"
          @click="selectMovie(item)"
        >
          <div class="card-cover">
            <img
              :src="proxyImg(item.cover_url)"
              :alt="item.code"
              @error="handleImgError"
              loading="lazy"
            />
            <div class="card-overlay">
              <span class="overlay-code">{{ item.code }}</span>
              <span v-if="item.magnets && item.magnets.length" class="overlay-badge">
                {{ item.magnets.length }} 磁力
              </span>
            </div>
          </div>
          <div class="card-info">
            <h3 class="card-title">{{ item.title }}</h3>
            <div class="card-meta">
              <span v-if="item.actor" class="meta-item">{{ item.actor }}</span>
              <span v-if="item.date" class="meta-item">{{ item.date }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 单个影片详情（从网格点击选中） -->
    <div v-else-if="selectedMovie" class="result-section">
      <div class="result-card av-card">
        <button class="back-btn" @click="selectedMovie = null">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="16" height="16">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
          返回列表
        </button>
        <div class="result-body">
          <div class="result-cover">
            <img
              :src="proxyImg(selectedMovie.cover_url)"
              :alt="selectedMovie.code"
              @error="handleImgError"
            />
          </div>
          <div class="result-info">
            <h2>{{ selectedMovie.title }}</h2>
            <div class="result-meta">
              <span v-if="selectedMovie.actor">
                <svg viewBox="0 0 24 24" fill="currentColor" width="13" height="13">
                  <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                </svg>
                {{ selectedMovie.actor }}
              </span>
              <span v-if="selectedMovie.date">
                <svg viewBox="0 0 24 24" fill="currentColor" width="13" height="13">
                  <path d="M19 3h-1V1h-2v2H8V1H6v2H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11z"/>
                </svg>
                {{ selectedMovie.date }}
              </span>
            </div>
            <div class="result-code">番号: <strong>{{ selectedMovie.code }}</strong></div>

            <!-- 磁力列表 -->
            <div class="result-magnets">
              <div class="magnets-header">
                <span>磁力链接 ({{ selectedMovie.magnets?.length || 0 }})</span>
              </div>
              <div class="magnets-list">
                <div v-for="(mag, idx) in selectedMovie.magnets" :key="idx" class="magnet-row">
                  <div class="magnet-left">
                    <span v-if="mag.hd" class="badge badge-success" style="font-size:10px;padding:1px 6px;">HD</span>
                    <span class="mag-title">{{ mag.title || '默认' }}</span>
                  </div>
                  <div class="magnet-right">
                    <span class="mag-size">{{ mag.size }}</span>
                    <button class="btn btn-primary download-btn" @click="download(selectedMovie, mag)">
                      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13">
                        <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                        <polyline points="7 10 12 15 17 10"/>
                        <line x1="12" y1="15" x2="12" y2="3"/>
                      </svg>
                      下载
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 磁力解析结果 -->
    <div v-else-if="parsedMagnets.length > 0" class="result-section">
      <div class="magnets-card av-card">
        <div class="magnets-header" style="padding:16px;border-bottom:1px solid var(--border)">
          <span>解析结果 ({{ parsedMagnets.length }} 条)</span>
        </div>
        <div class="magnets-list">
          <div v-for="(mag, idx) in parsedMagnets" :key="idx" class="magnet-row">
            <div class="magnet-left" style="flex-direction:column;align-items:flex-start;gap:4px">
              <div class="mag-hash">{{ mag.hash }}</div>
              <div class="mag-name">{{ mag.name || '未知文件' }}</div>
            </div>
            <div class="magnet-right">
              <span class="mag-size">{{ mag.size || '-' }}</span>
              <button class="btn btn-primary download-btn" @click="downloadMagnet(mag)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13">
                  <path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/>
                  <polyline points="7 10 12 15 17 10"/>
                  <line x1="12" y1="15" x2="12" y2="3"/>
                </svg>
                下载
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="searched && !loading" class="empty-state">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
        <line x1="12" y1="11" x2="12" y2="17"/>
        <line x1="9" y1="14" x2="15" y2="14"/>
      </svg>
      <p>未找到影片</p>
      <p class="text-secondary" style="font-size:13px;margin-top:6px">尝试其他番号</p>
    </div>
  </div>
</template>

<script>
import api from '../api'

export default {
  name: 'MagnetParse',
  data() {
    return {
      inputMode: 'code',
      codeInput: '',
      magnetInput: '',
      loading: false,
      searched: false,
      searchResults: [],
      selectedMovie: null,
      parsedMagnets: [],
      currentPage: 1,
      totalPages: 1
    }
  },
  methods: {
    proxyImg(url) {
      if (!url) return ''
      if (url.includes('javbus.com')) return api.proxyImage(url)
      return url
    },
    async searchCode() {
      if (!this.codeInput.trim()) return
      this.loading = true
      this.searched = true
      this.selectedMovie = null
      this.parsedMagnets = []
      this.currentPage = 1
      try {
        const resp = await api.search(this.codeInput.trim())
        const results = resp.data || []
        this.searchResults = results
        // 估算总页数（默认API每页30条，这里简单处理）
        this.totalPages = Math.max(1, Math.ceil(results.length / 30))
      } catch (e) {
        console.error('Search failed:', e)
        this.searchResults = []
      } finally {
        this.loading = false
      }
    },
    async changePage(page) {
      if (page < 1 || page > this.totalPages) return
      this.loading = true
      this.currentPage = page
      try {
        const resp = await api.search(this.codeInput.trim(), page)
        const results = resp.data || []
        this.searchResults = results
      } catch (e) {
        console.error('Page search failed:', e)
      } finally {
        this.loading = false
      }
    },
    selectMovie(movie) {
      this.selectedMovie = movie
    },
    parseMagnets() {
      const lines = this.magnetInput.trim().split('\n').filter(l => l.trim())
      if (!lines.length) return
      this.loading = true
      this.searched = true
      this.selectedMovie = null
      this.searchResults = []

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
    async download(item, mag) {
      try {
        await api.createDownload({ code: item.code, title: item.title, magnet: mag.magnet })
        this.$message.success('已添加到下载队列')
      } catch (e) {
        this.$message.error('添加失败')
      }
    },
    async downloadMagnet(mag) {
      try {
        await api.createDownload({
          code: mag.hash.slice(0, 12),
          title: mag.name || '磁力下载',
          magnet: mag.magnet
        })
        this.$message.success('已添加到下载队列')
      } catch (e) {
        this.$message.error('添加失败')
      }
    },
    handleImgError(e) {
      e.target.src = 'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="200" height="280" viewBox="0 0 200 280"><rect fill="%231a1a2e" width="200" height="280"/><text x="50%" y="50%" text-anchor="middle" dy=".3em" fill="%236B6B8A" font-size="14">暂无封面</text></svg>'
    }
  }
}
</script>

<style scoped>
.parse-page { padding: 24px; max-width: 1200px; margin: 0 auto; }
.page-header { margin-bottom: 24px; }
.page-header h1 { font-size: 24px; font-weight: 700; color: var(--text-primary); margin-bottom: 6px; }
.page-desc { font-size: 14px; color: var(--text-secondary); }

/* Input Card */
.parse-input-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 16px;
  margin-bottom: 20px;
}
.input-tabs { display: flex; gap: 4px; margin-bottom: 14px; }
.tab {
  padding: 8px 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
  transition: var(--transition);
}
.tab:hover { border-color: var(--border-light); color: var(--text-primary); }
.tab.active { background: var(--accent); border-color: var(--accent); color: white; }

.input-group { display: flex; gap: 10px; align-items: flex-start; }
.parse-input { flex: 1; }
.parse-textarea { flex: 1; resize: vertical; min-height: 80px; }

/* Loading */
.loading-state { text-align: center; padding: 40px; color: var(--text-secondary); display: flex; flex-direction: column; align-items: center; gap: 12px; }

/* Results Grid */
.results-section { animation: slideUp 0.3s ease; }
.results-header { font-size: 14px; color: var(--text-secondary); margin-bottom: 14px; padding: 0 4px; }

.pagination-bar {
  display: flex; align-items: center; justify-content: center; gap: 16px;
  margin-bottom: 16px;
}
.page-info { font-size: 13px; color: var(--text-secondary); }
.pagination-bar .btn { display: flex; align-items: center; gap: 4px; font-size: 13px; padding: 6px 12px; }

.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 20px;
}

/* Movie Card */
.movie-card { cursor: pointer; }
.card-cover {
  position: relative;
  aspect-ratio: 3/4;
  overflow: hidden;
  background: var(--bg-secondary);
  border-radius: var(--radius-md) var(--radius-md) 0 0;
}
.card-cover img {
  width: 100%; height: 100%; object-fit: cover;
  transition: transform 0.4s ease;
}
.movie-card:hover .card-cover img { transform: scale(1.05); }

.card-overlay {
  position: absolute; inset: 0;
  background: linear-gradient(transparent 40%, rgba(0,0,0,0.85) 100%);
  display: flex; flex-direction: column; justify-content: flex-end;
  padding: 12px;
  opacity: 0; transition: opacity 0.3s ease;
}
.movie-card:hover .card-overlay { opacity: 1; }
.overlay-code { color: white; font-size: 14px; font-weight: 700; }
.overlay-badge {
  display: inline-block; margin-top: 4px; padding: 3px 8px;
  background: rgba(76,175,80,0.25); backdrop-filter: blur(8px);
  border-radius: 20px; color: var(--accent-light); font-size: 11px; font-weight: 600;
  border: 1px solid rgba(76,175,80,0.3); width: fit-content;
}

.card-info { padding: 12px; }
.card-title {
  font-size: 13px; font-weight: 500; color: var(--text-primary);
  margin-bottom: 6px; display: -webkit-box; -webkit-line-clamp: 2;
  -webkit-box-orient: vertical; overflow: hidden; line-height: 1.4;
}
.card-meta { display: flex; gap: 10px; flex-wrap: wrap; }
.meta-item { font-size: 11px; color: var(--text-muted); }

/* Result Card (single movie detail) */
.result-section { animation: slideUp 0.3s ease; }
.result-card { padding: 20px; }
.back-btn {
  display: inline-flex; align-items: center; gap: 6px;
  background: none; border: none; color: var(--text-secondary);
  font-size: 13px; cursor: pointer; margin-bottom: 16px;
  padding: 4px 8px; border-radius: 6px; transition: var(--transition);
}
.back-btn:hover { color: var(--text-primary); background: var(--bg-secondary); }
.result-body { display: flex; gap: 20px; }
.result-cover {
  width: 160px; min-width: 160px;
  aspect-ratio: 3/4; border-radius: var(--radius-sm);
  overflow: hidden; background: var(--bg-secondary);
}
.result-cover img { width: 100%; height: 100%; object-fit: cover; }
.result-info { flex: 1; min-width: 0; }
.result-info h2 { font-size: 18px; font-weight: 700; color: var(--text-primary); margin-bottom: 10px; line-height: 1.3; }
.result-meta { display: flex; gap: 16px; margin-bottom: 8px; flex-wrap: wrap; }
.result-meta span { display: flex; align-items: center; gap: 4px; font-size: 13px; color: var(--text-secondary); }
.result-code { font-size: 13px; color: var(--text-secondary); margin-bottom: 14px; }
.result-code strong { color: var(--accent); }

/* Magnets */
.result-magnets { border-top: 1px solid var(--border); padding-top: 12px; }
.magnets-header { font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 10px; }
.magnets-list { display: flex; flex-direction: column; gap: 6px; }
.magnet-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 12px; background: var(--bg-secondary);
  border-radius: var(--radius-sm); gap: 12px;
  transition: var(--transition);
}
.magnet-row:hover { background: var(--bg-card-hover); }
.magnet-left { display: flex; align-items: center; gap: 8px; min-width: 0; flex: 1; }
.mag-title { font-size: 12px; color: var(--text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.mag-hash { font-size: 11px; color: var(--accent); font-family: monospace; }
.mag-name { font-size: 12px; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 400px; }
.magnet-right { display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
.mag-size { font-size: 11px; color: var(--text-muted); }
.download-btn { font-size: 12px; padding: 5px 10px; }

/* Magnets Card */
.magnets-card { overflow: hidden; }

/* Empty */
.empty-state { text-align: center; padding: 60px 20px; color: var(--text-secondary); display: flex; flex-direction: column; align-items: center; gap: 12px; }
.empty-state svg { width: 48px; height: 48px; opacity: 0.5; }

@media (max-width: 768px) {
  .parse-page { padding: 16px; }
  .result-body { flex-direction: column; }
  .result-cover { width: 100%; min-width: unset; max-width: 200px; margin: 0 auto; }
  .results-grid { grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 14px; }
}
</style>

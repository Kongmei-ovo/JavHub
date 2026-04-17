<template>
  <div class="normalize-page">
    <div class="page-header">
      <h1>演员合并</h1>
      <div class="header-actions">
        <button @click="loadSimilar" class="btn-secondary" :disabled="loading">
          刷新相似列表
        </button>
        <button @click="showHistory = true; fetchHistory()" class="btn-ghost">合并历史</button>
      </div>
    </div>

    <!-- 过滤栏 -->
    <div class="filter-bar">
      <div class="search-box">
        <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8"/>
          <path d="m21 21-4.35-4.35"/>
        </svg>
        <input
          v-model="filterName"
          placeholder="搜索演员名..."
          class="search-input"
          @input="onFilterInput"
        />
        <button v-if="filterName" class="search-clear" @click="filterName = ''; loadSimilar()">×</button>
      </div>
      <div class="threshold-control">
        <label>相似度 ≥</label>
        <select v-model.number="threshold" @change="loadSimilar" class="filter-select">
          <option :value="1.0">1.0 完全相同</option>
          <option :value="0.8">0.8+ 高相似</option>
          <option :value="0.6">0.6+ 中相似</option>
          <option :value="0.4">0.4+ 低相似</option>
        </select>
      </div>
      <span class="result-count">共 {{ similarPairs.length }} 对</span>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading">检测中...</div>
    <div v-else-if="error" class="error">{{ error }}</div>

    <!-- 疑似重复列表 -->
    <div v-else-if="similarPairs.length > 0" class="pairs-list">
      <div
        v-for="(pair, idx) in similarPairs"
        :key="idx"
        class="pair-card"
        :class="{ selected: selectedPair === idx }"
        @click="toggleSelect(idx)"
      >
        <div class="pair-info">
          <div class="actor-cell">
            <div class="actor-cover">
              <img
                :src="pair.actor_a.avatar_url || ''"
                :alt="pair.actor_a.actress_name"
                @error="$event.target.style.display='none'"
              />
            </div>
            <div class="actor-details">
              <div class="actor-name">{{ pair.actor_a.actress_name }}</div>
              <div class="actor-meta">ID: {{ pair.actor_a.actress_id }} · {{ pair.actor_a.total_videos }} 部</div>
            </div>
          </div>
          <div class="merge-arrow">→</div>
          <div class="actor-cell">
            <div class="actor-cover">
              <img
                :src="pair.actor_b.avatar_url || ''"
                :alt="pair.actor_b.actress_name"
                @error="$event.target.style.display='none'"
              />
            </div>
            <div class="actor-details">
              <div class="actor-name">{{ pair.actor_b.actress_name }}</div>
              <div class="actor-meta">ID: {{ pair.actor_b.actress_id }} · {{ pair.actor_b.total_videos }} 部</div>
            </div>
          </div>
        </div>
        <div class="pair-right">
          <div class="similarity-badge" :class="getSimilarityClass(pair.similarity)">
            {{ (pair.similarity * 100).toFixed(0) }}%
          </div>
          <div v-if="selectedPair === idx" class="merge-confirm">
            <div class="confirm-label">确认合并？</div>
            <div class="confirm-btns">
              <button class="btn-merge" @click.stop="confirmMerge(pair)">合并</button>
              <button class="btn-cancel" @click.stop="selectedPair = null">取消</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="empty">
      <template v-if="filterName || threshold < 0.8">未找到符合条件的相似演员</template>
      <template v-else>暂无疑似重复演员，试试降低相似度阈值</template>
    </div>

    <!-- 合并历史弹窗 -->
    <div v-if="showHistory" class="dialog-overlay" @click.self="showHistory = false">
      <div class="dialog history-dialog">
        <div class="dialog-header">
          <h3>合并历史</h3>
          <button @click="showHistory = false" class="close-btn">×</button>
        </div>
        <div v-if="loadingHistory" class="loading">加载中...</div>
        <div v-else-if="mergeHistory.length === 0" class="empty">暂无合并记录</div>
        <div v-else class="history-list">
          <div v-for="h in mergeHistory" :key="h.id" class="history-item">
            <div class="history-info">
              <span class="history-from">{{ h.from_name }}</span>
              <span class="history-arrow">→</span>
              <span class="history-to">{{ h.to_name }}</span>
            </div>
            <div class="history-meta">{{ h.merged_at }} · {{ h.movies_count }} 部电影已转移</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const similarPairs = ref([])
const loading = ref(false)
const error = ref('')
const filterName = ref('')
const threshold = ref(0.8)
const selectedPair = ref(null)
const showHistory = ref(false)
const mergeHistory = ref([])
const loadingHistory = ref(false)
let filterTimer = null

const loadSimilar = async () => {
  loading.value = true
  error.value = ''
  try {
    const params = { threshold: threshold.value }
    if (filterName.value) params.name = filterName.value
    const res = await axios.get('/api/inventory/actors/find-similar', { params })
    similarPairs.value = res.data.data || []
  } catch (e) {
    error.value = '加载失败: ' + e.message
  } finally {
    loading.value = false
  }
}

const onFilterInput = () => {
  clearTimeout(filterTimer)
  filterTimer = setTimeout(loadSimilar, 300)
}

const toggleSelect = (idx) => {
  selectedPair.value = selectedPair.value === idx ? null : idx
}

const getSimilarityClass = (sim) => {
  if (sim >= 1.0) return 'identical'
  if (sim >= 0.9) return 'high'
  if (sim >= 0.7) return 'medium'
  return 'low'
}

const confirmMerge = async (pair) => {
  if (!confirm(`确认合并「${pair.actor_a.actress_name}」的所有电影到「${pair.actor_b.actress_name}」？\n\n此操作不可逆，被合并的演员将无法在列表中找到。`)) {
    selectedPair.value = null
    return
  }
  try {
    await axios.post('/api/inventory/actors/merge', {
      from_actress_id: pair.actor_a.actress_id,
      to_actress_id: pair.actor_b.actress_id
    })
    alert('合并成功')
    selectedPair.value = null
    await loadSimilar()
  } catch (e) {
    alert('合并失败: ' + e.message)
  }
}

const fetchHistory = async () => {
  // 暂时从 aliases 接口拿数据，merge 后 alias 会记录
  loadingHistory.value = true
  try {
    const res = await axios.get('/api/inventory/aliases')
    mergeHistory.value = (res.data.data || []).map(a => ({
      id: a.id,
      from_id: a.alias_id,
      to_id: a.canonical_id,
      from_name: a.alias_name || `ID:${a.alias_id}`,
      to_name: a.canonical_name || `ID:${a.canonical_id}`,
      merged_at: a.created_at || '',
      movies_count: 0
    }))
  } catch (e) {
    console.error('load history failed:', e)
  } finally {
    loadingHistory.value = false
  }
}

onMounted(loadSimilar)
</script>

<style scoped>
.normalize-page { padding: 16px; }
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.header-actions { display: flex; gap: 8px; }
.btn-primary {
  background: var(--accent, #1890ff); color: #fff; border: none;
  padding: 8px 16px; border-radius: 4px; cursor: pointer;
}
.btn-secondary {
  background: var(--bg-card); color: var(--accent, #1890ff); border: 1px solid var(--accent, #1890ff);
  padding: 8px 16px; border-radius: 4px; cursor: pointer;
}
.btn-ghost {
  background: none; color: var(--text-secondary); border: 1px solid var(--border);
  padding: 8px 16px; border-radius: 4px; cursor: pointer;
}
.btn-secondary:disabled, .btn-ghost:disabled { opacity: 0.5; cursor: not-allowed; }

.filter-bar {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}
.search-box {
  display: flex;
  align-items: center;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 0 12px;
  flex: 1;
  max-width: 300px;
}
.search-box:focus-within { border-color: var(--accent, #1890ff); }
.search-icon {
  width: 18px; height: 18px; color: var(--text-muted); flex-shrink: 0;
}
.search-input {
  flex: 1; border: none; outline: none; padding: 8px;
  font-size: 14px; background: transparent; color: var(--text-primary);
}
.search-clear {
  background: none; border: none; color: var(--text-muted);
  cursor: pointer; font-size: 18px; padding: 0 4px;
}
.search-clear:hover { color: var(--text-primary); }
.threshold-control {
  display: flex; align-items: center; gap: 6px;
}
.threshold-control label { font-size: 13px; color: var(--text-secondary); white-space: nowrap; }
.filter-select {
  padding: 6px 10px; border: 1px solid var(--border);
  border-radius: 4px; background: var(--bg-card); color: var(--text-primary);
  font-size: 13px; cursor: pointer;
}
.filter-select:focus { outline: none; border-color: var(--accent, #1890ff); }
.result-count {
  font-size: 13px; color: var(--text-secondary); white-space: nowrap;
}

.pairs-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.pair-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}
.pair-card:hover { border-color: var(--accent, #1890ff); }
.pair-card.selected { border-color: var(--accent, #1890ff); background: color-mix(in srgb, var(--accent, #1890ff) 8%, var(--bg-card)); }
.pair-info {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
}
.actor-cell {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}
.actor-cover {
  width: 40px;
  height: 53px;
  border-radius: 4px;
  overflow: hidden;
  background: var(--bg-secondary);
  flex-shrink: 0;
}
.actor-cover img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.actor-details { min-width: 0; }
.actor-name {
  font-weight: 600;
  font-size: 14px;
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.actor-meta {
  font-size: 11px;
  color: var(--text-muted);
  margin-top: 2px;
}
.merge-arrow {
  font-size: 18px;
  color: var(--accent, #1890ff);
  flex-shrink: 0;
  font-weight: bold;
}
.pair-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}
.similarity-badge {
  font-size: 12px;
  font-weight: bold;
  padding: 3px 8px;
  border-radius: 10px;
  min-width: 44px;
  text-align: center;
}
.similarity-badge.identical { background: rgba(255, 64, 64, 0.15); color: #ff4d4f; }
.similarity-badge.high { background: rgba(250, 140, 22, 0.15); color: #fa8c16; }
.similarity-badge.medium { background: rgba(24, 144, 255, 0.15); color: #1890ff; }
.similarity-badge.low { background: rgba(82, 196, 26, 0.15); color: #52c41a; }
.merge-confirm {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}
.confirm-label {
  font-size: 12px;
  color: var(--text-secondary);
  white-space: nowrap;
}
.confirm-btns { display: flex; gap: 6px; }
.btn-merge {
  background: #ff4d4f; color: #fff; border: none;
  padding: 4px 12px; border-radius: 4px; cursor: pointer; font-size: 12px;
}
.btn-cancel {
  background: var(--bg-secondary); color: var(--text-secondary); border: 1px solid var(--border);
  padding: 4px 12px; border-radius: 4px; cursor: pointer; font-size: 12px;
}
.loading, .error, .empty {
  text-align: center; padding: 40px; color: var(--text-secondary);
}
.error { color: #ff4d4f; }

/* 历史弹窗 */
.dialog-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center;
  z-index: 1000;
}
.history-dialog {
  background: var(--bg-card); border-radius: 8px; width: 560px; max-height: 80vh;
  display: flex; flex-direction: column;
}
.dialog-header {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px 20px; border-bottom: 1px solid var(--border);
}
.dialog-header h3 { margin: 0; color: var(--text-primary); }
.close-btn {
  background: none; border: none; font-size: 24px; cursor: pointer; color: var(--text-muted);
}
.history-list { max-height: 60vh; overflow-y: auto; padding: 12px 20px; }
.history-item {
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
}
.history-item:last-child { border-bottom: none; }
.history-info {
  display: flex; align-items: center; gap: 8px; margin-bottom: 4px;
}
.history-from { font-weight: 600; color: var(--text-secondary); font-size: 13px; }
.history-arrow { color: var(--accent, #1890ff); font-weight: bold; }
.history-to { font-weight: 600; color: var(--text-primary); font-size: 13px; }
.history-meta { font-size: 11px; color: var(--text-muted); }

@media (max-width: 768px) {
  .pair-info { flex-direction: column; align-items: flex-start; gap: 8px; }
  .merge-arrow { transform: rotate(90deg); }
  .filter-bar { flex-direction: column; align-items: stretch; }
  .search-box { max-width: none; }
}
</style>

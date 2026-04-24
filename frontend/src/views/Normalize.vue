<template>
  <div class="normalize-page">
    <div class="page-header">
      <h1>演员合并</h1>
    </div>

    <!-- Tab 切换 -->
    <div class="tab-bar">
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'javhub' }"
        @click="activeTab = 'javhub'"
      >
        JavHub 映射
      </button>
    </div>

    <!-- ========== JavHub 映射 Tab ========== -->
    <div v-if="activeTab === 'javhub'" class="tab-panel">
      <div class="panel-desc">
        JavHub 本地映射层：只建立演员别名映射关系，<strong>不动电影数据，不碰 JavInfo 数据库</strong>。
        适合"我知道这两个是同一个人，但两边系统里名字不同"的情况。
      </div>

      <div class="filter-bar">
        <div class="search-box">
          <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"/>
            <path d="m21 21-4.35-4.35"/>
          </svg>
          <input v-model="filterName" placeholder="搜索演员名..." class="search-input" @input="onFilterInput" />
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

      <div v-if="loading" class="loading">检测中...</div>
      <div v-else-if="error" class="error">{{ error }}</div>

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
                <img :src="pair.actor_a.avatar_url || ''" :alt="pair.actor_a.actress_name" @error="$event.target.style.display='none'" />
              </div>
              <div class="actor-details">
                <div class="actor-name">{{ pair.actor_a.actress_name }}</div>
                <div class="actor-meta">ID: {{ pair.actor_a.actress_id }} · {{ pair.actor_a.total_videos }} 部</div>
              </div>
            </div>
            <div class="merge-arrow">→</div>
            <div class="actor-cell">
              <div class="actor-cover">
                <img :src="pair.actor_b.avatar_url || ''" :alt="pair.actor_b.actress_name" @error="$event.target.style.display='none'" />
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
              <div class="confirm-btns">
                <button class="btn-merge" @click.stop="mergeJavhub(pair)">映射</button>
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
    </div>

    <!-- 合并历史弹窗 -->
    <div v-if="showHistory" class="dialog-overlay" @click.self="showHistory = false">
      <div class="dialog history-dialog">
        <div class="dialog-header">
          <h3>映射历史</h3>
          <button @click="showHistory = false" class="close-btn">×</button>
        </div>
        <div v-if="loadingHistory" class="loading">加载中...</div>
        <div v-else-if="mergeHistory.length === 0" class="empty">暂无映射记录</div>
        <div v-else class="history-list">
          <div v-for="h in mergeHistory" :key="h.id" class="history-item">
            <div class="history-info">
              <span class="history-from">{{ h.from_name }}</span>
              <span class="history-arrow">→</span>
              <span class="history-to">{{ h.to_name }}</span>
              <span class="history-type">({{ h.type }})</span>
            </div>
            <div class="history-meta">{{ h.created_at }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const activeTab = ref('javhub')

// ---- JavHub 映射 ----
const similarPairs = ref([])
const loading = ref(false)
const error = ref('')
const filterName = ref('')
const threshold = ref(0.8)
const selectedPair = ref(null)

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

let filterTimer = null
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

const mergeJavhub = async (pair) => {
  if (!confirm(`确认在 JavHub 中建立映射关系？\n\n"${pair.actor_a.actress_name}" (ID:{{ pair.actor_a.actress_id }})\n  → "${pair.actor_b.actress_name}" (ID:{{ pair.actor_b.actress_id }})\n\n此操作只建立映射，不移动电影，不修改 JavInfo 数据。`)) {
    selectedPair.value = null
    return
  }
  try {
    await axios.post('/api/inventory/actors/merge-javhub', {
      from_actress_id: pair.actor_a.actress_id,
      to_actress_id: pair.actor_b.actress_id
    })
    alert('JavHub 映射建立成功')
    selectedPair.value = null
    await loadSimilar()
  } catch (e) {
    alert('映射失败: ' + e.message)
  }
}

// ---- 映射历史 ----
const showHistory = ref(false)
const mergeHistory = ref([])
const loadingHistory = ref(false)

const fetchHistory = async () => {
  loadingHistory.value = true
  try {
    const res = await axios.get('/api/inventory/aliases')
    mergeHistory.value = (res.data.data || []).map(a => ({
      id: a.id,
      from_id: a.alias_id,
      to_id: a.canonical_id,
      from_name: a.alias_name || `ID:${a.alias_id}`,
      to_name: a.canonical_name || `ID:${a.canonical_id}`,
      created_at: a.created_at || '',
      type: 'javhub_mapping'
    }))
  } catch (e) {
    console.error('load history failed:', e)
  } finally {
    loadingHistory.value = false
  }
}

onMounted(() => {
  loadSimilar()
})
</script>

<style scoped>
.normalize-page { padding: 16px; }
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-header h1 { margin: 0; font-size: 20px; }

.tab-bar {
  display: flex;
  gap: 4px;
  border-bottom: 2px solid var(--border);
  margin-bottom: 16px;
}
.tab-btn {
  padding: 8px 20px;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  cursor: pointer;
  font-size: 14px;
  color: var(--text-secondary);
  transition: all 0.2s;
}
.tab-btn:hover { color: var(--text-primary); }
.tab-btn.active {
  color: var(--accent, #1890ff);
  border-bottom-color: var(--accent, #1890ff);
  font-weight: 600;
}

.panel-desc {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 12px 16px;
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 16px;
  line-height: 1.6;
}
.panel-desc strong { color: var(--text-primary); }

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
.search-icon { width: 18px; height: 18px; color: var(--text-muted); flex-shrink: 0; }
.search-input {
  flex: 1; border: none; outline: none; padding: 8px;
  font-size: 14px; background: transparent; color: var(--text-primary);
}
.search-clear {
  background: none; border: none; color: var(--text-muted);
  cursor: pointer; font-size: 18px; padding: 0 4px;
}
.threshold-control { display: flex; align-items: center; gap: 6px; }
.threshold-control label { font-size: 13px; color: var(--text-secondary); white-space: nowrap; }
.filter-select {
  padding: 6px 10px; border: 1px solid var(--border);
  border-radius: 4px; background: var(--bg-card); color: var(--text-primary);
  font-size: 13px; cursor: pointer;
}
.result-count { font-size: 13px; color: var(--text-secondary); white-space: nowrap; }

/* JavHub 映射列表 */
.pairs-list { display: flex; flex-direction: column; gap: 8px; }
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
.pair-card.selected { border-color: var(--accent, #1890ff); background: color-mix(in srgb, var(--accent, #1890ff) 6%, var(--bg-card)); }
.pair-info { display: flex; align-items: center; gap: 16px; flex: 1; }
.actor-cell { display: flex; align-items: center; gap: 10px; flex: 1; min-width: 0; }
.actor-cover {
  width: 40px; height: 53px; border-radius: 4px;
  overflow: hidden; background: var(--bg-secondary); flex-shrink: 0;
}
.actor-cover img { width: 100%; height: 100%; object-fit: cover; }
.actor-details { min-width: 0; }
.actor-name {
  font-weight: 600; font-size: 14px; color: var(--text-primary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.actor-meta { font-size: 11px; color: var(--text-muted); margin-top: 2px; }
.merge-arrow { font-size: 18px; color: var(--accent, #1890ff); flex-shrink: 0; font-weight: bold; }
.pair-right { display: flex; align-items: center; gap: 12px; flex-shrink: 0; }
.similarity-badge {
  font-size: 12px; font-weight: bold; padding: 3px 8px;
  border-radius: 10px; min-width: 44px; text-align: center;
}
.similarity-badge.identical { background: rgba(255,64,64,0.15); color: #ff4d4f; }
.similarity-badge.high { background: rgba(250,140,22,0.15); color: #fa8c16; }
.similarity-badge.medium { background: rgba(24,144,255,0.15); color: #1890ff; }
.similarity-badge.low { background: rgba(82,196,26,0.15); color: #52c41a; }
.merge-confirm { display: flex; align-items: center; gap: 6px; }
.confirm-btns { display: flex; gap: 6px; }
.btn-merge {
  background: #ff4d4f; color: #fff; border: none;
  padding: 4px 12px; border-radius: 4px; cursor: pointer; font-size: 12px;
}
.btn-cancel {
  background: var(--bg-secondary); color: var(--text-secondary);
  border: 1px solid var(--border); padding: 4px 12px;
  border-radius: 4px; cursor: pointer; font-size: 12px;
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
.history-item { padding: 10px 0; border-bottom: 1px solid var(--border); }
.history-item:last-child { border-bottom: none; }
.history-info { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.history-from { font-weight: 600; color: var(--text-secondary); font-size: 13px; }
.history-arrow { color: var(--accent, #1890ff); font-weight: bold; }
.history-to { font-weight: 600; color: var(--text-primary); font-size: 13px; }
.history-type { font-size: 11px; color: var(--text-muted); }
.history-meta { font-size: 11px; color: var(--text-muted); }

@media (max-width: 768px) {
  .pair-info { flex-direction: column; align-items: flex-start; gap: 8px; }
  .merge-arrow { transform: rotate(90deg); }
  .filter-bar { flex-direction: column; align-items: stretch; }
  .search-box { max-width: none; }
}
</style>

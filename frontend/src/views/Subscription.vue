<template>
  <div class="subscriptions">
    <!-- Hero搜索区 -->
    <div class="search-hero">
      <h1 class="hero-title">订阅演员</h1>
      <div class="search-container">
        <div class="search-box">
          <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="11" cy="11" r="8"/>
            <path d="m21 21-4.35-4.35"/>
          </svg>
          <input
            v-model="searchKeyword"
            placeholder="输入演员名称，如 白石茉莉奈"
            @keyup.enter="doSearch"
            class="search-input"
          />
          <button v-if="searchKeyword" class="clear-btn" @click="clearSearch">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="16" height="16">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        <button class="btn btn-primary search-btn" :disabled="searching || !searchKeyword" @click="doSearch">
          <span v-if="searching" class="spinner"></span>
          <span v-else>搜索</span>
        </button>
      </div>
    </div>

    <!-- 搜索结果 -->
    <div v-if="!searching && searchResults.length > 0" class="results-wrap">
      <div class="results-header">
        <span class="results-count">搜索结果 ({{ searchResults.length }})</span>
      </div>
      <div class="results-grid">
        <div
          v-for="actor in searchResults"
          :key="actor.id"
          class="actor-card"
          @click="subscribe(actor)"
        >
          <div class="actor-cover">
            <img
              :src="'/api/actors/avatar/' + encodeURIComponent(actor.name)"
              :alt="actor.name"
              class="actor-cover-img"
              @error="$event.target.style.display='none'"
              loading="lazy"
            />
          </div>
          <div class="actor-body">
            <h3 class="actor-name">{{ actor.name }}</h3>
            <p class="actor-count">{{ actor.movie_count }} 部作品</p>
            <p v-if="actor.star_id" class="actor-star-id">ID: {{ actor.star_id }}</p>
          </div>
          <div class="actor-action">
            <span v-if="isSubscribed(actor.name_kanji || actor.name_en || actor.name)" class="subscribed-tag">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="12" height="12">
                <path d="M20 6L9 17l-5-5"/>
              </svg>
              已订阅
            </span>
            <span v-else class="subscribe-hint">点击订阅</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 加载骨架屏 -->
    <div v-else-if="searching" class="skeleton-wrap">
      <div class="skeleton-grid">
        <div v-for="n in 8" :key="n" class="skeleton-card">
          <div class="skeleton-cover"></div>
          <div class="skeleton-body">
            <div class="skeleton-line w-70"></div>
            <div class="skeleton-line w-50"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- 空结果 -->
    <div v-else-if="searched && searchResults.length === 0" class="empty-wrap">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="48" height="48">
        <circle cx="11" cy="11" r="8"/>
        <path d="m21 21-4.35-4.35"/>
        <line x1="8" y1="11" x2="14" y2="11"/>
      </svg>
      <p>未找到相关演员</p>
      <p class="text-secondary" style="font-size:13px;margin-top:6px">试试其他关键词</p>
    </div>

    <!-- 已订阅列表 -->
    <div class="subscribed-wrap">
      <div class="subscribed-header">
        <span>已订阅 ({{ subs.length }})</span>
      </div>

      <div v-if="loading" class="skeleton-wrap">
        <div class="skeleton-grid">
          <div v-for="n in 4" :key="n" class="skeleton-card">
            <div class="skeleton-cover"></div>
            <div class="skeleton-body">
              <div class="skeleton-line w-70"></div>
              <div class="skeleton-line w-50"></div>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="subs.length > 0" class="subs-grid">
        <div v-for="sub in subs" :key="sub.id" class="sub-card">
          <div class="sub-avatar">
            <img
              :src="'/api/actors/avatar/' + encodeURIComponent(sub.actress_name)"
              :alt="sub.actress_name"
              @error="$event.target.style.display='none'"
            />
          </div>
          <div class="sub-body">
            <h3 class="sub-name">{{ sub.actress_name }}</h3>
            <div class="sub-meta">
              <span :class="['badge', sub.enabled ? 'badge-success' : 'badge-pending']">
                {{ sub.enabled ? '监控中' : '已暂停' }}
              </span>
              <span class="text-muted" style="font-size:11px">{{ sub.auto_download ? '自动下载' : '仅通知' }}</span>
            </div>
            <p class="sub-time text-muted" style="font-size:11px">
              {{ sub.last_check ? '检查: ' + sub.last_check : '从未检查' }}
            </p>
          </div>
          <div class="sub-actions">
            <button class="btn btn-primary" style="font-size:12px;padding:6px 10px" @click="checkNow(sub.id)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="13" height="13">
                <polyline points="23 4 23 10 17 10"/>
                <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/>
              </svg>
              检查
            </button>
            <button class="btn btn-ghost" style="font-size:12px;padding:6px 10px" @click="remove(sub.id)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="13" height="13">
                <polyline points="3 6 5 6 21 6"/>
                <path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
              </svg>
              删除
            </button>
          </div>
        </div>
      </div>

      <div v-else class="empty-wrap-small">
        <p>暂无订阅</p>
      </div>
    </div>

    <!-- 检查结果弹窗 -->
    <transition name="modal-fade">
      <div v-if="checkResult" class="modal-overlay" @click.self="checkResult = null">
        <div class="modal-container">
          <div class="modal-header">
            <h3>{{ checkResult.actor_name }}</h3>
            <button class="modal-close" @click="checkResult = null">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="18" height="18">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
          <div class="modal-body">
            <div class="modal-stats">
              <span>最新作品: <strong>{{ checkResult.latest_movies?.length || 0 }}</strong></span>
              <span>新片: <strong style="color:var(--accent)">{{ checkResult.new_movies_count }}</strong></span>
            </div>
            <div v-if="checkResult.new_movies?.length" class="modal-list">
              <div v-for="movie in checkResult.new_movies" :key="movie.code" class="modal-item">
                <div class="modal-item-info">
                  <span class="modal-code">{{ movie.code }}</span>
                  <span class="modal-title">{{ movie.title }}</span>
                </div>
                <button class="btn btn-primary" style="font-size:12px;padding:5px 10px" @click="downloadMovie(movie)">下载</button>
              </div>
            </div>
            <div v-else class="text-secondary" style="text-align:center;padding:20px">暂无非下载的新片</div>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script>
import api from '../api'

export default {
  name: 'Subscriptions',
  data() {
    return {
      subs: [],
      searchKeyword: '',
      searchResults: [],
      searching: false,
      searched: false,
      loading: false,
      checkResult: null
    }
  },
  mounted() {
    this.loadSubs()
  },
  methods: {
    async loadSubs() {
      this.loading = true
      try {
        const resp = await api.getSubscriptions()
        this.subs = resp.data
      } catch (e) {
        console.error('Failed to load subscriptions:', e)
      } finally {
        this.loading = false
      }
    },
    async doSearch() {
      if (!this.searchKeyword.trim()) return
      this.searching = true
      this.searched = true
      this.searchResults = []
      try {
        const resp = await api.searchActors(this.searchKeyword.trim())
        this.searchResults = resp.data?.data || resp.data || []
      } catch (e) {
        console.error('Search actors failed:', e)
      } finally {
        this.searching = false
      }
    },
    clearSearch() {
      this.searchKeyword = ''
      this.searchResults = []
      this.searched = false
    },
    async subscribe(actor) {
      const name = actor.name_kanji || actor.name_en || actor.name || ''
      if (this.isSubscribed(name)) return
      try {
        await api.addSubscription({
          actress_id: actor.id || 0,
          actress_name: name,
        })
        this.$message?.success(`已订阅 ${name}`)
        this.loadSubs()
      } catch (e) {
        console.error('Subscribe failed:', e)
        this.$message?.error('订阅失败')
      }
    },
    isSubscribed(actressName) {
      return this.subs.some(s => s.actress_name === actressName)
    },
    async remove(id) {
      try {
        await api.deleteSubscription(id)
        this.$message.success('已删除')
        this.loadSubs()
      } catch (e) {
        console.error('Delete failed:', e)
      }
    },
    async checkNow(id) {
      try {
        const resp = await api.checkSubscription(id)
        this.checkResult = resp.data
      } catch (e) {
        console.error('Check failed:', e)
        this.$message?.error('检查失败')
      }
    },
    async downloadMovie(movie) {
      try {
        await api.createDownload({ code: movie.code, title: movie.title, magnet: '' })
        this.$message.success('已添加到下载队列')
      } catch (e) {
        console.error('Download failed:', e)
      }
    }
  }
}
</script>

<style scoped>
.subscriptions { padding: 24px 24px 60px; max-width: 1100px; margin: 0 auto; }

/* ===== Hero ===== */
.search-hero {
  text-align: center;
  padding: 48px 20px 36px;
  background: var(--bg-primary);
  margin: -24px -24px 0;
}
.hero-title {
  font-size: 36px; font-weight: 700; color: var(--text-primary);
  margin-bottom: 24px; letter-spacing: -0.02em;
}
.search-container { display: flex; gap: 10px; max-width: 560px; margin: 0 auto; }
.search-box {
  flex: 1; position: relative; display: flex; align-items: center;
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: var(--radius-md); padding: 0 14px;
  transition: border-color 0.2s;
}
.search-box:focus-within { border-color: var(--accent); }
.search-icon { width: 18px; height: 18px; color: var(--text-muted); flex-shrink: 0; }
.search-input {
  flex: 1; border: none; outline: none;
  padding: 12px 10px; font-size: 15px;
  background: transparent; color: var(--text-primary);
}
.search-input::placeholder { color: var(--text-muted); }
.clear-btn {
  background: none; border: none; padding: 4px; cursor: pointer;
  color: var(--text-muted); display: flex; align-items: center;
}
.clear-btn:hover { color: var(--text-primary); }
.search-btn { min-width: 80px; justify-content: center; font-size: 14px; padding: 12px 16px; }

/* ===== Results ===== */
.results-wrap { margin-top: 28px; }
.results-header { margin-bottom: 14px; }
.results-count { font-size: 13px; font-weight: 600; color: var(--text-secondary); }
.results-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
}

/* Actor Card */
.actor-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;
}
.actor-card:hover {
  border-color: var(--accent);
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(0,0,0,0.4);
}
.actor-cover {
  width: 100%;
  aspect-ratio: 2/3;
  background: var(--bg-secondary);
  overflow: hidden;
}
.actor-cover-img {
  width: 100%; height: 100%; object-fit: cover;
  transition: transform 0.3s;
}
.actor-card:hover .actor-cover-img { }
.actor-body { padding: 10px 12px 6px; }
.actor-name {
  font-size: 13px; font-weight: 600; color: var(--text-primary);
  margin-bottom: 3px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.actor-count { font-size: 11px; color: var(--text-muted); margin-bottom: 2px; }
.actor-star-id { font-size: 10px; color: var(--text-muted); }
.actor-action {
  padding: 6px 12px 10px;
  display: flex; align-items: center; justify-content: center;
}
.subscribe-hint {
  font-size: 11px; color: var(--accent); font-weight: 500;
}
.subscribed-tag {
  display: flex; align-items: center; gap: 4px;
  font-size: 11px; color: var(--text-muted);
}

/* ===== Skeleton ===== */
.skeleton-wrap { margin-top: 28px; }
.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
}
.skeleton-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  overflow: hidden;
}
.skeleton-cover {
  width: 100%;
  aspect-ratio: 2/3;
  background: var(--bg-card-hover);
  position: relative;
  overflow: hidden;
}
.skeleton-cover::after {
  content: "";
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, transparent, var(--white-06), transparent);
  transform: translateX(-100%);
  animation: shimmer 2s infinite;
}
.skeleton-body { padding: 10px 12px; }
.skeleton-line {
  height: 10px; background: var(--bg-card-hover);
  border-radius: 5px; margin-bottom: 8px;
}
.skeleton-line.w-70 { width: 70%; }
.skeleton-line.w-50 { width: 50%; }
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* ===== Empty ===== */
.empty-wrap {
  text-align: center; padding: 60px 20px;
  color: var(--text-secondary);
  display: flex; flex-direction: column; align-items: center; gap: 10px;
}
.empty-wrap svg { opacity: 0.4; }
.empty-wrap-small {
  text-align: center; padding: 30px;
  color: var(--text-muted); font-size: 14px;
}

/* ===== Subscribed ===== */
.subscribed-wrap { margin-top: 36px; }
.subscribed-header {
  font-size: 14px; font-weight: 600; color: var(--text-secondary);
  margin-bottom: 14px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}
.subs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 12px;
}
.sub-card {
  display: flex; gap: 0; overflow: hidden;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 0;
}
.sub-avatar {
  width: 80px; min-width: 80px;
  background: var(--bg-secondary);
  overflow: hidden;
}
.sub-avatar img {
  width: 100%; height: 100%; object-fit: cover;
}
.sub-body {
  flex: 1; padding: 12px 14px; min-width: 0;
  display: flex; flex-direction: column; justify-content: center;
}
.sub-name {
  font-size: 14px; font-weight: 600; color: var(--text-primary);
  margin-bottom: 5px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.sub-meta { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.sub-time { margin-top: 2px; }
.sub-actions {
  display: flex; flex-direction: column; gap: 6px;
  justify-content: center;
  padding: 10px 10px;
  border-left: 1px solid var(--border);
}
.sub-actions .btn { justify-content: center; }

/* ===== Modal ===== */
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.7); backdrop-filter: blur(8px);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000; padding: 20px;
}
.modal-container {
  background: var(--bg-card); border: 1px solid var(--border);
  border-radius: var(--radius-lg); width: 100%; max-width: 480px;
  max-height: 80vh; overflow: hidden;
  box-shadow: 0 25px 80px rgba(0,0,0,0.6);
}
.modal-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 20px; border-bottom: 1px solid var(--border);
}
.modal-header h3 { font-size: 16px; font-weight: 600; color: var(--text-primary); }
.modal-close {
  background: none; border: none; cursor: pointer;
  color: var(--text-secondary); display: flex; padding: 4px;
  border-radius: 6px;
}
.modal-close:hover { color: white; background: rgba(255,255,255,0.08); }
.modal-body { padding: 16px 20px; overflow-y: auto; max-height: 60vh; }
.modal-stats { display: flex; gap: 20px; font-size: 14px; color: var(--text-secondary); margin-bottom: 14px; }
.modal-stats strong { color: var(--text-primary); }
.modal-list { display: flex; flex-direction: column; gap: 8px; }
.modal-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 10px 12px; background: var(--bg-secondary);
  border-radius: var(--radius-sm); gap: 12px;
}
.modal-item-info { display: flex; align-items: center; gap: 10px; min-width: 0; flex: 1; }
.modal-code { font-size: 13px; font-weight: 600; color: var(--accent); flex-shrink: 0; }
.modal-title { font-size: 12px; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* Modal Transition */
.modal-fade-enter-active .modal-container { animation: modalIn 0.35s cubic-bezier(0.32, 0.72, 0, 1); }
.modal-fade-leave-active .modal-container { animation: modalOut 0.2s ease; }
.modal-fade-enter-active { animation: fadeIn 0.25s ease; }
.modal-fade-leave-active { animation: fadeIn 0.2s ease reverse; }
@keyframes modalIn { from { transform: scale(0.9); opacity: 0; } to { transform: scale(1); opacity: 1; } }
@keyframes modalOut { from { transform: scale(1); opacity: 1; } to { transform: scale(0.94); opacity: 0; } }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

/* ===== Responsive ===== */
@media (max-width: 768px) {
  .subscriptions { padding: 16px 16px 80px; }
  .search-hero { padding: 32px 16px 24px; margin: -16px -16px 0; }
  .hero-title { font-size: 26px; }
  .search-container { flex-direction: column; }
  .results-grid { grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 12px; }
  .skeleton-grid { grid-template-columns: repeat(auto-fill, minmax(130px, 1fr)); gap: 12px; }
  .subs-grid { grid-template-columns: 1fr; }
  .sub-card { flex-direction: column; }
  .sub-avatar { width: 100%; height: 80px; min-width: unset; }
  .sub-actions { flex-direction: row; border-left: none; border-top: 1px solid var(--border); }
}
</style>

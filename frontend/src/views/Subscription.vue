<template>
  <div class="sub-page">
    <!-- Hero -->
    <div class="sub-hero">
      <h1 class="hero-title">订阅演员</h1>
      <div class="segmented-control">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          class="segment-item"
          :class="{ active: activeTab === tab.id }"
          @click="switchTab(tab.id)"
        >
          {{ tab.label }}
          <span v-if="tab.badge > 0" class="tab-badge">{{ tab.badge }}</span>
        </button>
      </div>
    </div>

    <!-- ===== 发现 Tab ===== -->
    <div v-show="activeTab === 'discover'" class="tab-content">
      <div class="search-bar-wrap">
        <div class="search-bar">
          <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
          </svg>
          <input v-model="searchKeyword" placeholder="搜索演员名称" class="search-input" @keyup.enter="doSearch" />
          <button v-if="searchKeyword" class="clear-btn" @click="clearSearch">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14">
              <circle cx="12" cy="12" r="10"/><path d="m15 9-6 6M9 9l6 6"/>
            </svg>
          </button>
        </div>
      </div>

      <div v-if="searching" class="card-grid">
        <div v-for="n in 8" :key="n" class="skel-card"><div class="skel-cover"></div><div class="skel-info"><div class="skel-line w60"></div><div class="skel-line w40"></div></div></div>
      </div>

      <div v-else-if="searchResults.length > 0" class="card-grid">
        <ActressCard
          v-for="actor in searchResults"
          :key="actor.id"
          :coverUrl="avatarSrc(actor)"
          :name="displayName(actor, 'name_kanji', 'name_romaji') || '未知'"
          :originalName="actor.name_kanji || actor.name_romaji || ''"
          :totalCount="actor.movie_count"
          :subscribed="isSubscribed(actor.id)"
          @click="openActorSheet(actor)"
        />
      </div>

      <div v-else-if="searched && searchResults.length === 0" class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" width="48" height="48"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/><path d="M8 11h6"/></svg>
        <p>未找到相关演员</p>
      </div>
    </div>

    <!-- ===== 已订阅 Tab ===== -->
    <div v-show="activeTab === 'subscribed'" class="tab-content">
      <div v-if="loading" class="card-grid">
        <div v-for="n in 6" :key="n" class="skel-card"><div class="skel-cover"></div><div class="skel-info"><div class="skel-line w60"></div><div class="skel-line w40"></div></div></div>
      </div>

      <div v-else-if="subs.length > 0" class="card-grid">
        <ActressCard
          v-for="sub in subs"
          :key="sub.id"
          :coverUrl="subCoverUrl(sub)"
          :name="subDisplayName(sub)"
          :originalName="subOriginalName(sub)"
          :totalCount="subMeta(sub)?.movie_count ?? null"
          :subscribed="true"
          @click="openSubSheet(sub)"
        />
      </div>

      <div v-else class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" width="48" height="48"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/></svg>
        <p>还没有订阅任何演员</p>
        <button class="pill-btn pill-btn-primary" style="margin-top:16px" @click="activeTab = 'discover'">去发现</button>
      </div>
    </div>

    <!-- ===== Detail Sheet ===== -->
    <teleport to="body">
      <transition name="sheet">
        <div v-if="sheetActor" class="sheet-overlay" @click.self="closeSheet">
          <div class="sheet" @click.stop>
            <!-- Top Bar: grabber + actions -->
            <div class="sheet-top-bar">
              <div class="sheet-grabber"></div>
              <div v-if="sheetSub" class="sheet-top-actions">
                <button class="top-action-btn" @click="checkNow(sheetSub)" :disabled="checkingId === sheetSub.id">
                  <span v-if="checkingId === sheetSub.id" class="spinner-tiny"></span>
                  <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/></svg>
                  立即检查
                </button>
                <button class="top-action-btn danger" @click="remove(sheetSub.id)">取消订阅</button>
              </div>
            </div>

            <!-- Avatar -->
            <div class="sheet-avatar-wrap">
              <div class="sheet-avatar-glow"></div>
              <div class="sheet-avatar">
                <img v-if="sheetCoverUrl" :src="sheetCoverUrl" :alt="sheetActor.name_kanji" @error="$event.target.style.display='none'" />
                <span v-else class="avatar-fallback">{{ (sheetActor.name_kanji || '?')[0] }}</span>
              </div>
            </div>

            <!-- Translated Name -->
            <div v-if="sheetTranslatedName" class="sheet-translated">{{ sheetTranslatedName }}</div>
            <!-- Name pills row -->
            <div class="sheet-name-row">
              <span v-if="sheetActor.name_kanji" class="name-pill">{{ sheetActor.name_kanji }}</span>
              <span v-if="sheetActor.name_romaji" class="name-pill">{{ sheetActor.name_romaji }}</span>
              <span v-if="sheetActor.name_kana" class="name-pill dim">{{ sheetActor.name_kana }}</span>
            </div>

            <!-- Stats -->
            <div v-if="sheetActor.movie_count != null" class="sheet-stat-line">
              {{ sheetActor.movie_count.toLocaleString() }} 部作品
            </div>

            <!-- Toggle Pills + 全部作品 -->
            <div class="sheet-toggles">
              <button v-if="sheetSub" class="toggle-pill" :class="{ on: sheetSub.enabled }" @click="toggleEnabled(sheetSub)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                监控
              </button>
              <button v-if="sheetSub" class="toggle-pill" :class="{ on: sheetSub.auto_download }" @click="toggleAutoDownload(sheetSub)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                自动下载
              </button>
              <button class="toggle-pill" @click="viewAllVideos">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><path d="M4 19.5A2.5 2.5 0 016.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/></svg>
                全部作品
              </button>
            </div>

            <!-- Works: MovieCard grid (random) -->
            <div v-if="sheetMovies.length > 0" class="sheet-works">
              <div class="works-grid">
                <div v-for="movie in sheetMovies" :key="movie.content_id || movie.dvd_id" class="work-card-wrap">
                  <MovieCard
                    :contentId="movie.dvd_id || movie.content_id"
                    :coverUrl="movieCoverUrl(movie)"
                    :title="movie.title_en || movie.title_ja || ''"
                    :serviceCode="movie.service_code || ''"
                    :releaseDate="movie.release_date || ''"
                    :runtimeMins="movie.runtime_mins || ''"
                    :sampleUrl="movie.sample_url || ''"
                    :isFavorited="false"
                    @click="openVideoModal(movie)"
                  />
                  <button class="work-dl-btn" @click.stop="downloadMovie(movie)" title="下载">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" width="14" height="14"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                  </button>
                </div>
              </div>
            </div>
            <div v-else-if="sheetLoading" class="sheet-loading"><div class="spinner-small"></div></div>

            <!-- Bottom action for discover -->
            <div v-if="!sheetSub" class="sheet-bottom-action">
              <button v-if="!isSubscribed(sheetActor.id)" class="action-btn primary" :disabled="subscribing" @click="subscribeFromSheet">
                {{ subscribing ? '订阅中...' : '订阅' }}
              </button>
              <button v-else class="action-btn" disabled>已订阅</button>
            </div>
          </div>
        </div>
      </transition>
    </teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '../api'
import { actressImgUrl, jacketHdUrl } from '../utils/imageUrl.js'
import { openVideoModal as openVideoModalFn } from '../utils/modalState.js'
import { displayName } from '../utils/displayLang.js'
import ActressCard from '../components/ActressCard.vue'
import MovieCard from '../components/MovieCard.vue'

const router = useRouter()

const activeTab = ref('discover')
const searchKeyword = ref('')
const searchResults = ref([])
const searching = ref(false)
const searched = ref(false)

const subs = ref([])
const loading = ref(false)
const checkingId = ref(null)

const sheetActor = ref(null)
const sheetSub = ref(null)
const sheetMovies = ref([])
const sheetLoading = ref(false)
const subscribing = ref(false)

const newMovieMap = ref({})
const actressMetaMap = ref({})

const totalNewMovies = computed(() => {
  let c = 0
  for (const m of Object.values(newMovieMap.value)) c += m.length
  return c
})

const tabs = computed(() => [
  { id: 'discover', label: '发现', badge: 0 },
  { id: 'subscribed', label: '已订阅', badge: totalNewMovies.value },
])

const sheetCoverUrl = computed(() => {
  if (!sheetActor.value) return ''
  return actressImgUrl(sheetActor.value.image_url) || ''
})

const sheetTranslatedName = computed(() => {
  if (!sheetActor.value) return ''
  return displayName(sheetActor.value, 'name_kanji', 'name_romaji') || ''
})

function avatarSrc(actor) { return actressImgUrl(actor.image_url) || '' }
function subCoverUrl(sub) { const m = actressMetaMap.value[sub.actress_id]; return m?.image_url ? actressImgUrl(m.image_url) : '' }
function subMeta(sub) { return actressMetaMap.value[sub.actress_id] || null }
function isSubscribed(actressId) { return subs.value.some(s => s.actress_id === actressId) }
function subDisplayName(sub) {
  const meta = actressMetaMap.value[sub.actress_id]
  if (meta) { const n = displayName(meta, 'name_kanji', 'name_romaji'); if (n) return n }
  return sub.actress_name || '未知'
}
function subOriginalName(sub) {
  const meta = actressMetaMap.value[sub.actress_id]
  return meta?.name_kanji || sub.actress_name || ''
}
function newMovieCount(actressId) { return (newMovieMap.value[actressId] || []).length }
function movieCoverUrl(movie) { return jacketHdUrl(movie.jacket_thumb_url) || movie.jacket_thumb_url || '' }

function shuffleArray(arr) {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]] }
  return a
}

function switchTab(tab) { activeTab.value = tab; if (tab === 'subscribed' && subs.value.length) loadNewMovieBadges() }

// ===== Search =====
async function doSearch() {
  const q = searchKeyword.value.trim(); if (!q) return
  searching.value = true; searched.value = true; searchResults.value = []
  try { const r = await api.searchActors(q); searchResults.value = r.data?.data || r.data || [] }
  catch (e) { console.error(e) } finally { searching.value = false }
}

function clearSearch() { searchKeyword.value = ''; searchResults.value = []; searched.value = false }

// ===== Sheet =====
async function openActorSheet(actor) {
  sheetActor.value = actor; sheetSub.value = null
  sheetMovies.value = []; sheetLoading.value = true
  try {
    const r = await api.getActressVideos(actor.id, 1, 30)
    const all = r.data?.data || []
    sheetMovies.value = shuffleArray(all).slice(0, 12)
  } catch (e) { console.error(e) } finally { sheetLoading.value = false }
}

async function openSubSheet(sub) {
  const meta = actressMetaMap.value[sub.actress_id]
  sheetActor.value = { id: sub.actress_id, name_kanji: sub.actress_name, image_url: meta?.image_url || '', movie_count: meta?.movie_count, name_romaji: meta?.name_romaji, name_kana: meta?.name_kana, name_kanji_translated: meta?.name_kanji_translated || '', name_romaji_translated: meta?.name_romaji_translated || '' }
  sheetSub.value = sub
  sheetMovies.value = []; sheetLoading.value = true
  try {
    const r = await api.getActressVideos(sub.actress_id, 1, 30)
    const all = r.data?.data || []
    sheetMovies.value = shuffleArray(all).slice(0, 12)
  } catch (e) { console.error(e) } finally { sheetLoading.value = false }
}

function closeSheet() { sheetActor.value = null; sheetSub.value = null; sheetMovies.value = [] }

function viewAllVideos() {
  if (!sheetActor.value) return
  const name = sheetActor.value.name_kanji || sheetActor.value.name_romaji || ''
  router.push({ path: `/actor/${encodeURIComponent(name)}`, query: { name } })
}

function openVideoModal(movie) { openVideoModalFn(movie, router.currentRoute.value.path) }

async function subscribeFromSheet() {
  if (!sheetActor.value) return
  const a = sheetActor.value; const name = a.name_kanji || a.name_romaji || ''
  subscribing.value = true
  try { await api.addSubscription({ actress_id: a.id, actress_name: name }); ElMessage.success(`已订阅 ${name}`); await loadSubs(); closeSheet() }
  catch (e) { ElMessage.error('订阅失败') } finally { subscribing.value = false }
}

// ===== Subscriptions =====
async function loadSubs() {
  loading.value = true
  try { const r = await api.getSubscriptions(); subs.value = r.data?.data || r.data || []; await enrichActressMeta() }
  catch (e) { console.error(e) } finally { loading.value = false }
}

async function enrichActressMeta() {
  const ids = subs.value.filter(s => s.actress_id).map(s => s.actress_id)
  if (!ids.length) return
  const map = {}; const sem = { count: 0 }
  const fetchOne = async (id) => {
    while (sem.count >= 8) await new Promise(r => setTimeout(r, 50))
    sem.count++
    try { const r = await api.getActress(id); return { id, data: r.data || r } }
    catch { return { id, data: null } } finally { sem.count-- }
  }
  const results = await Promise.all(ids.map(fetchOne))
  for (const { id, data } of results) { if (data) map[id] = data }
  actressMetaMap.value = map
}

async function loadNewMovieBadges() {
  try { const r = await api.getNewMovies(); newMovieMap.value = r.data?.data || {} }
  catch (e) { console.error(e) }
}

async function checkNow(sub) {
  checkingId.value = sub.id
  try {
    const r = await api.checkSubscription(sub.id)
    if (r.data.new_movies_count > 0) ElMessage.success(`发现 ${r.data.new_movies_count} 部新片`)
    else ElMessage.info('暂无新片')
    await loadSubs(); await loadNewMovieBadges()
  } catch (e) { ElMessage.error('检查失败') } finally { checkingId.value = null }
}

async function toggleEnabled(sub) {
  try { await api.updateSubscription(sub.id, { enabled: !sub.enabled }); sub.enabled = !sub.enabled }
  catch (e) { ElMessage.error('操作失败') }
}

async function toggleAutoDownload(sub) {
  try { await api.updateSubscription(sub.id, { auto_download: !sub.auto_download }); sub.auto_download = !sub.auto_download }
  catch (e) { ElMessage.error('操作失败') }
}

async function remove(id) {
  try { await api.deleteSubscription(id); subs.value = subs.value.filter(s => s.id !== id); closeSheet(); ElMessage.success('已取消订阅') }
  catch (e) { ElMessage.error('删除失败') }
}

async function downloadMovie(movie) {
  try { await api.createDownload({ code: movie.dvd_id || movie.content_id, title: movie.title_en || movie.title_ja || '', magnet: '' }); ElMessage.success('已添加到下载队列') }
  catch (e) { ElMessage.error('下载失败') }
}

onMounted(loadSubs)
watch(activeTab, (tab) => { if (tab === 'subscribed' && subs.value.length) loadNewMovieBadges() })
</script>

<style scoped>
.sub-page {
  padding: 0 0 60px;
  max-width: 960px;
  margin: 0 auto;
  min-height: 100vh;
}

.sub-hero { text-align: center; padding: 40px 20px 20px; }

.hero-title {
  font-size: 34px; font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.03em;
  margin-bottom: 20px;
}

/* ===== Segmented Control ===== */
.segmented-control {
  display: inline-flex;
  background: rgba(255, 255, 255, 0.04);
  padding: 3px;
  border-radius: 12px;
  backdrop-filter: blur(40px) saturate(200%);
  -webkit-backdrop-filter: blur(40px) saturate(200%);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.segment-item {
  border: none; background: transparent;
  color: var(--text-secondary);
  padding: 7px 20px; font-size: 13px; font-weight: 600;
  border-radius: 9px; cursor: pointer;
  transition: all 0.25s cubic-bezier(0.23, 1, 0.32, 1);
  display: inline-flex; align-items: center; gap: 6px;
}

.segment-item:hover { color: var(--text-primary); }

.segment-item.active {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.3);
}

.tab-badge {
  font-size: 10px; background: #FF375F; color: #fff;
  padding: 1px 5px; border-radius: 8px;
  font-weight: 700; min-width: 16px; text-align: center;
}

.tab-content { padding: 0 16px; animation: fadeIn 0.2s ease; }

/* ===== Search Bar ===== */
.search-bar-wrap { margin-bottom: 20px; }

.search-bar {
  display: flex; align-items: center;
  background: rgba(255, 255, 255, 0.04);
  backdrop-filter: blur(40px) saturate(200%);
  -webkit-backdrop-filter: blur(40px) saturate(200%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 14px; padding: 0 14px; height: 44px;
  transition: border-color 0.3s, box-shadow 0.3s;
}

.search-bar:focus-within {
  border-color: rgba(255, 255, 255, 0.15);
  box-shadow: 0 0 0 4px rgba(255, 255, 255, 0.03);
}

.search-icon { width: 16px; height: 16px; color: var(--text-muted); flex-shrink: 0; }

.search-input {
  flex: 1; border: none; outline: none; background: transparent;
  padding: 0 10px; font-size: 15px; color: var(--text-primary); height: 100%;
}

.search-input::placeholder { color: var(--text-muted); }

.clear-btn {
  background: none; border: none; padding: 4px; cursor: pointer;
  color: var(--text-muted); display: flex; align-items: center; border-radius: 50%;
  transition: background 0.15s;
}

.clear-btn:hover { background: rgba(255, 255, 255, 0.08); color: var(--text-secondary); }

/* ===== Card Grid ===== */
.card-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 14px;
}

/* ===== Skeleton ===== */
.skel-card {
  border-radius: 16px; overflow: hidden;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(80px) saturate(200%);
  -webkit-backdrop-filter: blur(80px) saturate(200%);
}

.skel-cover {
  aspect-ratio: 3/4;
  background: rgba(255, 255, 255, 0.03);
  animation: pulse 1.5s ease-in-out infinite;
}

.skel-info {
  padding: 10px 12px 14px;
  display: flex; flex-direction: column; gap: 6px;
}

.skel-line {
  height: 12px;
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.05);
  animation: pulse 1.5s ease-in-out infinite;
}

.skel-line.w60 { width: 60%; }
.skel-line.w40 { width: 40%; }

@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

/* ===== Pill Button ===== */
.pill-btn {
  display: inline-flex; align-items: center; justify-content: center;
  height: 28px; padding: 0 14px; border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-primary); font-size: 12px; font-weight: 600;
  cursor: pointer; flex-shrink: 0;
  transition: all 0.2s cubic-bezier(0.23, 1, 0.32, 1);
}

.pill-btn:hover { background: rgba(255, 255, 255, 0.1); }

.pill-btn-primary {
  background: var(--accent); color: var(--bg-primary); border-color: transparent;
}

.pill-btn-primary:hover { background: var(--accent-light); }

/* ===== Empty State ===== */
.empty-state {
  text-align: center; padding: 80px 20px;
  display: flex; flex-direction: column; align-items: center; gap: 10px;
  color: var(--text-secondary);
}

.empty-state svg { opacity: 0.3; margin-bottom: 8px; }
.empty-state p { margin: 0; font-size: 15px; }

/* ===== Spinners ===== */
.spinner-small {
  width: 20px; height: 20px;
  border: 2px solid var(--border); border-top-color: var(--text-primary);
  border-radius: 50%; animation: spin 0.6s linear infinite;
}

.spinner-tiny {
  width: 14px; height: 14px;
  border: 1.5px solid var(--border); border-top-color: var(--text-primary);
  border-radius: 50%; animation: spin 0.6s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* ================================================================
   SHEET — iOS 26 Liquid Glass
   ================================================================ */
.sheet-overlay {
  position: fixed; inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(12px) saturate(150%);
  -webkit-backdrop-filter: blur(12px) saturate(150%);
  z-index: 900;
  display: flex; align-items: flex-end; justify-content: center;
}

.sheet {
  width: 90vw; max-width: 960px; max-height: 92vh;
  background: rgba(22, 22, 24, 0.85);
  backdrop-filter: blur(80px) saturate(200%);
  -webkit-backdrop-filter: blur(80px) saturate(200%);
  border-radius: 24px 24px 0 0;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-bottom: none;
  overflow-y: auto; overflow-x: hidden;
}

/* Top Bar */
.sheet-top-bar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 20px 0;
  position: sticky; top: 0; z-index: 5;
  background: rgba(22, 22, 24, 0.7);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}

.sheet-grabber {
  width: 36px; height: 5px;
  background: rgba(255, 255, 255, 0.15);
  border-radius: 3px;
}

.sheet-top-actions { display: flex; gap: 8px; }

.top-action-btn {
  display: inline-flex; align-items: center; gap: 5px;
  height: 32px; padding: 0 14px; border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-secondary);
  font-size: 12px; font-weight: 600;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.23, 1, 0.32, 1);
}

.top-action-btn:hover { background: rgba(255, 255, 255, 0.1); color: var(--text-primary); }
.top-action-btn:active { transform: scale(0.96); }
.top-action-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.top-action-btn.danger { color: #FF375F; border-color: rgba(255, 55, 95, 0.25); }
.top-action-btn.danger:hover { background: rgba(255, 55, 95, 0.1); }

/* Avatar */
.sheet-avatar-wrap {
  display: flex; justify-content: center;
  padding: 24px 0 16px;
  position: relative;
}

.sheet-avatar-glow {
  position: absolute; top: 50%; left: 50%;
  transform: translate(-50%, -50%);
  width: 120px; height: 120px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.08) 0%, transparent 70%);
  filter: blur(30px);
  pointer-events: none;
}

.sheet-avatar {
  width: 96px; height: 96px;
  border-radius: 50%; overflow: hidden;
  background: rgba(255, 255, 255, 0.06);
  border: 2px solid rgba(255, 255, 255, 0.1);
  position: relative;
}

.sheet-avatar img { width: 100%; height: 100%; object-fit: cover; }

.avatar-fallback {
  width: 100%; height: 100%;
  display: flex; align-items: center; justify-content: center;
  font-size: 36px; font-weight: 600; color: var(--text-muted);
}

/* Translated Name */
.sheet-translated {
  text-align: center;
  font-size: 22px; font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.02em;
  padding: 0 20px 8px;
}

/* Name Pills Row */
.sheet-name-row {
  display: flex; align-items: center; justify-content: center;
  flex-wrap: wrap; gap: 6px;
  padding: 0 20px 12px;
}

.name-pill {
  display: inline-flex; align-items: center;
  height: 24px; padding: 0 10px; border-radius: 8px;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.06);
  font-size: 12px; font-weight: 500;
  color: var(--text-secondary);
  white-space: nowrap;
}

.name-pill.dim { color: var(--text-muted); }

/* Stat Line */
.sheet-stat-line {
  text-align: center;
  font-size: 13px; font-weight: 500;
  color: var(--text-secondary);
  padding: 0 20px 16px;
}

/* Toggle Pills */
.sheet-toggles {
  display: flex; justify-content: center; gap: 8px;
  padding: 0 20px 20px;
}

.toggle-pill {
  display: inline-flex; align-items: center; justify-content: center; gap: 5px;
  height: 36px; padding: 0 18px; border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-muted); font-size: 13px; font-weight: 600;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.23, 1, 0.32, 1);
}

.toggle-pill:hover { background: rgba(255, 255, 255, 0.08); color: var(--text-secondary); }

.toggle-pill.on {
  background: rgba(50, 215, 75, 0.1);
  border-color: rgba(50, 215, 75, 0.25);
  color: #32D74B;
  box-shadow: 0 0 20px rgba(50, 215, 75, 0.08);
}

.toggle-pill svg { flex-shrink: 0; }

/* Works Grid */
.sheet-works {
  padding: 0 20px 24px;
}

.works-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
  gap: 14px;
}

.work-card-wrap {
  position: relative;
}

.work-dl-btn {
  position: absolute; top: 8px; right: 8px;
  width: 28px; height: 28px;
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.55);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 0.5px solid rgba(255, 255, 255, 0.15);
  color: rgba(255, 255, 255, 0.85);
  display: flex; align-items: center; justify-content: center;
  cursor: pointer; z-index: 2;
  opacity: 0;
  transition: all 0.2s cubic-bezier(0.23, 1, 0.32, 1);
}

.work-card-wrap:hover .work-dl-btn {
  opacity: 1;
}

.work-dl-btn:hover {
  background: rgba(0, 0, 0, 0.7);
  transform: scale(1.1);
}

.work-dl-btn:active { transform: scale(0.92); }

.sheet-loading {
  display: flex; justify-content: center; padding: 32px 0;
}

/* Bottom Action (discover) */
.sheet-bottom-action {
  padding: 0 20px 40px;
}

.action-btn {
  width: 100%;
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
  height: 48px; border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-primary); font-size: 15px; font-weight: 600;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.23, 1, 0.32, 1);
}

.action-btn:hover { background: rgba(255, 255, 255, 0.1); }
.action-btn:active { transform: scale(0.98); }
.action-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.action-btn.primary {
  background: var(--accent); color: var(--bg-primary); border-color: transparent;
}

.action-btn.primary:hover { background: var(--accent-light); }

/* ===== Sheet Transitions ===== */
.sheet-enter-active { transition: opacity 0.3s ease; }
.sheet-enter-active .sheet { animation: sheetUp 0.45s cubic-bezier(0.23, 1, 0.32, 1); }
.sheet-leave-active { transition: opacity 0.2s ease; }
.sheet-leave-active .sheet { animation: sheetUp 0.3s cubic-bezier(0.23, 1, 0.32, 1) reverse; }
.sheet-enter-from, .sheet-leave-to { opacity: 0; }

@keyframes sheetUp { from { transform: translateY(100%); } to { transform: translateY(0); } }

/* ===== Responsive ===== */
@media (max-width: 900px) {
  .card-grid { grid-template-columns: repeat(4, 1fr); }
}

@media (max-width: 768px) {
  .sub-page { padding: 0 0 80px; }
  .sub-hero { padding: 32px 16px 16px; }
  .hero-title { font-size: 28px; }
  .tab-content { padding: 0 12px; }
  .card-grid { grid-template-columns: repeat(3, 1fr); gap: 10px; }
  .sheet { width: 100vw; max-width: 100%; max-height: 95vh; border-radius: 20px 20px 0 0; }
  .works-grid { grid-template-columns: repeat(auto-fill, minmax(100px, 1fr)); gap: 10px; }
  .sheet-translated { font-size: 18px; }
  .name-pill { height: 22px; padding: 0 8px; font-size: 11px; }
}
</style>

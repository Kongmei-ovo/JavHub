<template>
  <div class="sub-page page-shell page-shell--standard">
    <!-- Hero -->
    <div class="sub-hero">
      <div class="hero-copy">
        <h1 class="hero-title">订阅演员</h1>
        <div class="hero-metrics" aria-label="订阅概览">
          <span>{{ subs.length }} 已订阅</span>
          <span>{{ totalNewMovies }} 候选</span>
          <span>{{ totalNeedsMagnet }} 待补磁力</span>
        </div>
      </div>
      <div class="hero-actions">
        <button class="top-action-btn" type="button" :disabled="checkingAll || loading" @click="checkAllNow">
          <span v-if="checkingAll" class="spinner-tiny"></span>
          <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/></svg>
          检查全部
        </button>
        <button class="top-action-btn primary" type="button" @click="openDiscover">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15"><path d="M12 5v14"/><path d="M5 12h14"/></svg>
          添加演员
        </button>
      </div>
    </div>

    <!-- ===== 已订阅管理 ===== -->
    <div class="tab-content subscription-content">
      <div v-if="loading" class="card-grid">
        <div v-for="n in 6" :key="n" class="skel-card"><div class="skel-cover"></div><div class="skel-info"><div class="skel-line w60"></div><div class="skel-line w40"></div></div></div>
      </div>

      <div v-else-if="subs.length > 0" class="card-grid">
        <ActorPortraitCard
          v-for="sub in subs"
          :key="sub.id"
          :actor="subActor(sub)"
          :name="subDisplayName(sub)"
          :subtitle="subOriginalName(sub)"
          :meta="subCardMeta(sub)"
          :avatar-url="subCoverUrl(sub)"
          :badges="subCardBadges(sub)"
          density="standard"
          @open="openSubSheet(sub)"
        />
      </div>

      <div v-else class="empty-state">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" width="48" height="48"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/></svg>
        <p>还没有订阅任何演员</p>
        <button class="pill-btn pill-btn-primary empty-action" type="button" @click="openDiscover">添加演员</button>
      </div>
    </div>

    <!-- ===== Discover Sheet ===== -->
    <teleport to="body">
      <transition name="sheet">
        <div v-if="discoverOpen" class="sheet-overlay discover-overlay" @click.self="closeDiscover">
          <div class="sheet discover-sheet" @click.stop>
            <div class="sheet-top-bar">
              <div class="sheet-top-actions">
                <button class="top-action-btn" type="button" @click="closeDiscover">关闭</button>
              </div>
            </div>

            <div class="discover-head">
              <h2>发现演员</h2>
            </div>

            <div class="discover-body">
              <div class="search-bar-wrap">
                <div class="search-bar">
                  <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/>
                  </svg>
                  <input v-model="searchKeyword" placeholder="搜索演员名称" class="search-input" @keyup.enter="doSearch" />
                  <button v-if="searchKeyword" class="clear-btn" type="button" @click="clearSearch">
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
                <ActorPortraitCard
                  v-for="actor in searchResults"
                  :key="actor.id"
                  :actor="actor"
                  :name="actorCardName(actor)"
                  :subtitle="actorCardSubtitle(actor)"
                  :meta="actorCardMeta(actor)"
                  :avatar-url="avatarSrc(actor)"
                  :badges="actorSearchBadges(actor)"
                  density="standard"
                  @open="openActorSheet(actor)"
                />
              </div>

              <div v-else-if="searched && searchResults.length === 0" class="empty-state">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2" width="48" height="48"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/><path d="M8 11h6"/></svg>
                <p>未找到相关演员</p>
              </div>
            </div>
          </div>
        </div>
      </transition>
    </teleport>

    <!-- ===== Detail Sheet ===== -->
    <teleport to="body">
      <transition name="sheet">
        <div v-if="sheetActor" class="sheet-overlay" @click.self="closeSheet">
          <div class="sheet" @click.stop>
            <!-- Top Bar: grabber + actions -->
            <div class="sheet-top-bar">
              <div v-if="sheetSub" class="sheet-top-actions">
                <button class="top-action-btn" @click="checkNow(sheetSub)" :disabled="checkingId === sheetSub.id">
                  <span v-if="checkingId === sheetSub.id" class="spinner-tiny"></span>
                  <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="15" height="15"><polyline points="23 4 23 10 17 10"/><path d="M20.49 15a9 9 0 11-2.12-9.36L23 10"/></svg>
                  立即检查
                </button>
                <button class="top-action-btn" @click="viewCandidates(sheetSub)">
                  查看候选
                  <span v-if="newMovieCount(sheetSub.actress_id)" class="inline-badge">{{ newMovieCount(sheetSub.actress_id) }}</span>
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
            <div v-if="sheetSub" class="sheet-stat-line">
              待处理候选 {{ sheetSub.candidate_count || newMovieCount(sheetSub.actress_id) }} · 待补磁力 {{ sheetSub.needs_magnet_count || 0 }}
            </div>

            <!-- Toggle Pills + 全部作品 -->
            <div class="sheet-toggles">
              <button v-if="sheetSub" class="toggle-pill" :class="{ on: sheetSub.enabled }" @click="toggleEnabled(sheetSub)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>
                监控
              </button>
              <button v-if="sheetSub" class="toggle-pill" :class="{ on: sheetSub.auto_download }" @click="toggleAutoDownload(sheetSub)">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                自动策略
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
                    @click="openVideoModal(movie)"
                  />
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
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from '../utils/message.js'
import api from '../api'
import { actressImgUrl } from '../utils/imageUrl.js'
import { openVideoModal as openVideoModalFn } from '../utils/modalState.js'
import { displayName } from '../utils/displayLang.js'
import { actorName, actorOriginalName } from '../utils/actorDisplay.js'
import subscriptionState from '../utils/subscriptionState'
import ActorPortraitCard from '../components/ActorPortraitCard.vue'
import MovieCard from '../components/MovieCard.vue'

const router = useRouter()

const discoverOpen = ref(false)
const searchKeyword = ref('')
const searchResults = ref([])
const searching = ref(false)
const searched = ref(false)

const subs = ref([])
const loading = ref(false)
const checkingAll = ref(false)
const checkingId = ref(null)

const sheetActor = ref(null)
const sheetSub = ref(null)
const sheetMovies = ref([])
const sheetLoading = ref(false)
const subscribing = ref(false)

const newMovieMap = ref({})
const actressMetaMap = ref({})
const lastCheckReport = ref(null)

const totalNewMovies = computed(() => {
  let c = 0
  for (const m of Object.values(newMovieMap.value)) c += m.length
  return c
})

const totalNeedsMagnet = computed(() => subs.value.reduce(
  (sum, sub) => sum + Number(sub.needs_magnet_count || 0),
  0,
))

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
function actorCardName(actor) { return actorName(actor, '未知') }
function actorCardSubtitle(actor) { return actorOriginalName(actor) }
function actorCardMeta(actor) { return actor?.movie_count != null ? `${Number(actor.movie_count).toLocaleString()} 部作品` : '' }
function actorSearchBadges(actor) {
  return isSubscribed(actor.id) ? [{ label: '已订阅', tone: 'subscribed' }] : []
}
function subActor(sub) {
  const meta = actressMetaMap.value[sub.actress_id] || {}
  return {
    id: sub.actress_id,
    actress_id: sub.actress_id,
    name: sub.actress_name,
    ...meta,
  }
}
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
function movieCoverUrl(movie) { return movie.jacket_thumb_url || movie.jacket_full_url || movie.cover_url || '' }
function subCardMeta(sub) {
  const count = subMeta(sub)?.movie_count
  const parts = []
  if (count != null) parts.push(`${Number(count).toLocaleString()} 部作品`)
  if (sub.needs_magnet_count) parts.push(`待补磁力 ${sub.needs_magnet_count}`)
  return parts.join(' · ')
}
function subCardBadges(sub) {
  const badges = [{ label: '已订阅', tone: 'subscribed' }]
  const candidates = sub.candidate_count || newMovieCount(sub.actress_id)
  if (candidates) badges.push({ label: `${candidates} 候选`, tone: 'warning' })
  if (sub.auto_download) badges.push({ label: '自动策略', tone: 'success' })
  return badges
}

function shuffleArray(arr) {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]] }
  return a
}

function openDiscover() {
  discoverOpen.value = true
}

function closeDiscover() {
  discoverOpen.value = false
  clearSearch()
}

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
  closeDiscover()
  sheetActor.value = actor; sheetSub.value = null
  sheetMovies.value = []; sheetLoading.value = true
  try {
    const r = await api.getActressVideos(actor.id, 1, 30, { include_supplement: '1' })
    const all = r.data?.data || []
    sheetMovies.value = shuffleArray(all).slice(0, 12)
  } catch (e) { console.error(e) } finally { sheetLoading.value = false }
}

async function openSubSheet(sub) {
  discoverOpen.value = false
  const meta = actressMetaMap.value[sub.actress_id]
  sheetActor.value = { id: sub.actress_id, name_kanji: meta?.name_kanji || sub.actress_name || '', image_url: meta?.image_url || '', movie_count: meta?.movie_count, name_romaji: meta?.name_romaji || '', name_kana: meta?.name_kana || '', name_kanji_translated: meta?.name_kanji_translated || '', name_romaji_translated: meta?.name_romaji_translated || '' }
  sheetSub.value = sub
  sheetMovies.value = []; sheetLoading.value = true
  try {
    const r = await api.getActressVideos(sub.actress_id, 1, 30, { include_supplement: '1' })
    const all = r.data?.data || []
    sheetMovies.value = shuffleArray(all).slice(0, 12)
  } catch (e) { console.error(e) } finally { sheetLoading.value = false }
}

function closeSheet() { sheetActor.value = null; sheetSub.value = null; sheetMovies.value = [] }

function viewAllVideos() {
  if (!sheetActor.value) return
  const actressId = sheetActor.value.actress_id || sheetActor.value.id
  const name = actorName(sheetActor.value, sheetActor.value.name || sheetActor.value.name_kanji || sheetActor.value.name_romaji || String(actressId || ''))
  const query = name ? { name } : {}
  if (actressId) query.actress_id = actressId
  closeSheet()
  router.push({ path: `/actor/${encodeURIComponent(name)}`, query })
}

function openVideoModal(movie) {
  const route = router.currentRoute.value
  openVideoModalFn(movie, route?.fullPath || route?.path || '/subscription')
}

async function syncSubscriptionState() {
  try {
    await subscriptionState.refresh()
  } catch (e) {
    console.error('Sync subscription state failed:', e)
  }
}

async function subscribeFromSheet() {
  if (!sheetActor.value) return
  const a = sheetActor.value; const name = a.name_kanji || a.name_romaji || ''
  subscribing.value = true
  try { await api.addSubscription({ actress_id: a.id, actress_name: name }); await syncSubscriptionState(); ElMessage.success(`已订阅 ${name}`); await loadSubs(); closeSheet() }
  catch (e) { ElMessage.error('订阅失败') } finally { subscribing.value = false }
}

// ===== Subscriptions =====
async function loadSubs() {
  loading.value = true
  try {
    const r = await api.getSubscriptions()
    subs.value = r.data?.data || r.data || []
    await enrichActressMeta()
    await loadNewMovieBadges()
  }
  catch (e) { console.error(e) } finally { loading.value = false }
}

async function enrichActressMeta() {
  const ids = subs.value.filter(s => s.actress_id).map(s => s.actress_id)
  if (!ids.length) { actressMetaMap.value = {}; return }
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

async function checkAllNow() {
  checkingAll.value = true
  try {
    const r = await api.checkSubscriptions()
    const data = r.data || {}
    lastCheckReport.value = data
    const checked = data.subscriptions_checked || 0
    const created = data.created || 0
    const existing = data.existing || 0
    const inLibrary = data.in_library || 0
    if (created > 0) ElMessage.success(`已检查 ${checked} 个订阅，新增 ${created} 个候选，已有 ${existing} 个，已在库 ${inLibrary} 个`)
    else if (existing > 0) ElMessage.info(`已检查 ${checked} 个订阅，没有新增候选，已有 ${existing} 个待处理`)
    else ElMessage.info(`已检查 ${checked} 个订阅，暂无缺失候选，已在库 ${inLibrary} 个`)
    await loadSubs()
  } catch (e) {
    ElMessage.error('检查失败')
  } finally {
    checkingAll.value = false
  }
}

async function checkNow(sub) {
  checkingId.value = sub.id
  try {
    const r = await api.checkSubscription(sub.id)
    lastCheckReport.value = r.data
    const created = r.data.created || 0
    const existing = r.data.existing || 0
    const inLibrary = r.data.in_library || 0
    if (created > 0) ElMessage.success(`新增 ${created} 个候选，已有 ${existing} 个，已在库 ${inLibrary} 个`)
    else if (existing > 0) ElMessage.info(`没有新增候选，已有 ${existing} 个待处理`)
    else ElMessage.info(`暂无缺失候选，已在库 ${inLibrary} 个`)
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
  try { await api.deleteSubscription(id); await syncSubscriptionState(); subs.value = subs.value.filter(s => s.id !== id); closeSheet(); ElMessage.success('已取消订阅') }
  catch (e) { ElMessage.error('删除失败') }
}

function viewCandidates(sub) {
  router.push({
    path: '/downloads',
    query: { tab: 'candidates', status: 'candidate', source: 'subscription', actress_id: sub.actress_id }
  })
}

onMounted(loadSubs)
</script>

<style scoped>
.sub-page {
  min-height: 100dvh;
}

.sub-hero {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 18px;
  padding: 20px 4px 24px;
}

.hero-copy {
  min-width: 0;
}

.hero-title {
  font-size: var(--page-title-size);
  font-weight: var(--page-title-weight);
  line-height: var(--page-title-line);
  color: var(--text-primary);
  letter-spacing: 0;
  margin: 0;
}

.hero-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.hero-metrics span {
  display: inline-flex;
  align-items: center;
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-secondary);
  font-size: var(--type-caption);
  font-weight: 600;
  white-space: nowrap;
}

.hero-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.inline-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 16px;
  height: 16px;
  padding: 0 5px;
  border-radius: 999px;
  background: #ff375f;
  color: #fff;
  font-size: var(--type-badge);
  font-weight: 700;
}

.tab-content { animation: fadeIn 0.2s ease; }
.subscription-content { padding-bottom: 32px; }

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
  padding: 0 10px; font-size: var(--type-card-title); color: var(--text-primary); min-height: 44px;
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
  grid-template-columns: repeat(auto-fill, minmax(148px, 1fr));
  gap: 16px;
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
  color: var(--text-primary); font-size: var(--type-caption); font-weight: 600;
  cursor: pointer; flex-shrink: 0;
  transition: all 0.2s cubic-bezier(0.23, 1, 0.32, 1);
}

.pill-btn:hover { background: rgba(255, 255, 255, 0.1); }

.pill-btn-primary {
  background: var(--accent); color: var(--text-on-accent); border-color: transparent;
}

.pill-btn-primary:hover { background: var(--accent-light); }

.empty-action {
  margin-top: 16px;
}

/* ===== Empty State ===== */
.empty-state {
  text-align: center; padding: 80px 20px;
  display: flex; flex-direction: column; align-items: center; gap: 10px;
  color: var(--text-secondary);
}

.empty-state svg { opacity: 0.3; margin-bottom: 8px; }
.empty-state p { margin: 0; font-size: var(--type-card-title); }

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
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  z-index: var(--z-modal);
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

.sheet-top-actions { display: flex; gap: 8px; flex-wrap: wrap; }

.top-action-btn {
  display: inline-flex; align-items: center; gap: 5px;
  height: 32px; padding: 0 14px; border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-secondary);
  font-size: var(--type-caption); font-weight: 600;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.23, 1, 0.32, 1);
}

.top-action-btn:hover { background: rgba(255, 255, 255, 0.1); color: var(--text-primary); }
.top-action-btn:active { transform: scale(0.96); }
.top-action-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.top-action-btn.danger { color: #FF375F; border-color: rgba(255, 55, 95, 0.25); }
.top-action-btn.danger:hover { background: rgba(255, 55, 95, 0.1); }
.top-action-btn.primary {
  background: var(--accent);
  color: var(--text-on-accent);
  border-color: transparent;
}
.top-action-btn.primary:hover {
  background: var(--accent-light);
  color: var(--text-on-accent);
}

.discover-sheet {
  max-width: 980px;
}

.discover-overlay {
  background: rgba(0, 0, 0, 0.22);
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
}

.discover-head {
  padding: 20px 24px 12px;
  text-align: center;
}

.discover-head h2 {
  margin: 0;
  color: var(--text-primary);
  font-size: var(--type-section-title);
  line-height: 1.2;
}

.discover-body {
  padding: 0 20px 28px;
}

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
  font-size: var(--type-section-title); font-weight: 700;
  color: var(--text-primary);
  letter-spacing: 0;
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
  font-size: var(--type-caption); font-weight: 500;
  color: var(--text-secondary);
  white-space: nowrap;
}

.name-pill.dim { color: var(--text-muted); }

/* Stat Line */
.sheet-stat-line {
  text-align: center;
  font-size: var(--type-control); font-weight: 500;
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
  color: var(--text-muted); font-size: var(--type-control); font-weight: 600;
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
  color: var(--text-primary); font-size: var(--type-card-title); font-weight: 600;
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.23, 1, 0.32, 1);
}

.action-btn:hover { background: rgba(255, 255, 255, 0.1); }
.action-btn:active { transform: scale(0.98); }
.action-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.action-btn.primary {
  background: var(--accent); color: var(--text-on-accent); border-color: transparent;
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
  .card-grid { grid-template-columns: repeat(auto-fill, minmax(136px, 1fr)); }
}

@media (max-width: 768px) {
  .sub-hero {
    align-items: stretch;
    flex-direction: column;
    padding: 32px 16px 16px;
  }
  .hero-title { font-size: var(--page-title-size-mobile); }
  .hero-actions { justify-content: flex-start; }
  .tab-content { padding: 0 12px; }
  .card-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; }
  .sheet { width: 100vw; max-width: 100%; max-height: 95vh; border-radius: 20px 20px 0 0; }
  .discover-body { padding: 0 12px 24px; }
  .works-grid {
    --video-grid-min-mobile: clamp(104px, 31vw, 148px);
    grid-template-columns: repeat(auto-fit, minmax(var(--video-grid-min-mobile), 1fr));
    gap: var(--video-grid-gap-mobile) !important;
  }
  .sheet-translated { font-size: var(--type-panel-title); }
  .name-pill { height: 22px; padding: 0 8px; font-size: var(--type-micro); }
  .clear-btn,
  .pill-btn,
  .top-action-btn,
  .toggle-pill {
    min-height: 44px;
  }
  .clear-btn {
    min-width: 44px;
  }
  .sheet-toggles {
    flex-wrap: wrap;
  }
}
</style>

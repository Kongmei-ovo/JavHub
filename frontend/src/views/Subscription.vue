<template>
  <div class="sub-page page-shell page-shell--standard">
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
        <button class="top-action-btn" type="button" :class="{ primary: subscriptionEditMode }" :disabled="loading || subs.length === 0" @click="toggleSubscriptionEditMode">
          {{ subscriptionEditMode ? '完成' : '编辑' }}
        </button>
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

    <div class="tab-content subscription-content">
      <div v-if="subscriptionEditMode" class="subscription-management-bar" role="toolbar" aria-label="订阅批量操作">
        <div class="subscription-management-summary">
          <strong>{{ selectedSubscriptionCount }}</strong>
          <span>已选择 · 共 {{ subs.length }} 个订阅</span>
        </div>
        <div class="sheet-top-actions subscription-batch-actions">
          <button class="top-action-btn" type="button" :disabled="subs.length === 0 || allSubscriptionsSelected" @click="selectAllSubscriptions">全选</button>
          <button class="top-action-btn" type="button" :disabled="selectedSubscriptionCount === 0" @click="clearSubscriptionSelection">清空</button>
          <button class="top-action-btn" type="button" :disabled="selectedSubscriptionCount === 0" @click="pauseSelectedSubscriptions">暂停监控</button><button class="top-action-btn" type="button" :disabled="selectedSubscriptionCount === 0" @click="resumeSelectedSubscriptions">恢复监控</button>
          <button class="top-action-btn" type="button" :disabled="selectedSubscriptionCount === 0" @click="enableSelectedAutoDownload">开启自动策略</button><button class="top-action-btn" type="button" :disabled="selectedSubscriptionCount === 0" @click="disableSelectedAutoDownload">关闭自动策略</button>
          <button class="top-action-btn danger" type="button" :disabled="selectedSubscriptionCount === 0" @click="removeSelectedSubscriptions">
            取消订阅 {{ selectedSubscriptionCount || '' }}
          </button>
        </div>
      </div>

      <AppleSkeleton v-if="loading" class="card-grid" variant="gallery" :items="6" label="订阅演员加载中" />

      <div v-else-if="subs.length > 0" class="card-grid" :class="{ 'is-subscription-editing': subscriptionEditMode }">
        <div v-for="sub in subs" :key="sub.id" class="subscription-selectable" :class="{ 'is-selected': isSubscriptionSelected(sub) }">
          <ActorPortraitCard :actor="subActor(sub)" :name="subDisplayName(sub)" :subtitle="subOriginalName(sub)" :meta="subCardMeta(sub)" :avatar-url="subCoverUrl(sub)" :badges="subCardBadges(sub)" density="standard" @open="handleSubscriptionCardOpen(sub)" />
          <button v-if="!subscriptionEditMode && sinceLastKnown(sub)" class="subscription-since-chip" type="button" aria-label="查看自上次以来新增" @click.stop="openSinceLastSheet(sub)">
            <template v-if="sinceLastCount(sub)">新增 {{ sinceLastCount(sub) }}</template><template v-else>无新增</template><span v-if="formatSinceLastElapsed(sub.last_run_at)"> · {{ formatSinceLastElapsed(sub.last_run_at) }}</span>
          </button>
          <button v-if="!subscriptionEditMode && sub.actress_id" class="subscription-completeness-chip" type="button" aria-label="查看收藏完整度" @click.stop="openCompletenessSheet(sub)"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="13" height="13"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>完整度</button>
          <button v-if="subscriptionEditMode" class="subscription-select-button" type="button" :aria-label="isSubscriptionSelected(sub) ? '取消选择订阅' : '选择订阅'" @click.stop="toggleSubscriptionSelection(sub)">
            <span></span>
          </button>
        </div>
      </div>

      <AppleEmptyState v-else class="empty-state" title="还没有订阅任何演员" description="订阅后可以定期检查新作品，并把缺失影片写入下载候选。" next-step="先搜索演员添加订阅；添加后可以立即检查，或到下载候选处理待补磁力。" action-label="添加演员" secondary-action-label="浏览演员目录" @action="openDiscover" @secondary-action="router.push('/entities?tab=actresses')">
        <template #icon>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 01-3.46 0"/></svg>
        </template>
      </AppleEmptyState>
    </div>

    <teleport to="body">
      <transition name="sheet">
        <div v-if="discoverOpen" class="sheet-overlay discover-overlay" @click.self="closeDiscover">
          <div class="sheet discover-sheet" @click.stop>
            <div class="sheet-top-bar">
              <div class="sheet-top-actions">
                <button class="top-action-btn" type="button" @click="closeDiscover">关闭</button>
              </div>
            </div>

            <div class="discover-head"><span class="discover-kicker">订阅发现</span><h2>发现演员</h2><p>搜索演员名称，添加后会进入订阅检查和候选整理。</p></div>

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

              <AppleSkeleton v-if="searching" class="card-grid" variant="gallery" :items="8" label="演员搜索中" />

              <div v-else-if="searchResults.length > 0" class="card-grid">
                <ActorPortraitCard v-for="actor in searchResults" :key="actor.id" :actor="actor" :name="actorCardName(actor)" :subtitle="actorCardSubtitle(actor)" :meta="actorCardMeta(actor)" :avatar-url="avatarSrc(actor)" :badges="actorSearchBadges(actor)" density="standard" @open="openActorSheet(actor)" />
              </div>

              <AppleEmptyState v-else-if="searched && searchResults.length === 0" class="empty-state compact" title="未找到相关演员" description="当前关键词没有匹配到可订阅的演员。" next-step="换一个日文名、罗马音或更短关键词再试。" action-label="重新搜索" secondary-action-label="清空关键词" density="compact" @action="doSearch" @secondary-action="clearSearch">
                <template #icon>
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/><path d="M8 11h6"/></svg>
                </template>
              </AppleEmptyState>

              <div v-else-if="!searched" class="discover-suggestions" aria-label="最近订阅">
                <span class="discover-suggestion-title">最近订阅</span>
                <button v-for="sub in recentSubscriptions" :key="sub.id" class="suggestion-chip" type="button" @click="openSubSheet(sub)">{{ subDisplayName(sub) }}</button>
                <span v-if="recentSubscriptions.length === 0" class="suggestion-chip is-empty">搜索演员后可在这里订阅</span>
              </div>
            </div>
          </div>
        </div>
      </transition>
    </teleport>

    <teleport to="body">
      <transition name="sheet">
        <div v-if="sheetActor" class="sheet-overlay" @click.self="closeSheet">
          <div class="sheet" @click.stop>
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

            <div class="sheet-avatar-wrap">
              <div class="sheet-avatar-glow"></div>
              <div class="sheet-avatar">
                <img v-if="sheetCoverUrl" :src="sheetCoverUrl" :alt="sheetActor.name_kanji" loading="eager" decoding="async" @error="handleSheetAvatarError" />
                <span v-else class="avatar-fallback">{{ (sheetActor.name_kanji || '?')[0] }}</span>
              </div>
            </div>

            <div v-if="sheetTranslatedName" class="sheet-translated">{{ sheetTranslatedName }}</div>
            <div class="sheet-name-row">
              <span v-if="sheetActor.name_kanji" class="name-pill">{{ sheetActor.name_kanji }}</span>
              <span v-if="sheetActor.name_romaji" class="name-pill">{{ sheetActor.name_romaji }}</span>
              <span v-if="sheetActor.name_kana" class="name-pill dim">{{ sheetActor.name_kana }}</span>
            </div>

            <div v-if="sheetActor.movie_count != null" class="sheet-stat-line">
              {{ sheetActor.movie_count.toLocaleString() }} 部作品
            </div>
            <div v-if="sheetSub" class="sheet-stat-line">
              待处理候选 {{ sheetSub.candidate_count || newMovieCount(sheetSub.actress_id) }} · 待补磁力 {{ sheetSub.needs_magnet_count || 0 }}
            </div>

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
            <div v-if="sheetSub" class="cadence-control">
              <span class="sheet-stat-line">每 {{ cadenceHours(sheetSub.cadence_minutes) }} 小时检查</span>
              <div class="cadence-options" aria-label="检查间隔">
                <button v-for="option in cadenceOptions" :key="option.minutes" class="cadence-option" :class="{ 'is-active': Number(sheetSub.cadence_minutes || 1440) === option.minutes }" type="button" @click="updateCadence(sheetSub, option.minutes)">{{ option.label }}</button>
              </div>
            </div>

            <div v-if="sheetMovies.length > 0" class="sheet-works">
              <div class="works-grid">
                <div v-for="movie in sheetMovies" :key="movie.content_id || movie.dvd_id" class="work-card-wrap">
                  <MovieCard v-bind="movieCardVariantProps(movie)" :coverUrl="movieCoverUrl(movie)" :title="movie.title_en || movie.title_ja || ''" :serviceCode="movie.service_code || ''" :releaseDate="movie.release_date || ''" :runtimeMins="movie.runtime_mins || ''" :sampleUrl="movie.sample_url || ''" @click="openVideoModal(movie)" />
                  <VariantGroupDisclosure :variantGroupCount="Number(movie.variant_group_count || 0)" :variantGroupItems="visibleVariantItems(movie)" :expanded="isVariantGroupExpanded(movie)" :itemKey="variantGroupKey(movie)" @toggle="toggleVariantGroup" @openVariant="openVideoModal" />
                </div>
              </div>
            </div>
            <div v-else-if="sheetLoading" class="sheet-loading"><div class="spinner-small"></div></div>

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

    <teleport to="body">
      <transition name="sheet">
        <div v-if="sinceLastSheetSub" class="sheet-overlay" @click.self="closeSinceLastSheet">
          <div class="sheet since-last-sheet" @click.stop>
            <div class="sheet-top-bar"><div class="sheet-top-actions"><button class="top-action-btn" type="button" @click="closeSinceLastSheet">关闭</button></div></div>
            <div class="since-last-head"><span class="discover-kicker">自上次以来新增</span><h2>{{ subDisplayName(sinceLastSheetSub) }}</h2><p>{{ sinceLastSummary(sinceLastSheetSub) }}</p></div>
            <div class="since-last-list">
              <div v-for="movie in sinceLastSheetMovies" :key="sinceLastMovieKey(movie)" class="since-last-item">
                <strong class="since-last-title">{{ sinceLastMovieTitle(movie) }}</strong>
                <span class="since-last-meta">{{ sinceLastMovieCode(movie) }}<template v-if="movie.release_date"> · {{ movie.release_date }}</template></span>
              </div>
              <div v-if="sinceLastSheetMovies.length === 0" class="since-last-item"><strong class="since-last-title">无新增</strong><span class="since-last-meta">最近一次检查没有发现新作品</span></div>
            </div>
          </div>
        </div>
      </transition>
    </teleport>

    <CompletenessSheet :sub="completenessSheetSub" :name="completenessSheetSub ? subDisplayName(completenessSheetSub) : ''" :data="completenessData" :loading="completenessLoading" @close="closeCompletenessSheet" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from '../utils/message.js'
import api from '../api'
import { actressImgUrl } from '../utils/imageUrl.js'
import { applyImageFallback } from '../utils/imageFallback.js'
import { openVideoModal as openVideoModalFn } from '../utils/modalState.js'
import { displayName } from '../utils/displayLang.js'
import { actorName, actorOriginalName } from '../utils/actorDisplay.js'
import subscriptionState from '../utils/subscriptionState'
import { hydrateSubscriptionActorMeta } from '../utils/subscriptionActorMeta.js'
import ActorPortraitCard from '../components/ActorPortraitCard.vue'
import CompletenessSheet from '../features/subscription/CompletenessSheet.vue'
import AppleEmptyState from '../components/AppleEmptyState.vue'
import AppleSkeleton from '../components/AppleSkeleton.vue'
import MovieCard from '../components/MovieCard.vue'
import VariantGroupDisclosure from '../components/VariantGroupDisclosure.vue'
import { movieCardVariantProps, variantGroupKey, visibleVariantItems } from '../utils/videoVariantPresentation.js'

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
const subscriptionEditMode = ref(false)
const selectedSubscriptionIds = ref(new Set())
const sheetActor = ref(null)
const sheetSub = ref(null)
const sheetMovies = ref([])
const sheetLoading = ref(false)
const subscribing = ref(false)
const expandedVariantGroups = ref({})
const actressMetaMap = ref({})
const lastCheckReport = ref(null)
const sinceLastSheetSub = ref(null)
const completenessSheetSub = ref(null)
const completenessData = ref(null)
const completenessLoading = ref(false)
const cadenceOptions = [{ label: '每 6 小时', minutes: 360 }, { label: '每 12 小时', minutes: 720 }, { label: '每 24 小时', minutes: 1440 }, { label: '每 72 小时', minutes: 4320 }]

const totalNewMovies = computed(() => subs.value.reduce((sum, sub) => sum + Number(sub.candidate_count || 0), 0))
const totalNeedsMagnet = computed(() => subs.value.reduce((sum, sub) => sum + Number(sub.needs_magnet_count || 0), 0))
const selectedSubscriptionCount = computed(() => selectedSubscriptionIds.value.size)
const allSubscriptionsSelected = computed(() => subs.value.length > 0 && subs.value.every(sub => selectedSubscriptionIds.value.has(subscriptionKey(sub))))
const recentSubscriptions = computed(() => subs.value.slice(0, 6))
const sheetCoverUrl = computed(() => sheetActor.value ? actressImgUrl(sheetActor.value.image_url) || '' : '')
const sheetTranslatedName = computed(() => sheetActor.value ? displayName(sheetActor.value, 'name_kanji', 'name_romaji') || '' : '')
const sinceLastSheetMovies = computed(() => sinceLastMovies(sinceLastSheetSub.value))

function avatarSrc(actor) { return actressImgUrl(actor.image_url) || '' }
function subCoverUrl(sub) { const m = actressMetaMap.value[sub.actress_id]; return m?.image_url ? actressImgUrl(m.image_url) : '' }
function subMeta(sub) { return actressMetaMap.value[sub.actress_id] || null }
function isSubscribed(actressId) { return subs.value.some(s => s.actress_id === actressId) }
function actorCardName(actor) { return actorName(actor, '未知') }
function actorCardSubtitle(actor) { return actorOriginalName(actor) }
function actorCardMeta(actor) { return actor?.movie_count != null ? `${Number(actor.movie_count).toLocaleString()} 部作品` : '' }
function actorSearchBadges(actor) { return isSubscribed(actor.id) ? [{ label: '已订阅', tone: 'subscribed' }] : [] }
function subActor(sub) { return { id: sub.actress_id, actress_id: sub.actress_id, name: sub.actress_name, ...(actressMetaMap.value[sub.actress_id] || {}) } }
function subDisplayName(sub) {
  const meta = actressMetaMap.value[sub.actress_id]
  if (meta) { const n = displayName(meta, 'name_kanji', 'name_romaji'); if (n) return n }
  return sub.actress_name || '未知'
}
function subOriginalName(sub) {
  const meta = actressMetaMap.value[sub.actress_id]
  return meta?.name_kanji || sub.actress_name || ''
}
function newMovieCount(actressId) { return Number(subs.value.find(item => String(item.actress_id) === String(actressId))?.candidate_count || 0) }
function movieCoverUrl(movie) { return movie.jacket_thumb_url || movie.jacket_full_url || movie.cover_url || '' }
function sinceLastMovies(sub) { return (Array.isArray(sub?.new_since_last) ? sub.new_since_last : []).map(item => typeof item === 'string' ? { code: item, title: item } : item).filter(Boolean) }
function sinceLastKnown(sub) { return Array.isArray(sub?.new_since_last) }
function sinceLastCount(sub) { return sinceLastMovies(sub).length }
function sinceLastMovieCode(movie) { return movie.dvd_id || movie.code || movie.content_id || movie.service_code || '未编号' }
function sinceLastMovieTitle(movie) { return movie.title_en || movie.title_ja || movie.title || sinceLastMovieCode(movie) }
function sinceLastMovieKey(movie) { return movie.candidate_id || movie.content_id || movie.dvd_id || movie.code || movie.title || JSON.stringify(movie) }
function sinceLastSummary(sub) { const count = sinceLastCount(sub); const elapsed = formatSinceLastElapsed(sub?.last_run_at); return count ? `新增 ${count}${elapsed ? ` · ${elapsed}` : ''}` : '无新增' }
function formatSinceLastElapsed(value) {
  if (!value) return ''
  const diff = Math.max(0, Date.now() - new Date(value).getTime())
  if (!Number.isFinite(diff)) return ''
  if (diff < 60_000) return '刚刚'
  const minutes = Math.floor(diff / 60_000)
  if (minutes < 60) return `${minutes} 分钟前`
  const hours = Math.floor(minutes / 60)
  if (hours < 48) return `${hours} 小时前`
  return `${Math.floor(hours / 24)} 天前`
}
function cadenceHours(minutes) { return Math.max(1, Math.round(Number(minutes || 1440) / 60)) }
function cadenceLabel(minutes) { return `每 ${cadenceHours(minutes)} 小时检查` }
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
function subscriptionKey(sub) { return String(sub?.id || '') }
function isSubscriptionSelected(sub) { return selectedSubscriptionIds.value.has(subscriptionKey(sub)) }
function toggleSubscriptionSelection(sub) { const key = subscriptionKey(sub); if (!key) return; const next = new Set(selectedSubscriptionIds.value); if (next.has(key)) next.delete(key); else next.add(key); selectedSubscriptionIds.value = next }
function selectAllSubscriptions() { selectedSubscriptionIds.value = new Set(subs.value.map(subscriptionKey).filter(Boolean)) }
function clearSubscriptionSelection() { selectedSubscriptionIds.value = new Set() }
function toggleSubscriptionEditMode() {
  subscriptionEditMode.value = !subscriptionEditMode.value
  if (!subscriptionEditMode.value) clearSubscriptionSelection()
}
function handleSubscriptionCardOpen(sub) { if (subscriptionEditMode.value) { toggleSubscriptionSelection(sub); return } openSubSheet(sub) }
function openSinceLastSheet(sub) { sinceLastSheetSub.value = sub }
function closeSinceLastSheet() { sinceLastSheetSub.value = null }
async function openCompletenessSheet(sub) {
  completenessSheetSub.value = sub; completenessData.value = null; completenessLoading.value = true
  try { completenessData.value = (await api.getActressCompleteness(sub.actress_id)).data }
  catch (error) { ElMessage.error('加载完整度失败'); completenessData.value = { total_films: 0, owned_films: 0, summary: {}, films: [] } }
  finally { completenessLoading.value = false }
}
function closeCompletenessSheet() { completenessSheetSub.value = null; completenessData.value = null }
function subscriptionSheetActor(sub, meta = null) {
  const m = meta || {}
  return { id: sub.actress_id, actress_id: sub.actress_id, name_kanji: m.name_kanji || sub.actress_name || '', image_url: m.image_url || '', movie_count: m.movie_count, name_romaji: m.name_romaji || '', name_kana: m.name_kana || '', name_kanji_translated: m.name_kanji_translated || '', name_romaji_translated: m.name_romaji_translated || '' }
}

function shuffleArray(arr) {
  const a = [...arr]
  for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]] }
  return a
}

function openDiscover() { discoverOpen.value = true }
function closeDiscover() { discoverOpen.value = false; clearSearch() }
async function doSearch() {
  const q = searchKeyword.value.trim(); if (!q) return
  searching.value = true; searched.value = true; searchResults.value = []
  try { const r = await api.searchActors(q); searchResults.value = r.data?.data || r.data || [] }
  catch (e) { console.error(e) } finally { searching.value = false }
}

function clearSearch() { searchKeyword.value = ''; searchResults.value = []; searched.value = false }
function handleSheetAvatarError(event) {
  const label = actorName(sheetActor.value) || sheetActor.value?.name_kanji || '?'
  applyImageFallback(event, { label: label.slice(0, 1) })
}

async function openActorSheet(actor) {
  closeDiscover()
  sheetActor.value = actor; sheetSub.value = null
  sheetMovies.value = []; sheetLoading.value = true
  try {
    const r = await api.getActressVideos(actor.id, 1, 30, { include_supplement: '1', variant_mode: 'grouped', variant_scope: 'indexed', include_variant_explanations: 1 })
    const all = r.data?.data || []
    sheetMovies.value = shuffleArray(all).slice(0, 12)
  } catch (e) { console.error(e) } finally { sheetLoading.value = false }
}

async function openSubSheet(sub) {
  discoverOpen.value = false
  const existingMeta = actressMetaMap.value[sub.actress_id] || null
  sheetActor.value = subscriptionSheetActor(sub, existingMeta)
  sheetSub.value = sub
  sheetMovies.value = []; sheetLoading.value = true
  try {
    const [meta, r] = await Promise.all([
      loadSubscriptionActorMeta(sub),
      api.getActressVideos(sub.actress_id, 1, 30, { include_supplement: '1', variant_mode: 'grouped', variant_scope: 'indexed', include_variant_explanations: 1 }),
    ])
    if (meta) sheetActor.value = subscriptionSheetActor(sub, meta)
    const all = r.data?.data || []
    sheetMovies.value = shuffleArray(all).slice(0, 12)
  } catch (e) { console.error(e) } finally { sheetLoading.value = false }
}

function closeSheet() { sheetActor.value = null; sheetSub.value = null; sheetMovies.value = []; expandedVariantGroups.value = {} }
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
function isVariantGroupExpanded(movie) {
  const key = variantGroupKey(movie)
  return Boolean(key && expandedVariantGroups.value[key])
}

function toggleVariantGroup(key) {
  if (!key) return
  expandedVariantGroups.value = {
    ...expandedVariantGroups.value,
    [key]: !expandedVariantGroups.value[key],
  }
}
async function syncSubscriptionState() { try { await subscriptionState.refresh() } catch (e) { console.error('Sync subscription state failed:', e) } }
async function subscribeFromSheet() {
  if (!sheetActor.value) return
  const a = sheetActor.value; const name = a.name_kanji || a.name_romaji || ''
  subscribing.value = true
  try { await api.addSubscription({ actress_id: a.id, actress_name: name }); await syncSubscriptionState(); ElMessage.success(`已订阅 ${name}`); await loadSubs(); closeSheet() }
  catch (e) { ElMessage.error('订阅失败') } finally { subscribing.value = false }
}
async function loadSubs() {
  loading.value = true
  try {
    const r = await api.getSubscriptions()
    const items = mergeSinceLastReport(r.data?.data || r.data || [])
    subs.value = items
    await loadSubscriptionActorMetaForSubs(items)
  }
  catch (e) { console.error(e) } finally { loading.value = false }
}

function mergeSinceLastReport(items) {
  const report = lastCheckReport.value
  const results = Array.isArray(report?.results) ? report.results : []
  if (!results.length) return items
  const resultBySub = new Map(results.map(item => [String(item.subscription_id), item]))
  const moviesBySub = new Map()
  for (const movie of (Array.isArray(report?.movies) ? report.movies : [])) {
    const key = String(movie.subscription_id || '')
    if (!key) continue
    moviesBySub.set(key, [...(moviesBySub.get(key) || []), movie])
  }
  return items.map(sub => {
    const result = resultBySub.get(String(sub.id))
    if (!result) return sub
    const moviesByCode = new Map((moviesBySub.get(String(sub.id)) || []).map(movie => [sinceLastMovieCode(movie), movie]))
    const newSinceLast = (Array.isArray(result.new_since_last) ? result.new_since_last : []).map(code => moviesByCode.get(String(code)) || { code: String(code), title: String(code) })
    return { ...sub, new_since_last: newSinceLast }
  })
}

async function loadSubscriptionActorMeta(sub) {
  if (!sub?.actress_id) return null
  const cached = actressMetaMap.value[sub.actress_id]
  if (cached) return cached
  try {
    const r = await api.getActress(sub.actress_id)
    const data = r.data || r
    if (data) {
      actressMetaMap.value = { ...actressMetaMap.value, [sub.actress_id]: data }
      return data
    }
  } catch (e) {
    console.error(e)
  }
  return null
}

async function loadSubscriptionActorMetaForSubs(items) {
  actressMetaMap.value = await hydrateSubscriptionActorMeta(
    items,
    actressMetaMap.value,
    (actressId) => api.getActress(actressId),
  )
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
    lastCheckReport.value = { results: [{ subscription_id: sub.id, ...(r.data || {}) }], movies: (r.data?.new_movies || []).map(movie => ({ ...movie, subscription_id: sub.id })) }
    const created = r.data.created || 0
    const existing = r.data.existing || 0
    const inLibrary = r.data.in_library || 0
    if (created > 0) ElMessage.success(`新增 ${created} 个候选，已有 ${existing} 个，已在库 ${inLibrary} 个`)
    else if (existing > 0) ElMessage.info(`没有新增候选，已有 ${existing} 个待处理`)
    else ElMessage.info(`暂无缺失候选，已在库 ${inLibrary} 个`)
    await loadSubs()
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

async function updateCadence(sub, minutes) {
  try {
    await api.updateSubscription(sub.id, { cadence_minutes: minutes })
    subs.value = subs.value.map(item => item.id === sub.id ? { ...item, cadence_minutes: minutes } : item)
    if (sheetSub.value?.id === sub.id) sheetSub.value = { ...sheetSub.value, cadence_minutes: minutes }
    ElMessage.success(`已改为${cadenceLabel(minutes)}`)
  } catch (e) { ElMessage.error('更新检查间隔失败') }
}

async function updateSelectedSubscriptions(patch, label) {
  const selectedIds = new Set(selectedSubscriptionIds.value)
  const selectedSubs = subs.value.filter(sub => selectedIds.has(subscriptionKey(sub)))
  if (selectedSubs.length === 0) return
  try {
    for (const sub of selectedSubs) await api.updateSubscription(sub.id, patch)
    subs.value = subs.value.map(sub => selectedIds.has(subscriptionKey(sub)) ? { ...sub, ...patch } : sub)
    clearSubscriptionSelection()
    ElMessage.success(`已${label} ${selectedSubs.length} 个订阅`)
  } catch (e) { ElMessage.error('批量更新失败') }
}
const pauseSelectedSubscriptions = () => updateSelectedSubscriptions({ enabled: false }, '暂停'), resumeSelectedSubscriptions = () => updateSelectedSubscriptions({ enabled: true }, '恢复')
const enableSelectedAutoDownload = () => updateSelectedSubscriptions({ auto_download: true }, '开启自动策略'), disableSelectedAutoDownload = () => updateSelectedSubscriptions({ auto_download: false }, '关闭自动策略')

async function remove(id) {
  try { await api.deleteSubscription(id); await syncSubscriptionState(); subs.value = subs.value.filter(s => s.id !== id); closeSheet(); ElMessage.success('已取消订阅') }
  catch (e) { ElMessage.error('删除失败') }
}

async function removeSelectedSubscriptions() {
  const selectedIds = new Set(selectedSubscriptionIds.value)
  const selectedSubs = subs.value.filter(sub => selectedIds.has(subscriptionKey(sub)))
  if (selectedSubs.length === 0) return
  try {
    for (const sub of selectedSubs) await api.deleteSubscription(sub.id)
    await syncSubscriptionState()
    subs.value = subs.value.filter(sub => !selectedIds.has(subscriptionKey(sub)))
    clearSubscriptionSelection()
    if (subs.value.length === 0) subscriptionEditMode.value = false
    ElMessage.success(`已取消 ${selectedSubs.length} 个订阅`)
  } catch (e) {
    ElMessage.error('批量取消失败')
  }
}

function viewCandidates(sub) {
  router.push({
    path: '/candidates',
    query: { status: 'candidate', source: 'subscription', actress_id: sub.actress_id }
  })
}

onMounted(loadSubs)
</script>

<style scoped src="../features/subscription/subscription.css"></style>

<template>
  <div class="today-page page-bleed">
    <div class="today-topbar">
      <div class="today-topbar__title">
        <h1>今日</h1>
        <p class="today-topbar__sub">{{ todaySubtitle }}</p>
      </div>
      <div class="today-topbar__spacer"></div>
      <button
        v-if="!searchOpen"
        class="today-search"
        type="button"
        aria-label="搜索影片"
        @click="searchOpen = true"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" width="17" height="17" aria-hidden="true">
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.35-4.35" />
        </svg>
        <span>搜索影片 / 番号 / 演员</span>
      </button>
      <button
        v-else
        class="today-search today-search--back"
        type="button"
        aria-label="返回今日"
        @click="searchOpen = false"
      >
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" width="17" height="17" aria-hidden="true">
          <polyline points="15 18 9 12 15 6" />
        </svg>
        <span>返回今日</span>
      </button>
      <button v-if="!searchOpen" class="today-iconbtn" type="button" aria-label="刷新" @click="loadAll">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" width="18" height="18" aria-hidden="true">
          <polyline points="23 4 23 10 17 10" />
          <path d="M20.49 15a9 9 0 11-2.12-9.36L23 10" />
        </svg>
      </button>
    </div>

    <Search v-if="searchOpen" embedded class="today-embed-search" />

    <div v-show="!searchOpen" class="today-page__rail">
      <section v-if="hero" class="today-hero" @click="openVideo(hero)">
        <div class="today-hero__art" :style="heroArtStyle" aria-hidden="true"></div>
        <div class="today-hero__scrim" aria-hidden="true"></div>
        <div class="today-hero__body">
          <span class="today-hero__kicker">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" width="13" height="13" aria-hidden="true">
              <circle cx="12" cy="12" r="10" />
              <polyline points="12 6 12 12 16 14" />
            </svg>
            最近查看
          </span>
          <h2 class="today-hero__title" :title="heroTitle">{{ heroTitle }}</h2>
          <p class="today-hero__meta">{{ heroMeta }}</p>
          <div class="today-hero__actions">
            <button class="btn today-hero__btn-primary" type="button" @click.stop="openVideo(hero)">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" width="14" height="14" aria-hidden="true">
                <polyline points="9 18 15 12 9 6" />
              </svg>
              查看详情
            </button>
          </div>
        </div>
      </section>
      <AppleErrorState
        v-else-if="heroError"
        class="today-section today-section--error"
        title="最近查看加载失败"
        :description="heroError"
        next-step="可以单独重试,或继续浏览其它区块。"
        source-label="JavInfo · /v1/videos"
        retry-label="重试"
        :retrying="heroRetrying"
        @retry="loadHero"
      />

      <section v-if="continueItems.length" class="today-section">
        <header class="today-section__head">
          <h2>继续观看</h2>
          <span class="today-section__count">{{ continueItems.length }} 部</span>
        </header>
        <div class="today-sub-grid">
          <div
            v-for="item in continueItems"
            :key="`cw-${item.content_id}`"
            class="today-continue"
          >
            <AppleVideoCard
              v-if="item.video"
              :video="item.video"
              @open="openVideo($event)"
            />
            <div
              v-else
              class="today-continue__fallback"
              role="button"
              tabindex="0"
              @click="openVideo({ content_id: item.content_id })"
            >
              <span class="today-continue__code">{{ item.content_id }}</span>
            </div>
            <div class="today-continue__bar" aria-hidden="true">
              <span :style="{ transform: `scaleX(${continueRatio(item)})` }"></span>
            </div>
          </div>
        </div>
      </section>

      <section class="today-section">
        <div class="today-stat-strip">
          <component
            :is="stat.to ? 'router-link' : 'div'"
            v-for="stat in statItems"
            :key="stat.key"
            :to="stat.to"
            class="today-stat"
          >
            <div class="today-stat__top">
              <span class="today-stat__label">{{ stat.label }}</span>
              <span class="today-stat__icon" v-html="stat.icon"></span>
            </div>
            <div class="today-stat__num">{{ stat.value }}</div>
            <div v-if="stat.delta" :class="['today-stat__delta', stat.deltaTone]">
              {{ stat.delta }}
            </div>
          </component>
        </div>
      </section>

      <section v-if="attentionItems.length" class="today-section">
        <header class="today-section__head">
          <h2>待处理</h2>
          <span class="today-section__count">{{ attentionItems.length }} 项</span>
        </header>
        <div class="today-attn-grid">
          <article
            v-for="item in attentionItems"
            :key="item.key"
            class="today-attn"
          >
            <div class="today-attn__top">
              <span :class="['today-attn__icon', `tone-${item.tone}`]" v-html="item.icon"></span>
              <h3 class="today-attn__title">{{ item.title }}</h3>
            </div>
            <p class="today-attn__desc">{{ item.desc }}</p>
            <div class="today-attn__actions">
              <router-link v-if="item.primary" :to="item.primary.to" class="btn today-attn__btn-primary">
                {{ item.primary.label }}
              </router-link>
              <router-link v-if="item.secondary" :to="item.secondary.to" class="btn today-attn__btn-ghost">
                {{ item.secondary.label }}
              </router-link>
            </div>
          </article>
        </div>
      </section>

      <section class="today-section">
        <header class="today-section__head">
          <h2>下载中</h2>
          <span class="today-section__count">{{ activeDownloads.length }} 个任务</span>
          <span class="today-section__spacer"></span>
          <router-link to="/downloads" class="today-section__link">
            下载队列
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" width="13" height="13" aria-hidden="true">
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </router-link>
        </header>
        <AppleErrorState
          v-if="downloadsError"
          class="today-section--error"
          title="下载任务加载失败"
          :description="downloadsError"
          next-step="只会重拉下载任务列表,不会刷整页其它区块。"
          source-label="JavHub · /v1/downloads"
          retry-label="重试"
          :retrying="downloadsRetrying"
          @retry="loadDownloads"
        />
        <div v-else-if="activeDownloads.length" class="today-dl-list">
          <div
            v-for="dl in activeDownloads.slice(0, 4)"
            :key="dl.id"
            class="today-dl"
          >
            <div class="today-dl__thumb" :style="thumbStyle(dl)" aria-hidden="true"></div>
            <div class="today-dl__info">
              <div class="today-dl__name" :title="dl.name">{{ dl.name }}</div>
              <div class="today-dl__meta">
                <span v-if="dl.code" class="today-dl__code">{{ dl.code }}</span>
                <span v-if="dl.size">{{ dl.size }}</span>
                <span v-if="dl.peers != null">{{ dl.peers }} peers</span>
                <span v-if="dl.eta">剩余 {{ dl.eta }}</span>
              </div>
              <div class="today-dl__bar" aria-hidden="true">
                <span :style="{ transform: `scaleX(${dl.pct / 100})` }"></span>
              </div>
            </div>
            <div class="today-dl__right">
              <div class="today-dl__pct">{{ dl.pct }}%</div>
              <div v-if="dl.speed" class="today-dl__speed">{{ dl.speed }}</div>
            </div>
          </div>
        </div>
        <p v-else class="today-empty">当前没有下载中的任务。</p>
      </section>

      <section v-if="subscriptionUpdates.length || subscriptionUpdatesError" class="today-section">
        <header class="today-section__head">
          <h2>订阅更新</h2>
          <span v-if="!subscriptionUpdatesError" class="today-section__count">{{ subscriptionUpdates.length }} 部新片</span>
          <span class="today-section__spacer"></span>
          <router-link to="/subscription" class="today-section__link">
            演员订阅
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" width="13" height="13" aria-hidden="true">
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </router-link>
        </header>
        <AppleErrorState
          v-if="subscriptionUpdatesError"
          class="today-section--error"
          title="订阅更新加载失败"
          :description="subscriptionUpdatesError"
          next-step="只会重拉订阅更新,不会刷整页其它区块。"
          source-label="JavHub · /v1/subscriptions/new-movies"
          retry-label="重试"
          :retrying="subscriptionUpdatesRetrying"
          @retry="loadSubscriptionUpdates"
        />
        <div v-else class="today-sub-grid">
          <AppleVideoCard
            v-for="video in subscriptionUpdates.slice(0, 6)"
            :key="video.content_id || video.dvd_id || video.id"
            :video="video"
            @open="openVideo($event)"
          />
        </div>
      </section>
    </div>
  </div>
</template>

<script>
import { defineComponent, defineAsyncComponent } from 'vue'
import api, { formatApiError } from '../api'
import AppleVideoCard from '../components/AppleVideoCard.vue'
import AppleErrorState from '../components/AppleErrorState.vue'
// 内嵌检索按需加载，避免把整套检索打进首页初始包。
const Search = defineAsyncComponent(() => import('./Search.vue'))
import { normalizeVideo } from '../utils/videoNormalize.js'
import { openVideoModal } from '../utils/modalState.js'

const ICON_LIBRARY = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" width="18" height="18"><path d="M4 19.5A2.5 2.5 0 016.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 014 19.5v-15A2.5 2.5 0 016.5 2z"/></svg>'
const ICON_DOWNLOAD = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" width="18" height="18"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>'
const ICON_STAR = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" width="18" height="18"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>'
const ICON_HEART = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" width="18" height="18"><path d="M20.84 4.61a5.5 5.5 0 00-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 00-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 000-7.78z"/></svg>'
const ICON_CHECK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" width="19" height="19"><polyline points="20 6 9 17 4 12"/></svg>'
const ICON_ALERT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" width="19" height="19"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>'
const ICON_SUPPLEMENT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" width="19" height="19"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>'

const HERO_STORAGE_KEY = 'javhub_today_last_opened'
// P3-2: 缓存最近查看 7 天即视为过期 — 比 hero 这种快被替换的引用足够,也避免久旧记录卡住首屏。
const HERO_STORAGE_MAX_AGE_MS = 7 * 24 * 60 * 60 * 1000

function readHeroFromStorage() {
  if (typeof localStorage === 'undefined') return null
  try {
    const raw = localStorage.getItem(HERO_STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object') return null
    const video = parsed.video || parsed
    if (!video || (!video.content_id && !video.dvd_id)) return null
    const savedAt = Number(parsed.savedAt)
    if (Number.isFinite(savedAt) && (Date.now() - savedAt) > HERO_STORAGE_MAX_AGE_MS) {
      return null
    }
    return { video, savedAt: Number.isFinite(savedAt) ? savedAt : null }
  } catch (err) {
    return null
  }
}

function dropHeroStorage() {
  if (typeof localStorage === 'undefined') return
  try { localStorage.removeItem(HERO_STORAGE_KEY) } catch (err) { /* private mode */ }
}

function formatErrorMessage(error, action) {
  if (!error) return `${action}失败`
  if (formatApiError) {
    return formatApiError(error, { service: 'JavHub', action, fallback: `${action}失败,请稍后重试。` }).message
  }
  return error.message || `${action}失败`
}

export default defineComponent({
  name: 'Today',
  components: { AppleVideoCard, AppleErrorState, Search },
  data() {
    return {
      searchOpen: false,
      hero: null,
      continueItems: [],
      activeDownloads: [],
      candidateSummary: { candidate: 0, missing_magnet: 0, approved: 0, rejected: 0 },
      missingActressesCount: 0,
      subscriptionUpdates: [],
      libraryTotal: null,
      subscribedActressCount: null,
      loading: false,
      // P3-1: 每个 loader 自记 xxxError,失败时区块用 AppleErrorState 显示重试,
      // 不再静默置空让"加载失败"与"真没数据"混在一起。
      heroError: '',
      heroRetrying: false,
      downloadsError: '',
      downloadsRetrying: false,
      candidateSummaryError: '',
      missingActressesError: '',
      subscriptionUpdatesError: '',
      subscriptionUpdatesRetrying: false,
      libraryCountError: '',
      subscribedCountError: '',
    }
  },
  computed: {
    todaySubtitle() {
      const today = new Date()
      const weekdayNames = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
      const m = today.getMonth() + 1
      const d = today.getDate()
      const w = weekdayNames[today.getDay()]
      const pendingTotal = this.candidateSummary.candidate + this.missingActressesCount
      const pendingHint = pendingTotal > 0 ? ` · ${pendingTotal} 项待处理` : ''
      return `${m} 月 ${d} 日 · ${w}${pendingHint}`
    },
    heroTitle() {
      if (!this.hero) return ''
      const n = normalizeVideo(this.hero)
      return n.title_ja || n.title_en || n.display_code || '继续浏览'
    },
    heroMeta() {
      if (!this.hero) return ''
      const n = normalizeVideo(this.hero)
      const parts = []
      if (n.display_code) parts.push(n.display_code)
      if (n.maker || n.studio) parts.push(n.maker || n.studio)
      if (n.release_date) parts.push(n.release_date)
      return parts.join(' · ')
    },
    heroArtStyle() {
      if (!this.hero) return {}
      const n = normalizeVideo(this.hero)
      const cover = n.jacket_full_url || n.jacket_thumb_url
      if (!cover) return {}
      return {
        backgroundImage: `url(${cover})`,
      }
    },
    statItems() {
      // 精修 4: delta 要么给新信息要么不给;只在确实正向时用绿,积压/中性走 flat。
      const fastestPct = this.activeDownloads.length > 0
        ? Math.max(...this.activeDownloads.map(d => Number(d.pct) || 0))
        : 0
      const pendingDelta = this.candidateSummary.candidate > 0
        ? `${this.candidateSummary.candidate} 候选${this.candidateSummary.missing_magnet ? ` · ${this.candidateSummary.missing_magnet} 缺档` : ''}`
        : '已清空'
      return [
        {
          key: 'library',
          label: '影库',
          value: this.libraryTotal != null ? this.formatNumber(this.libraryTotal) : '—',
          // 暂无"本周新增"数据源,留空胜过回显总数。
          delta: '',
          deltaTone: 'flat',
          icon: ICON_LIBRARY,
          to: '/search',
        },
        {
          key: 'downloading',
          label: '下载中',
          value: this.formatNumber(this.activeDownloads.length),
          delta: this.activeDownloads.length > 0 ? `${fastestPct}% 最快` : '空闲',
          deltaTone: 'flat',
          icon: ICON_DOWNLOAD,
          to: '/downloads',
        },
        {
          key: 'subs',
          label: '订阅演员',
          value: this.subscribedActressCount != null ? this.formatNumber(this.subscribedActressCount) : '—',
          delta: this.subscriptionUpdates.length > 0 ? `+${this.subscriptionUpdates.length} 新片` : '本期无更新',
          deltaTone: this.subscriptionUpdates.length > 0 ? 'up' : 'flat',
          icon: ICON_STAR,
          to: '/subscription',
        },
        {
          key: 'pending',
          label: '待处理',
          value: this.formatNumber(this.candidateSummary.candidate + this.missingActressesCount),
          delta: pendingDelta,
          // 积压不是好事,走中性灰。
          deltaTone: 'flat',
          icon: ICON_CHECK,
          to: '/candidates',
        },
      ]
    },
    attentionItems() {
      const items = []
      if (this.candidateSummary.candidate > 0) {
        items.push({
          key: 'candidate',
          tone: 'warn',
          icon: ICON_ALERT,
          title: '候选确认',
          desc: `订阅有 ${this.candidateSummary.candidate} 个新候选等待审核。`,
          primary: { label: '去确认', to: '/candidates' },
          secondary: this.candidateSummary.missing_magnet > 0
            ? { label: `缺磁力 ${this.candidateSummary.missing_magnet}`, to: '/candidates' }
            : null,
        })
      }
      if (this.missingActressesCount > 0) {
        items.push({
          key: 'supplement',
          tone: 'info',
          icon: ICON_SUPPLEMENT,
          title: '资料补全',
          desc: `${this.missingActressesCount} 位演员档案缺失，等待补全。`,
          primary: { label: '去补全', to: '/supplement' },
        })
      }
      return items
    },
  },
  mounted() {
    this.loadAll()
  },
  methods: {
    formatNumber(value) {
      if (value == null) return '—'
      const num = Number(value)
      if (!Number.isFinite(num)) return String(value)
      return num.toLocaleString('zh-CN')
    },
    thumbStyle(dl) {
      const cover = dl.jacket_thumb_url || dl.jacket_full_url || dl.cover_url
      if (!cover) return {}
      return {
        backgroundImage: `url(${cover})`,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
      }
    },
    openVideo(video) {
      if (!video) return
      const safe = {
        ...video,
        content_id: video.content_id || video.dvd_id || video.code || video.id,
        display_code: video.display_code || video.dvd_id || video.content_id,
      }
      // P3-2: 写入时带 savedAt;读出时 7 天过期/取详情 404 都会丢弃。
      if (typeof localStorage !== 'undefined') {
        try {
          localStorage.setItem(HERO_STORAGE_KEY, JSON.stringify({ video: safe, savedAt: Date.now() }))
        } catch (err) {
          // localStorage may throw in private mode; non-fatal.
        }
      }
      // 与全站一致:打开全局详情弹窗,而不是把用户甩进搜索页
      openVideoModal(video, '/')
    },
    async loadAll() {
      if (this.loading) return
      this.loading = true
      try {
        await Promise.allSettled([
          this.loadHero(),
          this.loadContinueWatching(),
          this.loadDownloads(),
          this.loadCandidateSummary(),
          this.loadMissingActresses(),
          this.loadSubscriptionUpdates(),
          this.loadLibraryCount(),
          this.loadSubscribedCount(),
        ])
      } finally {
        this.loading = false
      }
    },
    // P3-2: 优先读 localStorage 缓存,但用 savedAt 校验时效,再用 api.getVideo
    // 校验番号还在;失效就丢缓存,回退到"最新入库第一部"。404 / 显式失败都算失效。
    async loadHero() {
      this.heroError = ''
      this.heroRetrying = true
      try {
        const stored = readHeroFromStorage()
        if (stored?.video) {
          const code = stored.video.content_id || stored.video.dvd_id
          if (code) {
            try {
              const resp = await api.getVideo(code, { service_code: stored.video.service_code })
              const fresh = resp?.data?.data || resp?.data
              if (fresh && (fresh.content_id || fresh.dvd_id)) {
                this.hero = fresh
                return
              }
              // 接口返回空体:同 404 处理,丢缓存。
              dropHeroStorage()
            } catch (err) {
              if (err?.response?.status === 404) {
                dropHeroStorage()
              } else {
                // 非 404 错误(网络/5xx)— 仍可用缓存影片维持 hero,不阻塞首屏。
                this.hero = stored.video
                return
              }
            }
          }
        }
        // 回退到"最新入库第一部"。
        const res = await api.searchVideos({ page: 1, page_size: 1, sort: 'release_date_desc' })
        const list = res?.data?.data || res?.data?.items || []
        if (list.length) {
          this.hero = list[0]
        } else {
          this.hero = null
        }
      } catch (err) {
        this.hero = null
        this.heroError = formatErrorMessage(err, '加载最近查看')
      } finally {
        this.heroRetrying = false
      }
    },
    async loadDownloads() {
      this.downloadsError = ''
      this.downloadsRetrying = true
      try {
        const res = await api.getDownloads()
        const list = Array.isArray(res?.data) ? res.data : (res?.data?.data || res?.data?.items || [])
        this.activeDownloads = list
          .map(this.normalizeDownload)
          .filter(item => item.status === 'downloading' || item.status === 'queued')
      } catch (err) {
        this.activeDownloads = []
        this.downloadsError = formatErrorMessage(err, '加载下载任务')
      } finally {
        this.downloadsRetrying = false
      }
    },
    normalizeDownload(raw) {
      const pct = Number(raw?.progress ?? raw?.percent ?? raw?.pct ?? 0)
      return {
        id: raw?.id || raw?.task_id || raw?.hash || raw?.name,
        name: raw?.name || raw?.title || raw?.title_ja || raw?.display_code || '未命名任务',
        code: raw?.code || raw?.display_code || raw?.dvd_id || raw?.content_id || '',
        size: raw?.size_human || raw?.size || '',
        peers: raw?.peers ?? raw?.num_peers ?? null,
        eta: raw?.eta || raw?.eta_human || '',
        speed: raw?.speed_human || raw?.speed || raw?.dlspeed_human || '',
        pct: Math.round(Math.max(0, Math.min(100, Number.isFinite(pct) ? pct : 0))),
        status: raw?.status || (pct >= 100 ? 'done' : 'downloading'),
        jacket_thumb_url: raw?.jacket_thumb_url || raw?.cover_url || '',
      }
    },
    async loadCandidateSummary() {
      this.candidateSummaryError = ''
      try {
        const res = await api.getDownloadCandidateSummary()
        const data = res?.data || {}
        this.candidateSummary = {
          candidate: Number(data.candidate ?? data.pending ?? 0) || 0,
          missing_magnet: Number(data.missing_magnet ?? data.no_magnet ?? 0) || 0,
          approved: Number(data.approved ?? 0) || 0,
          rejected: Number(data.rejected ?? 0) || 0,
        }
      } catch (err) {
        this.candidateSummary = { candidate: 0, missing_magnet: 0, approved: 0, rejected: 0 }
        this.candidateSummaryError = formatErrorMessage(err, '加载候选汇总')
      }
    },
    async loadMissingActresses() {
      this.missingActressesError = ''
      try {
        const res = await api.getMissingActresses()
        const list = res?.data?.data || res?.data?.items || res?.data || []
        this.missingActressesCount = Array.isArray(list) ? list.length : Number(res?.data?.total || 0)
      } catch (err) {
        this.missingActressesCount = 0
        this.missingActressesError = formatErrorMessage(err, '加载缺失演员')
      }
    },
    async loadContinueWatching() {
      // 失败静默：继续观看是增强区块，没有数据/接口失败时整块隐藏
      try {
        const res = await api.getContinueWatching(6)
        const items = res?.data?.items || []
        this.continueItems = items.map(item => ({
          ...item,
          video: item.video ? normalizeVideo(item.video) : null,
        }))
      } catch (err) {
        this.continueItems = []
      }
    },
    continueRatio(item) {
      const duration = Number(item.duration_seconds || 0)
      if (!duration) return 0
      return Math.min(Math.max(Number(item.position_seconds || 0) / duration, 0), 1)
    },
    async loadSubscriptionUpdates() {
      this.subscriptionUpdatesError = ''
      this.subscriptionUpdatesRetrying = true
      try {
        const res = await api.getNewMovies({ page: 1, page_size: 12 })
        const list = res?.data?.data || res?.data?.items || []
        this.subscriptionUpdates = Array.isArray(list) ? list : []
      } catch (err) {
        this.subscriptionUpdates = []
        this.subscriptionUpdatesError = formatErrorMessage(err, '加载订阅更新')
      } finally {
        this.subscriptionUpdatesRetrying = false
      }
    },
    async loadLibraryCount() {
      this.libraryCountError = ''
      try {
        const res = await api.searchVideos({ page: 1, page_size: 1, include_total: true })
        const total = res?.data?.total ?? res?.data?.count ?? res?.data?.data?.length ?? null
        if (total != null) this.libraryTotal = Number(total)
      } catch (err) {
        this.libraryCountError = formatErrorMessage(err, '加载影库总数')
      }
    },
    async loadSubscribedCount() {
      this.subscribedCountError = ''
      try {
        const res = await api.getSubscriptions()
        const list = res?.data?.data || res?.data?.items || res?.data || []
        this.subscribedActressCount = Array.isArray(list) ? list.length : 0
      } catch (err) {
        this.subscribedCountError = formatErrorMessage(err, '加载订阅数量')
      }
    },
  },
})
</script>

<style scoped src="../features/today/today.css"></style>

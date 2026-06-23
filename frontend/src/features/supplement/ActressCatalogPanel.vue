<template>
  <section class="catalog-panel">
    <!-- hero -->
    <div class="sup-hero">
      <div class="sup-hero-av" :style="avatarUrl ? null : avatarStyle">
        <img v-if="avatarUrl" :src="avatarUrl" :alt="name" loading="eager" decoding="async" @error="onAvatarError" />
        <span v-else>{{ avatarLetter }}</span>
      </div>
      <div class="sup-hero-id">
        <h2>{{ name }}</h2>
        <div class="sh-sub">
          <template v-if="original">{{ original }} · </template>全部作品 {{ totalFilms }} 部<template v-if="recentText"> · {{ recentText }}</template>
        </div>
        <div class="sh-status">
          <span v-if="statusKey !== 'idle' && statusText" class="status-pill" :class="`status-${statusKey}`">{{ statusText }}</span>
          <span v-if="newFindText" class="sh-recent">{{ newFindText }}</span>
        </div>
      </div>
      <div class="sup-hero-actions">
        <button class="btn btn-primary" type="button" :disabled="recomputing" @click="$emit('recompute')">
          <span v-if="recomputing" class="spin-ring" aria-hidden="true"></span>
          {{ recomputing ? '补全中…' : '重新补全这位演员' }}
        </button>
        <button class="btn btn-ghost btn-sm" type="button" @click="$emit('back')">返回演员列表</button>
        <button class="btn btn-ghost btn-sm" type="button" @click="$emit('view-all')">查看全部待补全</button>
      </div>
    </div>

    <!-- completeness duo -->
    <div class="cmp-strip">
      <div class="cmp-meter">
        <div class="cmp-top">
          <span class="cmp-label">收藏 <small>已入库 / 全部</small></span>
          <span class="cmp-val"><b>{{ ownedCount }}</b>/ {{ totalFilms }} 部</span>
        </div>
        <div class="cmp-bar collect"><i :style="{ width: collectPct }"></i></div>
      </div>
      <div class="cmp-meter">
        <div class="cmp-top">
          <span class="cmp-label">资料 <small>已入库作品的资料完整度</small></span>
          <span class="cmp-val"><b>{{ metaCompleteCount }}</b>/ {{ ownedCount }} 齐全</span>
        </div>
        <div class="cmp-bar meta"><i :style="{ width: metaPct }"></i></div>
      </div>
    </div>

    <!-- stage filter -->
    <div class="stage-filter">
      <button
        v-for="chip in stageChips"
        :key="chip.key"
        type="button"
        class="chip"
        :class="{ on: activeStage === chip.key }"
        @click="activeStage = chip.key"
      >
        <span v-if="chip.tone" class="d" :class="chip.tone"></span>{{ chip.label }}
        <span class="n">{{ chip.count }}</span>
      </button>
    </div>

    <!-- search + sort toolbar -->
    <div v-if="films.length" class="catalog-toolbar">
      <label class="catalog-search">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true">
          <circle cx="11" cy="11" r="7"></circle><path d="M16.5 16.5 21 21"></path>
        </svg>
        <input v-model="query" type="search" placeholder="搜索番号或片名" aria-label="搜索番号或片名" />
      </label>
      <div class="catalog-sort">
        <span class="catalog-sort-label">排序</span>
        <select v-model="sortKey" aria-label="排序方式">
          <option value="date_desc">出演时间 · 新→旧</option>
          <option value="date_asc">出演时间 · 旧→新</option>
          <option value="number">番号 · A→Z</option>
        </select>
      </div>
      <span class="catalog-count">共 {{ sortedFilms.length }} 部</span>
    </div>

    <!-- work list -->
    <AppleSkeleton v-if="loading && !films.length" class="panel-state" variant="list" :items="6" label="作品目录加载中" />

    <AppleEmptyState
      v-else-if="!films.length"
      class="panel-state"
      title="还没有作品目录"
      description="这位演员的作品目录还没有结果。"
      next-step="点「重新补全这位演员」拉取她的完整作品集。"
      action-label="重新补全这位演员"
      density="compact"
      @action="$emit('recompute')"
    />

    <AppleEmptyState
      v-else-if="!sortedFilms.length"
      class="panel-state"
      title="没有匹配的作品"
      :description="query ? `没有番号或片名匹配「${query}」的作品。` : '当前筛选下没有作品。'"
      next-step="换一个关键词，或切到「全部」阶段。"
      action-label="清除搜索与筛选"
      density="compact"
      @action="resetFilters"
    />

    <div v-else class="field-list">
      <div
        v-for="film in pagedFilms"
        :key="film.canonical_number"
        class="cand-card"
        :class="{ dim: film.stage === 'complete' }"
      >
        <div class="cc-poster">
          <img v-if="coverUrl(film)" :src="coverUrl(film)" :alt="film.display_code || film.canonical_number" loading="lazy" decoding="async" @error="onCoverError" />
          <div v-else class="cc-poster-placeholder">
            <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="m3 16 5-5 4 4 3-3 6 6"/></svg>
          </div>
          <div class="cc-scrim"></div>
          <span class="cc-code">{{ film.display_code || film.canonical_number }}</span>
        </div>

        <div class="cc-main">
          <div class="cc-srcline">
            <span class="src-pill">{{ originLabel(film) }}</span>
            <span class="cc-tag">{{ tagText(film) }}</span>
          </div>
          <div class="cc-title" :title="film.title || ''">{{ film.title || film.display_code || film.canonical_number }}</div>
          <div class="cc-orig">
            <template v-if="film.release_date">{{ film.release_date.slice(0, 7) }} · </template>
            <span class="why-link" @click="$emit('open-sources', film)">{{ film.stage === 'meta_gap' ? '看缺什么字段' : '为什么在这' }}</span>
          </div>
        </div>

        <div class="cc-decide">
          <div class="trail-stage">
            <span class="stage" :class="stageMeta(film).tone">
              <span v-if="film.stage === 'fetching'" class="spin-sm"></span>
              <span v-else class="pd"></span>
              {{ stageMeta(film).label }}
            </span>
          </div>
          <div class="trail-act">
            <button
              v-if="stageMeta(film).action"
              type="button"
              class="btn"
              :class="stageMeta(film).primary ? 'btn-primary' : 'btn-ghost'"
              @click="onAction(film)"
            >{{ stageMeta(film).action }}</button>
            <span v-else-if="film.stage === 'fetching'" class="trail-prog">获取中</span>
            <span v-else-if="film.stage === 'complete'" class="trail-done">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5"/></svg>
            </span>
          </div>
          <button type="button" class="cc-dots" aria-label="诊断与字段来源" @click="$emit('open-sources', film)">⋯</button>
        </div>
      </div>
    </div>

    <div v-if="totalPages > 1" class="catalog-pager">
      <button type="button" class="page-btn" :disabled="page <= 1" @click="page = Math.max(1, page - 1)">上一页</button>
      <span class="page-indicator">{{ page }} / {{ totalPages }}</span>
      <button type="button" class="page-btn" :disabled="page >= totalPages" @click="page = Math.min(totalPages, page + 1)">下一页</button>
    </div>
  </section>
</template>

<script>
import { actressImgUrl } from '../../utils/imageUrl.js'
import { applyImageFallback } from '../../utils/imageFallback.js'
import { displayName } from '../../utils/displayLang.js'
import { STAGE_META, STAGE_ORDER, STAGE_SUMMARY_KEY } from './catalogStage.js'
import AppleSkeleton from '../../components/AppleSkeleton.vue'
import AppleEmptyState from '../../components/AppleEmptyState.vue'

const MISSING_LABELS = { cover: '封面', runtime: '时长', maker: '厂商', label: '厂牌', series: '系列', category: '分类' }

export default {
  name: 'ActressCatalogPanel',
  components: { AppleSkeleton, AppleEmptyState },
  props: {
    actor: { type: Object, default: () => ({}) },
    films: { type: Array, default: () => [] },
    summary: { type: Object, default: () => ({}) },
    loading: { type: Boolean, default: false },
    recomputing: { type: Boolean, default: false },
    statusText: { type: String, default: '待补全' },
    statusKey: { type: String, default: 'idle' },
    recentText: { type: String, default: '' },
  },
  emits: ['find', 'download', 'enrich', 'open-sources', 'recompute', 'back', 'view-all'],
  data() {
    return { activeStage: 'all', query: '', sortKey: 'date_desc', page: 1, pageSize: 24 }
  },
  watch: {
    activeStage() { this.page = 1 },
    query() { this.page = 1 },
    sortKey() { this.page = 1 },
    films() { this.page = 1 },
    totalPages(n) { if (this.page > n) this.page = n },
  },
  computed: {
    name() {
      return displayName(this.actor, 'name_kanji', 'name_romaji')
        || this.actor?.name_kanji || this.actor?.name_romaji || this.actor?.name || '未知演员'
    },
    original() {
      const o = this.actor?.name_kanji || this.actor?.name_romaji || ''
      return o && o !== this.name ? o : ''
    },
    avatarLetter() { return (this.name || '?').slice(0, 1) },
    avatarUrl() { return this.actor?.image_url ? (actressImgUrl(this.actor.image_url) || '') : '' },
    avatarStyle() {
      const seed = String(this.actor?.id || this.name || 'jh')
      let h = 5381
      for (let i = 0; i < seed.length; i++) h = ((h << 5) + h + seed.charCodeAt(i)) & 0xffffffff
      const hue = Math.abs(h) % 360
      return { background: `linear-gradient(135deg, hsl(${hue} 60% 58%), hsl(${(hue + 38) % 360} 55% 46%))` }
    },
    totalFilms() { return this.films.length },
    ownedCount() {
      const s = this.summary || {}
      if (Number.isFinite(s.owned)) return s.owned
      return (s.owned_complete || 0) + (s.owned_meta_gap || 0)
    },
    metaCompleteCount() { return this.summary?.owned_complete || 0 },
    collectPct() { return this.pct(this.ownedCount, this.totalFilms) },
    metaPct() { return this.pct(this.metaCompleteCount, this.ownedCount) },
    newFindText() {
      const n = this.summary?.needs_magnet || 0
      return n ? `${n} 部待找源` : ''
    },
    stageChips() {
      const s = this.summary || {}
      const chips = [{ key: 'all', label: '全部', count: this.totalFilms, tone: null }]
      for (const stage of STAGE_ORDER) {
        chips.push({
          key: stage,
          label: STAGE_META[stage].label,
          tone: STAGE_META[stage].tone,
          count: s[STAGE_SUMMARY_KEY[stage]] || 0,
        })
      }
      return chips
    },
    stageFilms() {
      if (this.activeStage === 'all') return this.films
      return this.films.filter(f => f.stage === this.activeStage)
    },
    searchedFilms() {
      const q = this.query.trim().toLowerCase()
      if (!q) return this.stageFilms
      const qn = q.replace(/[^a-z0-9]/g, '')
      return this.stageFilms.filter(film => {
        const code = `${film.display_code || ''} ${film.canonical_number || ''}`.toLowerCase()
        const title = (film.title || '').toLowerCase()
        return code.includes(q) || (qn && code.replace(/[^a-z0-9]/g, '').includes(qn)) || title.includes(q)
      })
    },
    sortedFilms() {
      const list = [...this.searchedFilms]
      if (this.sortKey === 'number') {
        list.sort((a, b) => String(a.canonical_number || '').localeCompare(String(b.canonical_number || '')))
      } else {
        const dir = this.sortKey === 'date_asc' ? 1 : -1
        list.sort((a, b) => {
          const da = a.release_date || ''
          const db = b.release_date || ''
          if (da === db) return 0
          if (!da) return 1 // undated last regardless of direction
          if (!db) return -1
          return da < db ? -dir : dir
        })
      }
      return list
    },
    totalPages() {
      return Math.max(1, Math.ceil(this.sortedFilms.length / this.pageSize))
    },
    pagedFilms() {
      const start = (this.page - 1) * this.pageSize
      return this.sortedFilms.slice(start, start + this.pageSize)
    },
  },
  methods: {
    pct(num, den) {
      if (!den) return '0%'
      return `${Math.min(100, Math.round((num / den) * 100))}%`
    },
    resetFilters() {
      this.query = ''
      this.activeStage = 'all'
      this.page = 1
    },
    stageMeta(film) { return STAGE_META[film.stage] || STAGE_META.find_source },
    originLabel(film) {
      if (film.status === 'owned') return '已入库'
      return film.origin === 'supplement' ? '私拍 / 外快' : '正片'
    },
    tagText(film) {
      if (film.stage === 'meta_gap') {
        const miss = (film.metadata_missing || []).map(k => MISSING_LABELS[k] || k)
        return miss.length ? `缺 ${miss.slice(0, 3).join(' · ')}` : '元数据待补'
      }
      if (film.stage === 'complete') return '元数据已齐'
      if (film.origin === 'supplement') return '私拍 / 外快'
      return film.member_count > 1 ? `${film.member_count} 个版本` : '番号作品'
    },
    coverUrl(film) {
      const raw = String(film.cover_url || '').trim()
      if (!raw) return ''
      if (/^https?:\/\//i.test(raw)) return raw
      return `https://pics.dmm.co.jp/${raw.replace(/^\/+/, '')}.jpg`
    },
    onAction(film) {
      const event = { find_source: 'find', downloadable: 'download', meta_gap: 'enrich' }[film.stage]
      if (event) this.$emit(event, film)
    },
    onAvatarError(e) { applyImageFallback(e, { label: this.avatarLetter }) },
    onCoverError(e) { e.target.style.visibility = 'hidden' },
  },
}
</script>

<style scoped src="./actressCatalogPanel.css"></style>

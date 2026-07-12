<template>
  <section class="catalog-panel">
    <!-- hero (头像/名字由 SupplementActorHero 统一；本页插入 查看全部待补全 + 收藏/待办 meter) -->
    <SupplementActorHero :actor="actor" :subtitle="`全部作品 ${totalFilms} 部`">
      <!-- 查看全部待补全 是「跳出本演员、看跨演员聚合」——降级为安静的次级文字链接，
           与「重选演员」(顶部 tab 行) 不是同一层级，不再做成并排实心按钮。 -->
      <template #aside>
        <button class="sh-viewall" type="button" @click="$emit('view-all')">
          查看全部待补全
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><polyline points="9 6 15 12 9 18" /></svg>
        </button>
      </template>

      <!-- 收藏 / 待办 进度胶囊(grid 由 SupplementActorHero 提供) -->
      <template #meters>
        <div class="hero-meter">
          <div class="hm-top">
            <span class="hm-label">媒体库 <small>115 已有</small></span>
            <span class="hm-val"><b>{{ ownedCount }}</b> / {{ totalFilms }}</span>
          </div>
          <div class="cmp-bar collect"><i :style="{ width: collectPct }"></i></div>
        </div>
        <div class="hero-meter">
          <div class="hm-top">
            <span class="hm-label">待办 <small>资料 / 获取</small></span>
            <span class="hm-val"><b>{{ fieldsCount }}</b> 待补资料 · <b>{{ sourcesCount }}</b> 待获取</span>
          </div>
          <div class="cmp-bar meta"><i :style="{ width: donePct }"></i></div>
        </div>
      </template>
    </SupplementActorHero>

    <!-- 阶段切换 + 随阶段联动的右侧主操作（影片目录→重新拉片单 / 字段→一键补全 / 下载源→一键查找） -->
    <div class="stage-row">
      <nav class="stage-seg" aria-label="补全阶段">
        <button v-for="seg in segments" :key="seg.key" type="button" :class="{ active: stage === seg.key }" @click="$emit('change-stage', seg.key)">
          {{ seg.label }}<span class="seg-n">{{ seg.count }}</span>
        </button>
      </nav>
      <button
        v-if="primary" class="btn btn-primary stage-primary" type="button"
        :disabled="primary.busy" @click="onPrimary"
      >
        <span v-if="primary.busy" class="spin-ring" aria-hidden="true"></span>
        {{ primary.busy ? primary.busyLabel : primary.label }}
      </button>
    </div>

    <!-- 三阶段共享的工具行：搜索框主导（撑满），筛选收在它右侧（不再领头） -->
    <div class="cat-toolbar">
      <label class="cat-search">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" aria-hidden="true">
          <circle cx="11" cy="11" r="7" /><path d="M21 21l-4.3-4.3" />
        </svg>
        <input v-model="search" type="search" :placeholder="searchPlaceholder" aria-label="搜索作品" />
        <button v-if="search" type="button" class="cat-search-clear" aria-label="清除搜索" @click="search = ''">×</button>
      </label>

      <div v-if="hasFilters" ref="filterRoot" class="cat-filter">
        <button
          type="button" class="filter-trigger"
          :class="{ on: filterOpen, active: activeCount > 0 }"
          :aria-expanded="filterOpen" @click="filterOpen = !filterOpen"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true">
            <path d="M3 6h11M3 12h7M3 18h13" /><circle cx="17.5" cy="6" r="2.2" /><circle cx="13.5" cy="12" r="2.2" /><circle cx="19" cy="18" r="2.2" />
          </svg>
          <span>筛选</span>
          <span v-if="activeCount" class="ft-count">{{ activeCount }}</span>
          <svg class="ft-chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><polyline points="6 9 12 15 18 9" /></svg>
        </button>

        <transition name="fp">
          <div v-if="filterOpen" class="filter-panel" role="dialog" aria-label="作品筛选">
            <!-- 影片目录：资料来源 / 媒体库 / 时间 -->
            <template v-if="stage === 'collection'">
              <div class="fp-row">
                <span class="fp-label">资料来源</span>
                <div class="stage-seg fp-seg" role="group" aria-label="资料来源筛选">
                  <button
                    v-for="opt in originOptions" :key="opt.key" type="button"
                    :class="{ active: originFilter === opt.key }" @click="originFilter = opt.key"
                  >{{ opt.label }}</button>
                </div>
              </div>
              <div class="fp-row">
                <span class="fp-label">媒体库</span>
                <div class="stage-seg fp-seg" role="group" aria-label="媒体库筛选">
                  <button
                    v-for="opt in ownedOptions" :key="opt.key" type="button"
                    :class="{ active: ownedFilter === opt.key }" @click="ownedFilter = opt.key"
                  >{{ opt.label }}</button>
                </div>
              </div>
              <div class="fp-row">
                <span class="fp-label">时间</span>
                <GlassSelect
                  v-model="yearFilter" :options="yearSelectOptions" size="compact"
                  placement="right" placeholder="全部年份" aria-label="出演时间筛选"
                />
              </div>
            </template>

            <!-- 下载源：按生命周期阶段过滤 -->
            <template v-else-if="stage === 'sources'">
              <div class="fp-row fp-row-stack">
                <span class="fp-label">状态</span>
                <div class="stage-seg fp-seg fp-seg-wrap" role="group" aria-label="下载源状态筛选">
                  <button
                    v-for="opt in sourceStageOptions" :key="opt.key" type="button"
                    :class="{ active: sourceStageFilter === opt.key }" @click="sourceStageFilter = opt.key"
                  >{{ opt.label }}<span class="fp-seg-n">{{ opt.count }}</span></button>
                </div>
              </div>
            </template>

            <div class="fp-foot">
              <span class="fp-count">{{ countLabel }}</span>
              <button v-if="activeCount" type="button" class="fp-clear" @click="clearFilters">清除筛选</button>
            </div>
          </div>
        </transition>
      </div>

      <span v-if="resultHint" class="cat-result">{{ resultHint }}</span>
    </div>

    <CatalogCollectionList
      v-if="stage === 'collection'"
      :year-groups="filteredYearGroups" :total-count="totalFilms" :has-filter="collectionFiltered"
      :loading="loading"
      @recompute="$emit('recompute')" @clear-filters="clearAll"
    />
    <CatalogStagePanel
      v-else :tab="stage" :films="filteredStageFilms" :has-filter="stageFiltered" :busy="busy"
      @enrich="$emit('enrich', $event)" @find="$emit('find', $event)"
      @download="$emit('download', $event)" @open-sources="$emit('open-sources', $event)"
    />
  </section>
</template>

<script>
import CatalogCollectionList from './CatalogCollectionList.vue'
import CatalogStagePanel from './CatalogStagePanel.vue'
import SupplementActorHero from './SupplementActorHero.vue'
import GlassSelect from '../../components/GlassSelect.vue'

const ORIGIN_OPTIONS = [
  { key: 'all', label: '全部' },
  { key: 'native', label: 'DMM收录' },
  { key: 'supplement', label: '补充源独有' },
]
const OWNED_OPTIONS = [
  { key: 'all', label: '全部' },
  { key: 'owned', label: '115已有' },
  { key: 'not', label: '115未有' },
]

function normNumber(value) {
  return String(value || '').toUpperCase().replace(/[^A-Z0-9]/g, '')
}

export default {
  name: 'ActressCatalogPanel',
  components: { CatalogCollectionList, CatalogStagePanel, SupplementActorHero, GlassSelect },
  props: {
    actor: { type: Object, default: () => ({}) },
    yearGroups: { type: Array, default: () => [] },
    byTab: { type: Object, default: () => ({ fields: [], sources: [], complete: [] }) },
    summary: { type: Object, default: () => ({}) },
    stage: { type: String, default: 'collection' },
    busy: { type: Object, default: () => ({}) },
    batchBusy: { type: Boolean, default: false },   // 字段「一键补全」运行中
    finding: { type: Boolean, default: false },     // 下载源「一键查找」运行中
    loading: { type: Boolean, default: false },
    recomputing: { type: Boolean, default: false },
  },
  emits: ['change-stage', 'recompute', 'find', 'download', 'enrich', 'enrich-all', 'find-all', 'open-sources', 'view-all'],
  data() {
    return {
      search: '',
      originFilter: 'all', ownedFilter: 'all', yearFilter: 'all',
      sourceStageFilter: 'all',
      filterOpen: false,
    }
  },
  computed: {
    totalFilms() { return this.summary?.total || 0 },
    ownedCount() { return this.summary?.owned || 0 },
    fieldsCount() { return this.summary?.stage_fields || 0 },
    sourcesCount() { return this.summary?.stage_sources || 0 },
    completeCount() { return this.summary?.stage_complete || 0 },
    collectPct() { return this.pct(this.ownedCount, this.totalFilms) },
    donePct() { return this.pct(this.completeCount, this.totalFilms) },
    segments() {
      return [
        { key: 'collection', label: '影片目录', count: this.totalFilms },
        { key: 'fields', label: '字段', count: this.fieldsCount },
        { key: 'sources', label: '下载源', count: this.sourcesCount },
      ]
    },
    // 随阶段联动的主操作；null = 该阶段右侧不放主按钮（字段/下载源 计数为 0 时）。
    primary() {
      if (this.stage === 'fields') {
        if (!this.fieldsCount) return null
        return { event: 'enrich-all', label: '一键补全', busyLabel: '补全中…', busy: this.batchBusy }
      }
      if (this.stage === 'sources') {
        if (!this.sourcesCount) return null
        return { event: 'find-all', label: '一键查找', busyLabel: '查找中…', busy: this.finding }
      }
      return { event: 'recompute', label: '重新拉片单', busyLabel: '补全中…', busy: this.recomputing }
    },
    searchPlaceholder() {
      return this.stage === 'collection' ? '搜索番号 / 片名' : '在本阶段内搜索番号 / 片名'
    },
    originOptions() { return ORIGIN_OPTIONS },
    ownedOptions() { return OWNED_OPTIONS },
    hasFilters() { return this.stage === 'collection' || this.stage === 'sources' },
    allFilms() { return this.yearGroups.flatMap(group => group.films) },
    yearSelectOptions() {
      const years = this.yearGroups.map(group => String(group.year))
      return [{ value: 'all', label: '全部年份' }, ...years.map(year => ({ value: year, label: year }))]
    },
    // ---- 下载源阶段子集（按生命周期）----
    sourceStageFilms() { return this.byTab.sources || [] },
    sourceStageOptions() {
      const by = s => this.sourceStageFilms.filter(f => f.stage === s).length
      return [
        { key: 'all', label: '全部', count: this.sourceStageFilms.length },
        { key: 'find_source', label: '待找源', count: by('find_source') },
        { key: 'downloadable', label: '可下载', count: by('downloadable') },
        { key: 'fetching', label: '获取中', count: by('fetching') },
      ]
    },
    // ---- 过滤：搜索对三阶段都生效，筛选按阶段分别生效 ----
    filteredYearGroups() {
      return this.yearGroups
        .filter(group => this.yearFilter === 'all' || String(group.year) === this.yearFilter)
        .map(group => ({ year: group.year, films: group.films.filter(f => this.matchOrigin(f) && this.matchOwned(f) && this.matchSearch(f)) }))
        .filter(group => group.films.length)
    },
    filteredStageFilms() {
      const base = this.stage === 'fields' ? (this.byTab.fields || []) : this.sourceStageFilms
      return base.filter(f =>
        this.matchSearch(f)
        && (this.stage !== 'sources' || this.sourceStageFilter === 'all' || f.stage === this.sourceStageFilter),
      )
    },
    filteredCollectionCount() { return this.filteredYearGroups.reduce((total, group) => total + group.films.length, 0) },
    // 「筛选」徽标只数下拉里的维度（搜索是独立输入，不计入）。
    activeCount() {
      if (this.stage === 'collection') {
        return [this.originFilter !== 'all', this.ownedFilter !== 'all', this.yearFilter !== 'all'].filter(Boolean).length
      }
      if (this.stage === 'sources') return this.sourceStageFilter !== 'all' ? 1 : 0
      return 0
    },
    collectionFiltered() { return this.activeCount > 0 || !!this.search.trim() },
    stageFiltered() { return this.activeCount > 0 || !!this.search.trim() },
    countLabel() {
      if (this.stage === 'collection') {
        return this.collectionFiltered ? `${this.filteredCollectionCount} / ${this.allFilms.length} 部` : `共 ${this.allFilms.length} 部`
      }
      const total = this.stage === 'fields' ? (this.byTab.fields || []).length : this.sourceStageFilms.length
      return this.stageFiltered ? `${this.filteredStageFilms.length} / ${total} 部` : `共 ${total} 部`
    },
    resultHint() {
      if (this.stage === 'collection') return this.collectionFiltered ? `已筛选 ${this.filteredCollectionCount} 部` : ''
      return this.stageFiltered ? `已筛选 ${this.filteredStageFilms.length} 部` : ''
    },
  },
  watch: {
    // 切换阶段时收起下拉、复位搜索与子筛选，避免带着上一阶段的条件落地。
    stage() {
      this.filterOpen = false
      this.search = ''
      this.sourceStageFilter = 'all'
    },
    filterOpen(open) {
      if (open) {
        document.addEventListener('mousedown', this.onDocPointer)
        document.addEventListener('keydown', this.onKeydown)
      } else {
        document.removeEventListener('mousedown', this.onDocPointer)
        document.removeEventListener('keydown', this.onKeydown)
      }
    },
  },
  beforeUnmount() {
    document.removeEventListener('mousedown', this.onDocPointer)
    document.removeEventListener('keydown', this.onKeydown)
  },
  methods: {
    pct(n, d) { if (!d) return '0%'; return `${Math.min(100, Math.round((n / d) * 100))}%` },
    onPrimary() { if (this.primary && !this.primary.busy) this.$emit(this.primary.event) },
    isOwned(film) { return film.funnel_stage === 'complete' || film.status === 'owned' || film.stage === 'complete' },
    isSupplement(film) { return film.origin === 'supplement' },
    matchOrigin(film) {
      if (this.originFilter === 'all') return true
      return this.originFilter === 'supplement' ? this.isSupplement(film) : !this.isSupplement(film)
    },
    matchOwned(film) {
      if (this.ownedFilter === 'all') return true
      return this.ownedFilter === 'owned' ? this.isOwned(film) : !this.isOwned(film)
    },
    matchSearch(film) {
      const q = this.search.trim().toLowerCase()
      if (!q) return true
      const hay = `${film.display_code || ''} ${film.canonical_number || ''} ${film.title || ''}`.toLowerCase()
      if (hay.includes(q)) return true
      const nq = normNumber(q)
      return !!nq && normNumber(`${film.display_code || ''}${film.canonical_number || ''}`).includes(nq)
    },
    clearFilters() {
      this.originFilter = 'all'
      this.ownedFilter = 'all'
      this.yearFilter = 'all'
      this.sourceStageFilter = 'all'
    },
    clearAll() {
      this.clearFilters()
      this.search = ''
    },
    onDocPointer(event) {
      const root = this.$refs.filterRoot
      if (!root) return
      if (root.contains(event.target) || (event.target.closest && event.target.closest('.glass-select__menu'))) return
      this.filterOpen = false
    },
    onKeydown(event) {
      if (event.key === 'Escape') this.filterOpen = false
    },
  },
}
</script>

<style scoped src="./actressCatalogPanel.css"></style>
<style scoped src="./supplementHero.css"></style>

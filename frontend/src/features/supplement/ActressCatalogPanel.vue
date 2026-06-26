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
          <template v-if="original">{{ original }} · </template>全部作品 {{ totalFilms }} 部
        </div>
      </div>
      <div class="sup-hero-actions">
        <button class="btn btn-ghost btn-sm" type="button" @click="$emit('back')">返回演员列表</button>
        <button class="btn btn-ghost btn-sm" type="button" @click="$emit('view-all')">查看全部待补全</button>
      </div>
    </div>

    <!-- two meters double as the stage switch -->
    <div class="cmp-strip">
      <button class="cmp-meter" type="button" :class="{ on: stage === 'collection' }" @click="$emit('change-stage', 'collection')">
        <div class="cmp-top"><span class="cmp-label">收藏 <small>已入库 / 全部</small></span><span class="cmp-val"><b>{{ ownedCount }}</b>/ {{ totalFilms }} 部</span></div>
        <div class="cmp-bar collect"><i :style="{ width: collectPct }"></i></div>
      </button>
      <button class="cmp-meter" type="button" :class="{ on: stage !== 'collection' }" @click="$emit('change-stage', 'fields')">
        <div class="cmp-top"><span class="cmp-label">待办 <small>字段 / 下载源</small></span><span class="cmp-val"><b>{{ fieldsCount }}</b> 缺字段 · <b>{{ sourcesCount }}</b> 待入库</span></div>
        <div class="cmp-bar meta"><i :style="{ width: donePct }"></i></div>
      </button>
    </div>

    <nav class="stage-seg" aria-label="补全阶段">
      <button v-for="seg in segments" :key="seg.key" type="button" :class="{ active: stage === seg.key }" @click="$emit('change-stage', seg.key)">
        {{ seg.label }}<span class="seg-n">{{ seg.count }}</span>
      </button>
    </nav>

    <CatalogCollectionList
      v-if="stage === 'collection'"
      :year-groups="yearGroups" :owned-count="ownedCount" :total-count="totalFilms"
      :loading="loading" :recomputing="recomputing"
      @recompute="$emit('recompute')" @find="$emit('find', $event)"
    />
    <CatalogStagePanel
      v-else :tab="stage" :films="stage === 'fields' ? byTab.fields : byTab.sources" :busy="busy"
      @enrich="$emit('enrich', $event)" @find="$emit('find', $event)"
      @download="$emit('download', $event)" @open-sources="$emit('open-sources', $event)"
    />
  </section>
</template>

<script>
import { actressImgUrl } from '../../utils/imageUrl.js'
import { applyImageFallback } from '../../utils/imageFallback.js'
import { displayName } from '../../utils/displayLang.js'
import CatalogCollectionList from './CatalogCollectionList.vue'
import CatalogStagePanel from './CatalogStagePanel.vue'

export default {
  name: 'ActressCatalogPanel',
  components: { CatalogCollectionList, CatalogStagePanel },
  props: {
    actor: { type: Object, default: () => ({}) },
    yearGroups: { type: Array, default: () => [] },
    byTab: { type: Object, default: () => ({ fields: [], sources: [], complete: [] }) },
    summary: { type: Object, default: () => ({}) },
    stage: { type: String, default: 'collection' },
    busy: { type: Object, default: () => ({}) },
    loading: { type: Boolean, default: false },
    recomputing: { type: Boolean, default: false },
  },
  emits: ['change-stage', 'recompute', 'find', 'download', 'enrich', 'open-sources', 'back', 'view-all'],
  computed: {
    name() {
      return displayName(this.actor, 'name_kanji', 'name_romaji')
        || this.actor?.name_kanji || this.actor?.name_romaji || this.actor?.name || '未知演员'
    },
    original() { const o = this.actor?.name_kanji || this.actor?.name_romaji || ''; return o && o !== this.name ? o : '' },
    avatarLetter() { return (this.name || '?').slice(0, 1) },
    avatarUrl() { return this.actor?.image_url ? (actressImgUrl(this.actor.image_url) || '') : '' },
    avatarStyle() {
      const seed = String(this.actor?.id || this.name || 'jh'); let h = 5381
      for (let i = 0; i < seed.length; i++) h = ((h << 5) + h + seed.charCodeAt(i)) & 0xffffffff
      const hue = Math.abs(h) % 360
      return { background: `linear-gradient(135deg, hsl(${hue} 60% 58%), hsl(${(hue + 38) % 360} 55% 46%))` }
    },
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
  },
  methods: {
    pct(n, d) { if (!d) return '0%'; return `${Math.min(100, Math.round((n / d) * 100))}%` },
    onAvatarError(e) { applyImageFallback(e, { label: this.avatarLetter }) },
  },
}
</script>

<style scoped src="./actressCatalogPanel.css"></style>

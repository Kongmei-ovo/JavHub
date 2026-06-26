<template>
  <div class="cand-card" :class="{ dim: film.stage === 'complete' }">
    <div class="cc-poster" @click="$emit('open-sources', film)">
      <img v-if="cover" :src="cover" :alt="code" loading="lazy" decoding="async" referrerpolicy="no-referrer" @error="onCoverError" />
      <div v-else class="cc-poster-placeholder">
        <svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="m3 16 5-5 4 4 3-3 6 6"/></svg>
      </div>
      <div class="cc-scrim"></div>
      <span class="cc-code">{{ code }}</span>
    </div>

    <div class="cc-main">
      <div class="cc-srcline">
        <span class="src-pill">{{ stageMeta.label }}</span>
        <span class="cc-tag">{{ tagText }}</span>
      </div>
      <div class="cc-title" :title="film.title || ''">{{ film.title || code }}</div>
      <div class="cc-orig">
        <template v-if="film.release_date">{{ String(film.release_date).slice(0, 7) }} · </template>
        <span class="why-link" @click="$emit('open-sources', film)">{{ tab === 'fields' ? '看缺什么字段' : '为什么在这' }}</span>
      </div>
    </div>

    <div class="cc-decide">
      <div class="trail-act">
        <button v-if="tab === 'fields'" class="btn btn-primary" type="button" :disabled="busy" @click="$emit('enrich', film)">{{ busy ? '排队中…' : '补字段' }}</button>
        <button v-else-if="film.stage === 'downloadable'" class="btn btn-primary" type="button" @click="$emit('download', film)">下载</button>
        <button v-else-if="film.stage === 'find_source'" class="btn btn-ghost" type="button" @click="$emit('find', film)">找源</button>
        <span v-else-if="film.stage === 'fetching'" class="trail-prog">获取中</span>
      </div>
      <button type="button" class="cc-dots" aria-label="诊断与字段来源" @click="$emit('open-sources', film)">⋯</button>
    </div>
  </div>
</template>

<script>
import { STAGE_META } from './catalogStage.js'
const MISSING_LABELS = { cover: '封面', runtime: '时长', maker: '厂商', label: '厂牌', series: '系列', category: '分类' }

export default {
  name: 'CatalogFilmCard',
  props: {
    film: { type: Object, required: true },
    tab: { type: String, default: 'sources' }, // 'fields' | 'sources'
    busy: { type: Boolean, default: false },
  },
  emits: ['enrich', 'find', 'download', 'open-sources'],
  computed: {
    code() { return this.film.display_code || this.film.canonical_number || '—' },
    stageMeta() { return STAGE_META[this.film.stage] || STAGE_META.find_source },
    cover() {
      const raw = String(this.film.cover_url || '').trim()
      if (!raw) return ''
      return /^https?:\/\//i.test(raw) ? raw : `https://pics.dmm.co.jp/${raw.replace(/^\/+/, '')}.jpg`
    },
    tagText() {
      if (this.tab === 'fields') {
        const miss = (this.film.metadata_missing || []).map(k => MISSING_LABELS[k] || k)
        return miss.length ? `缺 ${miss.slice(0, 3).join(' · ')}` : '元数据待补'
      }
      return this.film.origin === 'supplement' ? '私拍 / 外快' : '番号作品'
    },
  },
  methods: {
    onCoverError(e) { e.target.style.visibility = 'hidden' },
  },
}
</script>

<style scoped src="./actressCatalogPanel.css"></style>

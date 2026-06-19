<template>
  <div class="diag-overlay" :class="{ 'diag-overlay--drawer': drawer }" @click.self="$emit('close')">
    <div class="diag-panel" :class="{ 'diag-panel--drawer': drawer }">
      <header class="diag-head">
        <div class="diag-head-text">
          <h2>{{ diagnosticsMovieTitle }}</h2>
          <p v-if="diagnosticsMovieSubtitle">{{ diagnosticsMovieSubtitle }}</p>
        </div>
        <button class="btn btn-ghost btn-sm" type="button" @click="$emit('close')">关闭</button>
      </header>

      <div v-if="sourceDiagnosticsLoading" class="diag-loading"><div class="spinner-large"></div></div>

      <div v-else-if="sourceDiagnostics" class="diag-body">
        <!-- 媒体 -->
        <section class="diag-media">
          <div class="diag-cover">
            <img v-if="coverImage" :src="coverImage" :alt="diagnosticsMovieTitle" loading="lazy" @error="onImgError" />
            <span v-else class="diag-cover-empty">无封面</span>
          </div>
          <div class="diag-media-side">
            <div v-if="actressName" class="diag-actress">
              <img v-if="actressAvatar" :src="actressAvatar" :alt="actressName" class="diag-avatar" @error="onImgError" />
              <span v-else class="diag-avatar diag-avatar--empty">{{ actressName.slice(0, 1) }}</span>
              <strong>{{ actressName }}</strong>
            </div>
            <div class="diag-status">
              <span class="diag-stat" :class="matchTone"><b>{{ matchStatusLabel }}</b><em>匹配状态</em></span>
              <span class="diag-stat"><b>{{ candidateCount }}</b><em>候选</em></span>
              <span class="diag-stat" :class="{ warn: missingFieldCount > 0 }"><b>{{ missingFieldCount }}</b><em>字段缺口</em></span>
            </div>
          </div>
        </section>

        <!-- 剧照 -->
        <section v-if="stillImages.length" class="diag-stills" aria-label="剧照">
          <img
            v-for="(src, i) in stillImages"
            :key="i"
            :src="src"
            loading="lazy"
            @error="onImgError"
            @click="openImage(src)"
          />
        </section>

        <!-- 匹配 -->
        <section class="diag-section">
          <h3>匹配</h3>
          <div class="diag-match-bar">
            <input
              :value="manualContentId"
              placeholder="内容编号(人工确认)"
              class="filter-input"
              @input="$emit('update:manualContentId', $event.target.value)"
              @keyup.enter="$emit('match')"
            />
            <button class="btn btn-primary btn-sm" type="button" :disabled="manualActionLoading || !manualContentId.trim()" @click="$emit('match')">确认匹配</button>
            <button class="btn btn-ghost btn-sm" type="button" :disabled="manualActionLoading" @click="$emit('unmatch')">解除</button>
            <button class="btn btn-ghost btn-sm danger" type="button" :disabled="manualActionLoading" @click="$emit('ignore')">忽略</button>
          </div>
          <table v-if="candidates.length" class="diag-table">
            <thead>
              <tr><th>内容编号</th><th>分数</th><th>状态</th><th></th></tr>
            </thead>
            <tbody>
              <tr v-for="c in candidates" :key="c.candidate_content_id" :class="{ primary: c === candidates[0] }">
                <td>{{ c.candidate_content_id }}<em v-if="c === candidates[0]" class="diag-tag">首选</em></td>
                <td>{{ c.score }}</td>
                <td>{{ c.status }}</td>
                <td><button class="btn btn-ghost btn-xs" type="button" :disabled="manualActionLoading" @click="$emit('match', c.candidate_content_id)">确认</button></td>
              </tr>
            </tbody>
          </table>
          <p v-else class="diag-note">此作品在 r18 目录无候选——多为外快/无码片,匹配不适用。可保留补全数据,或点「忽略」。</p>
        </section>

        <!-- 字段来源(单表,取代原来 6 个重复面板) -->
        <section class="diag-section">
          <h3>字段来源 <span class="diag-sub">{{ missingFieldCount ? `${missingFieldCount} 个缺口` : '已齐' }}</span></h3>
          <table class="diag-table diag-field-table">
            <thead>
              <tr><th>字段</th><th>当前值</th><th>来源</th><th>可补来源</th><th>状态</th></tr>
            </thead>
            <tbody>
              <tr v-for="row in fieldRows" :key="row.key" :class="{ missing: !row.ready }">
                <td>{{ row.label }}</td>
                <td class="diag-val">{{ row.value || '—' }}</td>
                <td>{{ row.source || '—' }}</td>
                <td>{{ row.available || '—' }}</td>
                <td><span class="diag-pill" :class="row.ready ? 'ok' : 'gap'">{{ row.ready ? '已取' : '缺口' }}</span></td>
              </tr>
            </tbody>
          </table>
        </section>

        <!-- 来源详情(可折叠) -->
        <section v-if="details.length" class="diag-section">
          <button class="diag-collapse" type="button" @click="showDetails = !showDetails">
            来源详情 ({{ details.length }})<span>{{ showDetails ? '收起' : '展开' }}</span>
          </button>
          <div v-if="showDetails" class="diag-detail-grid">
            <article v-for="d in details" :key="`${d.source}-${d.source_movie_id}`" class="diag-detail">
              <img v-if="d.cover_url" :src="d.cover_url" loading="lazy" @error="onImgError" />
              <span v-else class="diag-detail-noimg">无图</span>
              <div class="diag-detail-text">
                <strong>{{ d.source }}</strong>
                <small>{{ d.source_movie_id }}</small>
                <span>{{ detailMeta(d) }}</span>
              </div>
            </article>
          </div>
        </section>

        <!-- 源身份 + 人工记录 -->
        <section v-if="hasMeta" class="diag-section diag-meta">
          <div v-if="sourceDiagnostics.identities && sourceDiagnostics.identities.length" class="diag-identities">
            <a
              v-for="id in sourceDiagnostics.identities"
              :key="`${id.source}-${id.source_movie_id}`"
              :href="id.source_url || '#'"
              target="_blank"
              class="diag-id-chip"
            >{{ id.source }}: {{ id.source_movie_id }}</a>
          </div>
          <ul v-if="sourceDiagnostics.manual_actions && sourceDiagnostics.manual_actions.length" class="diag-log">
            <li v-for="a in sourceDiagnostics.manual_actions" :key="`${a.action}-${a.created_at}`">
              <b>{{ manualActionLabel(a.action) }}</b>
              <span>{{ a.content_id || a.previous_content_id || '—' }}</span>
              <small>{{ formatActionTime(a.created_at) }}</small>
            </li>
          </ul>
        </section>
      </div>

      <div v-else class="diag-body"><p class="diag-note">暂无诊断数据</p></div>
    </div>
  </div>
</template>

<script>
import { applyImageFallback } from '../../utils/imageFallback.js'

const FIELD_DEFS = [
  { key: 'title', label: '标题', names: ['title'], movie: ['title'], detail: ['title'] },
  { key: 'release_date', label: '发行日', names: ['release_date'], movie: ['release_date'], detail: ['release_date'] },
  { key: 'runtime', label: '时长', names: ['runtime_mins'], movie: ['runtime_mins'], detail: ['runtime_mins'] },
  { key: 'cover', label: '封面', names: ['cover_url', 'cover_thumb_url'], movie: ['cover_url', 'cover_thumb_url'], detail: ['cover_url'], media: true },
  { key: 'maker', label: '厂商', names: ['maker_name'], movie: ['maker_name'], detail: ['maker_name'] },
  { key: 'label', label: '厂牌', names: ['label_name'], movie: [], detail: ['label_name'] },
  { key: 'series', label: '系列', names: ['series_name'], movie: [], detail: ['series_name'] },
  { key: 'category', label: '分类', names: ['category_names', 'genres'], movie: ['category_names'], detail: ['genres'] },
]

export default {
  name: 'SupplementSourceDiagnosticsDialog',
  props: {
    drawer: { type: Boolean, default: false },
    sourceDiagnosticsLoading: { type: Boolean, default: false },
    sourceDiagnostics: { type: Object, default: null },
    diagnosticsMovieTitle: { type: String, default: '字段来源' },
    diagnosticsMovieSubtitle: { type: String, default: '' },
    manualContentId: { type: String, default: '' },
    manualActionLoading: { type: Boolean, default: false },
    actressName: { type: String, default: '' },
    actressAvatar: { type: String, default: '' },
    fieldLabel: { type: Function, required: true },
    fieldValuePreview: { type: Function, required: true },
    manualActionLabel: { type: Function, required: true },
    formatActionTime: { type: Function, required: true },
  },
  emits: ['close', 'update:manualContentId', 'match', 'unmatch', 'ignore'],
  data() {
    return { showDetails: false }
  },
  computed: {
    movie() {
      return this.sourceDiagnostics?.movie || {}
    },
    details() {
      return this.sourceDiagnostics?.details || []
    },
    coverImage() {
      if (this.movie.cover_url) return this.movie.cover_url
      if (this.movie.cover_thumb_url) return this.movie.cover_thumb_url
      const fromDetail = this.details.find(d => d.cover_url)
      return fromDetail?.cover_url || ''
    },
    stillImages() {
      const seen = new Set()
      const out = []
      for (const d of this.details) {
        for (const url of d.sample_image_urls || []) {
          if (url && !seen.has(url)) {
            seen.add(url)
            out.push(url)
          }
        }
      }
      return out.slice(0, 12)
    },
    candidates() {
      return [...(this.sourceDiagnostics?.match_candidates || [])]
        .sort((a, b) => this.scoreOf(b) - this.scoreOf(a))
    },
    candidateCount() {
      return this.sourceDiagnostics?.match_candidates?.length || 0
    },
    matchStatusLabel() {
      if (this.movie.matched_content_id) return '已匹配'
      if (this.movie.match_status === 'manual_ignored') return '已忽略'
      return '未匹配'
    },
    matchTone() {
      if (this.movie.matched_content_id) return 'ok'
      if (this.movie.match_status === 'manual_ignored') return 'muted'
      return 'warn'
    },
    fieldRows() {
      const chosen = this.sourceDiagnostics?.chosen_fields || []
      return FIELD_DEFS.map(def => {
        const chosenField = chosen.find(c => def.names.includes(c.field_name) && this.hasValue(c.field_value))
        let value = ''
        let source = ''
        if (chosenField) {
          source = chosenField.source
          value = def.media ? '已设置' : this.fieldValuePreview(chosenField.field_value)
        } else {
          const movieVal = def.movie.map(name => this.movie[name]).find(v => this.hasValue(v))
          if (this.hasValue(movieVal)) {
            source = '影片本体'
            value = def.media ? '已设置' : this.fieldValuePreview(movieVal)
          }
        }
        const available = [...new Set(
          this.details
            .filter(d => def.detail.some(name => this.hasValue(d[name])))
            .map(d => d.source),
        )].join(' · ')
        return { key: def.key, label: def.label, value, source, available, ready: this.hasValue(value) }
      })
    },
    missingFieldCount() {
      return this.fieldRows.filter(row => !row.ready).length
    },
    hasMeta() {
      return Boolean(
        this.sourceDiagnostics?.identities?.length ||
        this.sourceDiagnostics?.manual_actions?.length,
      )
    },
  },
  methods: {
    scoreOf(candidate) {
      const score = Number(candidate?.score)
      return Number.isFinite(score) ? score : 0
    },
    hasValue(value) {
      if (Array.isArray(value)) return value.length > 0
      return value !== undefined && value !== null && String(value).trim() !== ''
    },
    detailMeta(detail) {
      return [
        detail.runtime_mins && `${detail.runtime_mins} 分钟`,
        detail.maker_name,
        detail.label_name,
        (detail.genres || []).slice(0, 4).join(' / '),
      ].filter(Boolean).join(' · ')
    },
    onImgError(event) {
      applyImageFallback(event)
    },
    openImage(src) {
      if (src) window.open(src, '_blank', 'noopener')
    },
  },
}
</script>

<style scoped src="./supplementSourceDiagnosticsDialog.css"></style>

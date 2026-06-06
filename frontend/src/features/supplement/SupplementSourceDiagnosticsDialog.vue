<template>
  <div class="diagnostics-overlay" @click.self="$emit('close')">
    <div class="diagnostics-panel apple-surface">
      <div class="diagnostics-header">
        <div>
          <h2>{{ diagnosticsMovieTitle }}</h2>
          <p>{{ diagnosticsMovieSubtitle }}</p>
        </div>
        <button class="btn btn-ghost btn-sm" type="button" @click="$emit('close')">关闭</button>
      </div>
      <div v-if="sourceDiagnosticsLoading" class="loading-wrap"><div class="spinner-large"></div></div>
      <div v-else-if="sourceDiagnostics" class="diagnostics-body">
        <div class="diagnostics-triage">
          <div v-for="card in diagnosticsTriageCards" :key="card.label" class="triage-card">
            <strong>{{ card.value }}</strong>
            <span>{{ card.label }}</span>
          </div>
        </div>
        <div class="diagnostics-action-queue" aria-label="诊断修复优先级">
          <div
            v-for="action in diagnosticsActionQueue"
            :key="action.label"
            class="diagnostics-action-item"
            :class="{ ready: action.ready }"
          >
            <strong>{{ action.label }}</strong>
            <span>{{ action.detail }}</span>
          </div>
        </div>
        <div class="diagnostics-layout">
          <div class="diagnostics-main">
            <section class="diagnostics-section">
              <h3>选中字段</h3>
              <div class="diagnostics-field-checklist" aria-label="诊断字段完整度">
                <span
                  v-for="field in diagnosticsFieldChecklist"
                  :key="field.key"
                  :class="{ missing: !field.ready }"
                >
                  <b>{{ field.label }}</b>
                  <em>{{ field.ready ? '已取' : '缺失' }}</em>
                </span>
              </div>
              <div class="diagnostics-field-source-matrix" aria-label="字段来源矩阵">
                <div class="field-source-row field-source-head">
                  <span>字段</span>
                  <span>影片本体</span>
                  <span>已选字段</span>
                  <span>详情来源</span>
                  <span>状态</span>
                </div>
                <div
                  v-for="row in fieldSourceRepairRows"
                  :key="row.key"
                  class="field-source-row"
                  :class="fieldSourceRepairClass(row)"
                >
                  <span>{{ row.label }}</span>
                  <span
                    v-for="source in row.sources"
                    :key="source.key"
                    class="field-source-pill"
                    :class="{ ready: source.ready }"
                  >{{ source.ready ? '可用' : '缺口' }}</span>
                  <span class="field-source-status">{{ row.ready ? '可用' : '缺口' }}</span>
                </div>
              </div>
              <div v-if="sourceDiagnostics.chosen_fields?.length" class="diagnostics-table">
                <div class="diagnostics-row diagnostics-row-head">
                  <span>字段</span>
                  <span>来源</span>
                  <span>值</span>
                </div>
                <div v-for="field in sourceDiagnostics.chosen_fields" :key="`chosen-${field.field_name}`" class="diagnostics-row">
                  <span>{{ fieldLabel(field.field_name) }}</span>
                  <span>{{ field.source }}</span>
                  <span class="diagnostics-value">{{ fieldValuePreview(field.field_value) }}</span>
                </div>
              </div>
              <div v-else class="empty-inline">暂无字段来源</div>
            </section>
            <section class="diagnostics-section">
              <h3>源身份</h3>
              <div v-if="sourceDiagnostics.identities?.length" class="identity-list">
                <a
                  v-for="identity in sourceDiagnostics.identities"
                  :key="`${identity.source}-${identity.source_movie_id}`"
                  :href="identity.source_url || '#'"
                  class="identity-chip"
                  target="_blank"
                >{{ identity.source }}: {{ identity.source_movie_id }}</a>
              </div>
              <div v-else class="empty-inline">暂无源身份</div>
            </section>
            <section class="diagnostics-section">
              <h3>详情来源</h3>
              <div v-if="sourceDiagnostics.details?.length" class="detail-source-list">
                <div v-for="detail in sourceDiagnostics.details" :key="`${detail.source}-${detail.source_movie_id}`" class="detail-source-item">
                  <strong>{{ detail.source }} · {{ detail.source_movie_id }}</strong>
                  <span>{{ [detail.runtime_mins && `${detail.runtime_mins} 分钟`, detail.maker_name, detail.label_name, detail.genres?.slice(0, 4).join(' / ')].filter(Boolean).join(' · ') }}</span>
                </div>
              </div>
              <div v-else class="empty-inline">暂无详情来源</div>
            </section>
          </div>
          <aside class="manual-match-panel">
            <div>
              <h3>匹配候选</h3>
              <p>{{ candidateCount }} 个候选，{{ missingFieldCount }} 个字段缺口。</p>
            </div>
            <div class="candidate-decision-strip" aria-label="候选决策摘要">
              <span
                v-for="card in candidateDecisionCards"
                :key="card.label"
                class="candidate-decision-card"
                :class="{ warning: card.warning, ready: card.ready }"
              >
                <b>{{ card.label }}</b>
                <em>{{ card.value }}</em>
              </span>
            </div>
            <div class="manual-match-bar">
              <input
                :value="manualContentId"
                placeholder="输入内容编号人工确认"
                class="filter-input"
                @input="$emit('update:manualContentId', $event.target.value)"
                @keyup.enter="$emit('match')"
              />
              <button class="btn btn-primary btn-sm" type="button" :disabled="manualActionLoading || !manualContentId.trim()" @click="$emit('match')">确认匹配</button>
              <button class="btn btn-ghost btn-sm" type="button" :disabled="manualActionLoading" @click="$emit('unmatch')">解除匹配</button>
              <button class="btn btn-ghost btn-sm danger" type="button" :disabled="manualActionLoading" @click="$emit('ignore')">忽略</button>
            </div>
            <div v-if="sourceDiagnostics.match_candidates?.length" class="diagnostics-table">
              <div class="diagnostics-row diagnostics-row-head diagnostics-row-candidates">
                <span>内容编号</span>
                <span>分数</span>
                <span>状态</span>
                <span>操作</span>
              </div>
              <div
                v-for="candidate in sortedCandidates"
                :key="candidate.candidate_content_id"
                class="diagnostics-row diagnostics-row-candidates"
                :class="candidateRowClass(candidate)"
              >
                <span>
                  {{ candidate.candidate_content_id }}
                  <em v-if="candidateDecisionLabel(candidate)" class="candidate-row-decision">{{ candidateDecisionLabel(candidate) }}</em>
                </span>
                <span>{{ candidate.score }}</span>
                <span>{{ candidate.status }}</span>
                <span>
                  <button class="btn btn-ghost btn-xs" type="button" :disabled="manualActionLoading" @click="$emit('match', candidate.candidate_content_id)">确认</button>
                </span>
              </div>
            </div>
            <div v-else class="empty-inline">暂无匹配候选</div>
            <section class="diagnostics-section">
              <h3>人工校正记录</h3>
              <div v-if="sourceDiagnostics.manual_actions?.length" class="manual-action-list">
                <div v-for="action in sourceDiagnostics.manual_actions" :key="`${action.action}-${action.created_at}`" class="manual-action-item">
                  <strong>{{ manualActionLabel(action.action) }}</strong>
                  <span>{{ action.content_id || action.previous_content_id || '无内容编号' }}</span>
                  <small>{{ action.reason || '未填写原因' }} · {{ formatActionTime(action.created_at) }}</small>
                </div>
              </div>
              <div v-else class="empty-inline">暂无人工校正记录</div>
            </section>
          </aside>
        </div>
      </div>
      <div v-else class="diagnostics-body">
        <div class="diagnostics-triage">
          <div class="triage-card">
            <strong>0</strong>
            <span>字段缺口</span>
          </div>
          <div class="triage-card">
            <strong>0</strong>
            <span>候选</span>
          </div>
          <div class="triage-card">
            <strong>0</strong>
            <span>源身份</span>
          </div>
        </div>
        <div class="empty-inline">暂无诊断数据</div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'SupplementSourceDiagnosticsDialog',
  props: {
    sourceDiagnosticsLoading: { type: Boolean, default: false },
    sourceDiagnostics: { type: Object, default: null },
    diagnosticsMovieTitle: { type: String, default: '来源诊断' },
    diagnosticsMovieSubtitle: { type: String, default: '' },
    manualContentId: { type: String, default: '' },
    manualActionLoading: { type: Boolean, default: false },
    fieldLabel: { type: Function, required: true },
    fieldValuePreview: { type: Function, required: true },
    manualActionLabel: { type: Function, required: true },
    formatActionTime: { type: Function, required: true },
  },
  emits: ['close', 'update:manualContentId', 'match', 'unmatch', 'ignore'],
  computed: {
    diagnosticsFieldChecklist() {
      return [
        { key: 'cover', label: '封面', fields: ['cover_thumb_url', 'cover_url'] },
        { key: 'runtime', label: '时长', fields: ['runtime_mins'] },
        { key: 'maker', label: '厂商', fields: ['maker_name'] },
        { key: 'label', label: '厂牌', fields: ['label_name'] },
        { key: 'series', label: '系列', fields: ['series_name'] },
        { key: 'category', label: '分类', fields: ['category_names', 'genres'] },
      ].map(item => ({
        ...item,
        ready: item.fields.some(field => this.fieldHasDiagnosticValue(field)),
      }))
    },
    missingDiagnosticsFields() {
      return this.diagnosticsFieldChecklist.filter(field => !field.ready)
    },
    missingFieldCount() {
      return this.missingDiagnosticsFields.length
    },
    fieldSourceRepairRows() {
      return this.diagnosticsFieldChecklist.map(field => {
        const coverage = this.fieldSourceCoverage(field)
        return {
          key: field.key,
          label: field.label,
          ready: coverage.some(source => source.ready),
          sources: coverage,
        }
      })
    },
    candidateCount() {
      return this.sourceDiagnostics?.match_candidates?.length || 0
    },
    sortedCandidates() {
      return [...(this.sourceDiagnostics?.match_candidates || [])].sort((a, b) => this.candidateScoreValue(b) - this.candidateScoreValue(a))
    },
    topCandidate() {
      return this.sortedCandidates[0] || null
    },
    candidateScoreGap() {
      if (!this.topCandidate) return null
      const secondCandidate = this.sortedCandidates[1]
      if (!secondCandidate) return this.candidateScoreValue(this.topCandidate)
      return Math.max(0, this.candidateScoreValue(this.topCandidate) - this.candidateScoreValue(secondCandidate))
    },
    candidateConfirmationRisk() {
      if (!this.candidateCount) return '暂无候选'
      if (this.sourceDiagnostics?.movie?.matched_content_id) return '已匹配'
      if (this.candidateCount > 1 && this.candidateScoreGap !== null && this.candidateScoreGap < 10) return '需人工复核'
      return '可确认'
    },
    candidateDecisionCards() {
      const needsReview = this.candidateConfirmationRisk === '需人工复核'
      return [
        {
          label: '首选候选',
          value: this.topCandidate?.candidate_content_id || '暂无',
          ready: Boolean(this.topCandidate),
        },
        {
          label: '分差',
          value: this.candidateScoreGap === null ? '—' : this.candidateScoreGap,
          warning: needsReview,
        },
        {
          label: '确认风险',
          value: this.candidateConfirmationRisk,
          warning: needsReview,
          ready: this.candidateConfirmationRisk === '可确认' || this.candidateConfirmationRisk === '已匹配',
        },
      ]
    },
    identityCount() {
      return this.sourceDiagnostics?.identities?.length || 0
    },
    diagnosticsTriageCards() {
      return [
        { label: '字段缺口', value: this.missingFieldCount },
        { label: '候选', value: this.candidateCount },
        { label: '源身份', value: this.identityCount },
      ]
    },
    diagnosticsActionQueue() {
      return [
        {
          label: '补字段',
          detail: this.missingFieldCount ? `${this.missingFieldCount} 个字段待补` : '字段已齐',
          ready: this.missingFieldCount === 0,
        },
        {
          label: '确认匹配',
          detail: this.candidateCount ? `${this.candidateCount} 个候选待确认` : '暂无候选',
          ready: Boolean(this.sourceDiagnostics?.movie?.matched_content_id),
        },
        {
          label: '补源身份',
          detail: this.identityCount ? `${this.identityCount} 个身份可追溯` : '缺少源身份',
          ready: this.identityCount > 0,
        },
        {
          label: '可入库',
          detail: this.missingFieldCount === 0 && this.identityCount > 0 ? '可进入版本匹配' : '仍需修复',
          ready: this.missingFieldCount === 0 && this.identityCount > 0,
        },
      ]
    },
  },
  methods: {
    candidateScoreValue(candidate) {
      const score = Number(candidate?.score)
      return Number.isFinite(score) ? score : 0
    },
    candidateRowClass(candidate) {
      return {
        'candidate-row-primary': candidate === this.topCandidate,
        'candidate-row-review': this.candidateConfirmationRisk === '需人工复核',
      }
    },
    candidateDecisionLabel(candidate) {
      if (candidate === this.topCandidate) return '首选'
      if (this.candidateConfirmationRisk === '需人工复核') return '复核'
      return ''
    },
    fieldSourceRepairClass(row) {
      return {
        missing: !row.ready,
      }
    },
    fieldSourceCoverage(field) {
      return [
        {
          key: 'movie',
          label: '影片本体',
          ready: field.fields.some(fieldName => this.movieHasDiagnosticValue(fieldName)),
        },
        {
          key: 'chosen',
          label: '已选字段',
          ready: field.fields.some(fieldName => this.chosenFieldHasDiagnosticValue(fieldName)),
        },
        {
          key: 'detail',
          label: '详情来源',
          ready: field.fields.some(fieldName => this.detailHasDiagnosticValue(fieldName)),
        },
      ]
    },
    fieldHasDiagnosticValue(fieldName) {
      return this.movieHasDiagnosticValue(fieldName)
        || this.chosenFieldHasDiagnosticValue(fieldName)
        || this.detailHasDiagnosticValue(fieldName)
    },
    movieHasDiagnosticValue(fieldName) {
      const movie = this.sourceDiagnostics?.movie || {}
      return this.hasValue(movie[fieldName])
    },
    chosenFieldHasDiagnosticValue(fieldName) {
      return (this.sourceDiagnostics?.chosen_fields || []).some(field => field.field_name === fieldName && this.hasValue(field.field_value))
    },
    detailHasDiagnosticValue(fieldName) {
      return (this.sourceDiagnostics?.details || []).some(detail => this.hasValue(detail[fieldName]))
    },
    hasValue(value) {
      if (Array.isArray(value)) return value.length > 0
      return value !== undefined && value !== null && String(value).trim() !== ''
    },
  },
}
</script>

<style scoped src="./supplementSourceDiagnosticsDialog.css"></style>

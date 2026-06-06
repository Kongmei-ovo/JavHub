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
        <section class="diagnostics-section">
          <h3>选中字段</h3>
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
        <section class="diagnostics-section">
          <h3>匹配候选</h3>
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
            <div v-for="candidate in sourceDiagnostics.match_candidates" :key="candidate.candidate_content_id" class="diagnostics-row diagnostics-row-candidates">
              <span>{{ candidate.candidate_content_id }}</span>
              <span>{{ candidate.score }}</span>
              <span>{{ candidate.status }}</span>
              <span>
                <button class="btn btn-ghost btn-xs" type="button" :disabled="manualActionLoading" @click="$emit('match', candidate.candidate_content_id)">确认</button>
              </span>
            </div>
          </div>
          <div v-else class="empty-inline">暂无匹配候选</div>
        </section>
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
}
</script>

<style scoped src="./supplementSourceDiagnosticsDialog.css"></style>

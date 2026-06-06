<template>
  <section class="workspace-panel apple-surface">
    <div class="panel-header">
      <div>
        <h2>校对台</h2>
      </div>
      <div class="panel-actions">
        <button class="btn btn-ghost btn-sm" type="button" :disabled="reviewLoading" @click="$emit('load-items', reviewPage)">
          {{ reviewLoading ? '加载中...' : '刷新条目' }}
        </button>
        <button class="btn btn-primary btn-sm" type="button" :disabled="retryingItems" @click="$emit('retry-items')">
          {{ retryingItems ? '提交中...' : '重试当前筛选' }}
        </button>
      </div>
    </div>

    <div class="review-toolbar">
      <label class="field">
        <span>类型</span>
        <GlassSelect
          :model-value="reviewType"
          :options="translationTypeOptions"
          aria-label="校对类型"
          @update:model-value="$emit('update-review-type', $event)"
          @change="$emit('load-items', 1)"
        />
      </label>
      <label class="field">
        <span>状态</span>
        <GlassSelect
          :model-value="reviewStatus"
          :options="reviewStatusOptions"
          aria-label="校对状态"
          @update:model-value="$emit('update-review-status', $event)"
          @change="$emit('load-items', 1)"
        />
      </label>
      <label class="field search-field">
        <span>检索</span>
        <input
          :value="reviewQuery"
          class="input"
          placeholder="演员名、日文、中文、番号或标题"
          @input="$emit('update-review-query', $event.target.value)"
          @keyup.enter="$emit('load-items', 1)"
        />
      </label>
      <button class="btn btn-ghost review-search-btn" type="button" @click="$emit('load-items', 1)">搜索</button>
    </div>

    <div class="review-stats">
      <div><strong>{{ reviewTotal }}</strong><span>索引条目</span></div>
      <div><strong>{{ reviewStatsByStatus.untranslated || 0 }}</strong><span>未翻译</span></div>
      <div><strong>{{ reviewStatsByStatus.failed || 0 }}</strong><span>失败</span></div>
      <div><strong>{{ reviewUnreviewed }}</strong><span>待校对</span></div>
    </div>

    <div v-if="reviewMessage" class="message-line" :class="reviewMessageType">{{ reviewMessage }}</div>

    <div class="review-table">
      <div class="review-head">
        <span>原文</span>
        <span>当前译文</span>
        <span>状态</span>
        <span>来源</span>
        <span>操作</span>
      </div>
      <div v-if="reviewLoading && !reviewItems.length" class="empty-panel compact">加载中...</div>
      <div v-else-if="!reviewItems.length" class="empty-panel compact">暂无工作台条目</div>
      <div
        v-for="item in reviewItems"
        :key="`${item.item_type}:${item.item_id}`"
        v-memo="[item.item_type, item.item_id, item.edit_text, item.status, item.provider, item.updated_at, item.last_error]"
        class="review-row"
      >
        <div class="review-source">
          <strong>{{ item.source_text || '—' }}</strong>
          <small>{{ translationTypeLabels[item.item_type] || item.item_type }} · {{ item.item_id }}</small>
        </div>
        <textarea
          :value="item.edit_text"
          class="input review-edit"
          rows="2"
          @input="$emit('update-item-edit-text', { item, value: $event.target.value })"
        ></textarea>
        <span class="status-pill" :class="workbenchStatusClass(item.status)">{{ workbenchStatusLabel(item.status) }}</span>
        <div class="review-meta">
          <span>{{ providerLabel(item.provider) || '本地' }}</span>
          <small>{{ formatTime(item.updated_at) }}</small>
          <small v-if="item.last_error" class="error-text">{{ item.last_error }}</small>
        </div>
        <div class="review-actions">
          <button class="btn btn-primary btn-sm" type="button" @click="$emit('save-item', item)">保存</button>
          <button class="btn btn-ghost btn-sm" type="button" @click="$emit('mark-item', item)">标记已校对</button>
          <button class="btn btn-ghost btn-sm" type="button" @click="$emit('show-history', item)">历史</button>
          <button class="btn btn-ghost btn-sm danger" type="button" @click="$emit('reset-item', item)">重置</button>
        </div>
      </div>
    </div>

    <div class="review-pagination">
      <button class="btn btn-ghost btn-sm" type="button" :disabled="reviewPage <= 1" @click="$emit('load-items', reviewPage - 1)">上一页</button>
      <span>共 {{ reviewTotalCount }} 条 · 第 {{ reviewPage }} / {{ reviewTotalPages }} 页</span>
      <label class="page-size-field">
        <span>每页</span>
        <GlassSelect
          :model-value="reviewPageSize"
          :options="reviewPageSizeOptions"
          size="compact"
          aria-label="校对台每页条数"
          @update:model-value="$emit('update-review-page-size', $event)"
          @change="$emit('load-items', 1)"
        />
      </label>
      <button class="btn btn-ghost btn-sm" type="button" :disabled="reviewPage >= reviewTotalPages" @click="$emit('load-items', reviewPage + 1)">下一页</button>
    </div>

    <aside v-if="reviewHistoryItem" class="review-history-panel">
      <div class="recent-head">
        <strong>{{ reviewHistoryItem.source_text }} 的修改历史</strong>
        <button class="btn btn-ghost btn-sm" type="button" @click="$emit('close-history')">关闭</button>
      </div>
      <div v-if="reviewHistoryLoading" class="empty-panel compact">加载中...</div>
      <div v-else-if="!reviewHistory.length" class="empty-panel compact">暂无修改历史</div>
      <div v-for="history in reviewHistory" :key="history.id" class="history-row review-history-row">
        <div>
          <strong>{{ history.action }}</strong>
          <span>{{ history.old_text || '空' }} -> {{ history.new_text || '空' }}</span>
        </div>
        <button class="btn btn-ghost btn-sm" type="button" @click="$emit('restore-history', history)">恢复</button>
      </div>
    </aside>
  </section>
</template>

<script>
import GlassSelect from '../../components/GlassSelect.vue'
import { providerLabel } from '../../utils/translationProviders.js'
import {
  workbenchStatusClass,
  workbenchStatusLabel,
} from '../../utils/translationJobPresentation.js'

export default {
  name: 'TranslationReviewPanel',
  components: { GlassSelect },
  props: {
    reviewType: { type: String, required: true },
    reviewStatus: { type: String, required: true },
    reviewStatusOptions: { type: Array, required: true },
    reviewQuery: { type: String, default: '' },
    reviewPage: { type: Number, default: 1 },
    reviewPageSize: { type: Number, default: 30 },
    reviewPageSizeOptions: { type: Array, required: true },
    reviewTotal: { type: Number, default: 0 },
    reviewTotalCount: { type: Number, default: 0 },
    reviewTotalPages: { type: Number, default: 1 },
    reviewUnreviewed: { type: Number, default: 0 },
    reviewStatsByStatus: { type: Object, default: () => ({}) },
    reviewItems: { type: Array, default: () => [] },
    reviewLoading: { type: Boolean, default: false },
    retryingItems: { type: Boolean, default: false },
    reviewMessage: { type: String, default: '' },
    reviewMessageType: { type: String, default: 'info' },
    reviewHistoryItem: { type: Object, default: null },
    reviewHistory: { type: Array, default: () => [] },
    reviewHistoryLoading: { type: Boolean, default: false },
    translationTypeLabels: { type: Object, required: true },
    translationTypeOptions: { type: Array, required: true },
  },
  emits: [
    'load-items',
    'retry-items',
    'save-item',
    'mark-item',
    'show-history',
    'reset-item',
    'close-history',
    'restore-history',
    'update-review-type',
    'update-review-status',
    'update-review-query',
    'update-review-page-size',
    'update-item-edit-text',
  ],
  methods: {
    providerLabel,
    workbenchStatusLabel,
    workbenchStatusClass,
    formatTime(value) {
      if (!value) return '—'
      const date = new Date(value)
      if (Number.isNaN(date.getTime())) return String(value)
      return date.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
      })
    },
  },
}
</script>

<style scoped src="./translationPanelControls.css"></style>
<style scoped src="./translationReviewPanel.css"></style>

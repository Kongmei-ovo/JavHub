<template>
  <div class="duplicates-page page-shell page-shell--standard">
    <div class="page-header">
      <h1>去重管理</h1>
      <button @click="rescan" class="rescan-btn">重新扫描</button>
    </div>

    <div v-if="!loading && !error && duplicates.length > 0" class="duplicate-list">
      <div
        v-for="item in duplicates"
        :key="item.emby_item_id"
        class="duplicate-item"
      >
        <div class="item-cover">
          <img :src="item.jacket_thumb_url || '/placeholder.png'" :alt="item.content_id" loading="lazy" decoding="async" />
        </div>
        <div class="item-info">
          <div class="item-code">{{ item.content_id }}</div>
          <div class="item-title">{{ item.javinfo_title }}</div>
          <div v-if="item.duplicate_count" class="item-similarity">重复条目: {{ item.duplicate_count }}</div>
          <div v-else class="item-similarity">相似度: {{ (item.similarity * 100).toFixed(0) }}%</div>
          <div class="item-reason">{{ item.reason }}</div>
          <div class="duplicate-entries">
            <div
              v-for="duplicate in duplicateItems(item)"
              :key="duplicate.emby_item_id"
              class="duplicate-entry"
            >
              <div class="duplicate-entry-main">
                <div class="item-emby-name">Emby 名称: {{ duplicate.emby_name }}</div>
                <div v-if="duplicate.filename" class="item-filename">{{ duplicate.filename }}</div>
              </div>
              <div class="item-actions">
                <button @click="deleteItem(duplicate)" class="action-btn delete">删除</button>
                <button @click="ignoreItem(duplicate)" class="action-btn ignore">忽略</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <AppleSkeleton
      v-if="loading"
      class="loading"
      variant="list"
      :items="5"
      label="重复条目加载中"
    />
    <AppleErrorState
      v-else-if="error"
      class="error"
      title="重复扫描加载失败"
      :description="error"
      next-step="重新扫描会再次读取 Emby 条目；如果仍失败，请去运行日志查看接口错误。"
      retry-label="重新扫描"
      secondary-action-label="查看日志"
      @retry="rescan"
      @secondary-action="$router.push('/logs')"
    />
    <AppleEmptyState
      v-else-if="duplicates.length === 0"
      class="empty"
      title="暂无可疑重复"
      description="当前快照没有发现需要清理的重复条目。"
      next-step="可以重新扫描确认最新结果，或回到片库整理继续处理缺失和映射。"
      action-label="重新扫描"
      secondary-action-label="片库整理"
      density="compact"
      @action="rescan"
      @secondary-action="$router.push({ path: '/library-organize', query: { tab: 'duplicates' } })"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from '../utils/message.js'
import api from '../api'
import { requestConfirm } from '../utils/confirmDialog'
import AppleSkeleton from '../components/AppleSkeleton.vue'
import AppleEmptyState from '../components/AppleEmptyState.vue'
import AppleErrorState from '../components/AppleErrorState.vue'

const duplicates = ref([])
const loading = ref(false)
const error = ref('')

const fetchDuplicates = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await api.getDuplicates()
    duplicates.value = res.data.data || []
  } catch (e) {
    error.value = '加载失败: ' + e.message
  } finally {
    loading.value = false
  }
}

const rescan = async () => {
  await fetchDuplicates()
}

const duplicateItems = (item) => item.items?.length ? item.items : [item]

const removeDuplicateItem = (embyItemId) => {
  duplicates.value = duplicates.value
    .map(group => {
      const items = duplicateItems(group).filter(item => item.emby_item_id !== embyItemId)
      if (!group.items) return group.emby_item_id === embyItemId ? null : group
      if (items.length < 2) return null
      return {
        ...group,
        emby_item_id: items[0].emby_item_id,
        emby_name: items[0].emby_name,
        duplicate_count: items.length,
        items,
      }
    })
    .filter(Boolean)
}

const deleteItem = async (item) => {
  const confirmed = await requestConfirm({
    title: '删除 Emby 条目',
    message: '确定要删除 Emby 中的这个条目吗？',
    details: item.emby_name || item.content_id || '',
    confirmText: '删除',
    tone: 'danger'
  })
  if (!confirmed) return
  try {
    await api.deleteDuplicate(item.emby_item_id)
    removeDuplicateItem(item.emby_item_id)
  } catch (e) {
    ElMessage.error('删除失败: ' + e.message)
  }
}

const ignoreItem = async (item) => {
  try {
    await api.ignoreDuplicate(item.emby_item_id)
    removeDuplicateItem(item.emby_item_id)
  } catch (e) {
    ElMessage.error('忽略失败: ' + e.message)
  }
}

onMounted(fetchDuplicates)
</script>

<style scoped>
.duplicates-page {
  color: var(--text-primary);
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  gap: 12px;
  flex-wrap: wrap;
}
.page-header h1 {
  margin: 0;
  font-size: var(--type-page-title);
  line-height: 1.2;
  letter-spacing: 0;
}
.rescan-btn {
  min-height: 44px;
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--material-glass-control);
  color: var(--text-primary);
  border: 1px solid var(--glass-control-border);
  padding: 0 18px;
  border-radius: 999px;
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  cursor: pointer;
  font-weight: 700;
  transition: transform var(--motion-standard);
}
.rescan-btn:hover {
  transform: translateY(-1px);
  background:
    var(--surface-specular-edge-strong),
    var(--surface-noise),
    var(--material-glass-control-hover);
  border-color: var(--glass-control-border-hover);
  box-shadow: var(--glass-control-shadow-hover);
}
.rescan-btn:focus-visible {
  outline: none;
  transform: translateY(-1px);
  background:
    var(--surface-specular-edge-strong),
    var(--surface-noise),
    var(--material-glass-control-hover);
  border-color: var(--glass-control-border-hover);
  box-shadow: var(--glass-control-shadow-hover), var(--focus-ring);
}
.duplicate-item {
  display: flex;
  gap: 16px;
  padding: 16px;
  background: var(--card);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  margin-bottom: 12px;
  min-width: 0;
}
.item-cover img {
  width: 100px;
  aspect-ratio: 3 / 4;
  object-fit: cover;
  border-radius: 4px;
}
.item-info {
  flex: 1;
  min-width: 0;
}
.item-code {
  font-weight: bold;
  font-size: 16px;
}
.item-title {
  color: var(--text-primary);
  margin: 4px 0;
  overflow-wrap: anywhere;
}
.item-emby-name {
  color: var(--text-secondary);
  font-size: 14px;
  overflow-wrap: anywhere;
}
.item-similarity {
  color: var(--text-primary);
  font-size: 14px;
}
.item-reason {
  color: var(--text-muted);
  font-size: 12px;
  margin-top: 4px;
  overflow-wrap: anywhere;
}
.duplicate-entries {
  display: grid;
  gap: 8px;
  margin-top: 12px;
}
.duplicate-entry {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  padding: 10px;
  border: 1px solid var(--hairline);
  border-radius: var(--radius-sm);
  background: var(--card-2);
  box-shadow: none;
  transition: transform var(--motion-standard);
}
.duplicate-entry:focus-within {
  transform: translateY(-1px);
  background: var(--card-hover);
  border-color: var(--hairline-strong);
  box-shadow: var(--focus-ring);
}
.duplicate-entry-main {
  min-width: 0;
}
.item-filename {
  color: var(--text-muted);
  font-size: 12px;
  overflow-wrap: anywhere;
}
.item-actions {
  display: flex;
  flex-direction: row;
  gap: 8px;
}
.action-btn {
  min-width: 72px;
  min-height: 44px;
  padding: 0 16px;
  border: 1px solid var(--glass-control-border);
  border-radius: 999px;
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--material-glass-control);
  color: var(--text-primary);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  cursor: pointer;
  font-weight: 700;
  transition: transform var(--motion-standard);
}
.action-btn:hover {
  transform: translateY(-1px);
  background:
    var(--surface-specular-edge-strong),
    var(--surface-noise),
    var(--material-glass-control-hover);
  border-color: var(--glass-control-border-hover);
  box-shadow: var(--glass-control-shadow-hover);
}
.action-btn:focus-visible {
  outline: none;
  transform: translateY(-1px);
  background:
    var(--surface-specular-edge-strong),
    var(--surface-noise),
    var(--material-glass-control-hover);
  border-color: var(--glass-control-border-hover);
  box-shadow: var(--glass-control-shadow-hover), var(--focus-ring);
}
.action-btn.delete {
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--badge-error-bg);
  border-color: var(--badge-error-border);
  color: var(--badge-error-text);
}
.action-btn.delete:hover {
  background:
    var(--surface-specular-edge-strong),
    var(--surface-noise),
    var(--badge-error-bg);
  border-color: var(--badge-error-border);
}
.action-btn.delete:focus-visible {
  outline: none;
  background:
    var(--surface-specular-edge-strong),
    var(--surface-noise),
    var(--badge-error-bg);
  border-color: var(--badge-error-border);
  box-shadow: var(--glass-control-shadow-hover), 0 0 0 3px color-mix(in srgb, var(--badge-error-text) 18%, transparent);
  transform: translateY(-1px);
}
.action-btn.ignore {
  background:
    var(--surface-specular-edge),
    var(--surface-noise),
    var(--material-glass-control);
  border: 1px solid var(--glass-control-border);
  color: var(--text-secondary);
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}
.loading, .error, .empty {
  text-align: center;
  padding: 40px;
  border: 1px solid var(--hairline);
  border-radius: var(--radius-lg);
  background: var(--card);
  box-shadow: var(--shadow-card);
}
.error {
  color: var(--badge-error-text);
}

@media (max-width: 768px) {
  .duplicate-item {
    display: grid;
    grid-template-columns: 86px minmax(0, 1fr);
    gap: 12px;
  }

  .item-cover img {
    width: 86px;
  }

  .item-actions {
    flex-direction: row;
  }

  .duplicate-entry {
    grid-template-columns: minmax(0, 1fr);
  }

  .action-btn {
    flex: 1;
  }
}
</style>

<template>
  <div class="duplicates-page page-shell page-shell--standard">
    <div class="page-header">
      <h1>去重管理</h1>
      <button @click="rescan" class="rescan-btn">重新扫描</button>
    </div>

    <div class="duplicate-list">
      <div
        v-for="item in duplicates"
        :key="item.emby_item_id"
        class="duplicate-item"
      >
        <div class="item-cover">
          <img :src="item.jacket_thumb_url || '/placeholder.png'" :alt="item.content_id" />
        </div>
        <div class="item-info">
          <div class="item-code">{{ item.content_id }}</div>
          <div class="item-title">{{ item.javinfo_title }}</div>
          <div class="item-emby-name">Emby 名称: {{ item.emby_name }}</div>
          <div class="item-similarity">相似度: {{ (item.similarity * 100).toFixed(0) }}%</div>
          <div class="item-reason">{{ item.reason }}</div>
        </div>
        <div class="item-actions">
          <button @click="deleteItem(item)" class="action-btn delete">删除</button>
          <button @click="ignoreItem(item)" class="action-btn ignore">忽略</button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-if="error" class="error">{{ error }}</div>
    <div v-if="!loading && duplicates.length === 0" class="empty">暂无可疑重复</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from '../utils/message.js'
import api from '../api'
import { requestConfirm } from '../utils/confirmDialog'

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
    duplicates.value = duplicates.value.filter(d => d.emby_item_id !== item.emby_item_id)
  } catch (e) {
    ElMessage.error('删除失败: ' + e.message)
  }
}

const ignoreItem = async (item) => {
  try {
    await api.ignoreDuplicate(item.emby_item_id)
    duplicates.value = duplicates.value.filter(d => d.emby_item_id !== item.emby_item_id)
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
  background: var(--accent);
  color: var(--text-on-accent);
  border: 0;
  padding: 0 18px;
  border-radius: 999px;
  cursor: pointer;
  font-weight: 700;
}
.duplicate-item {
  display: flex;
  gap: 16px;
  padding: 16px;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
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
.item-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.action-btn {
  min-width: 72px;
  min-height: 44px;
  padding: 0 16px;
  border: none;
  border-radius: 999px;
  cursor: pointer;
  font-weight: 700;
}
.action-btn.delete {
  background: #ff4d4f;
  color: #fff;
}
.action-btn.ignore {
  background: var(--white-06);
  color: var(--text-secondary);
}
.loading, .error, .empty {
  text-align: center;
  padding: 40px;
}
.error {
  color: #ff4d4f;
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
    grid-column: 1 / -1;
    flex-direction: row;
  }

  .action-btn {
    flex: 1;
  }
}
</style>

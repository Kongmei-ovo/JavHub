<template>
  <div class="duplicates-page">
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
          <img :src="item.jacket_thumb_url || '/placeholder.png'" />
        </div>
        <div class="item-info">
          <div class="item-code">{{ item.content_id }}</div>
          <div class="item-title">{{ item.javinfo_title }}</div>
          <div class="item-emby-name">Emby名称: {{ item.emby_name }}</div>
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
import axios from 'axios'

const duplicates = ref([])
const loading = ref(false)
const error = ref('')

const fetchDuplicates = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await axios.get('/api/duplicates')
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
  if (!confirm('确定要删除 Emby 中的这个条目吗？')) return
  try {
    await axios.post(`/api/duplicates/${item.emby_item_id}/delete`)
    duplicates.value = duplicates.value.filter(d => d.emby_item_id !== item.emby_item_id)
  } catch (e) {
    alert('删除失败: ' + e.message)
  }
}

const ignoreItem = async (item) => {
  try {
    await axios.post(`/api/duplicates/${item.emby_item_id}/ignore`)
    duplicates.value = duplicates.value.filter(d => d.emby_item_id !== item.emby_item_id)
  } catch (e) {
    alert('忽略失败: ' + e.message)
  }
}

onMounted(fetchDuplicates)
</script>

<style scoped>
.duplicates-page {
  padding: 16px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.rescan-btn {
  background: #1890ff;
  color: #fff;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
}
.duplicate-item {
  display: flex;
  gap: 16px;
  padding: 16px;
  background: #fff;
  border-radius: 8px;
  margin-bottom: 12px;
}
.item-cover img {
  width: 100px;
  border-radius: 4px;
}
.item-info {
  flex: 1;
}
.item-code {
  font-weight: bold;
  font-size: 16px;
}
.item-title {
  color: #333;
  margin: 4px 0;
}
.item-emby-name {
  color: #666;
  font-size: 14px;
}
.item-similarity {
  color: #1890ff;
  font-size: 14px;
}
.item-reason {
  color: #999;
  font-size: 12px;
  margin-top: 4px;
}
.item-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.action-btn {
  padding: 8px 16px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
.action-btn.delete {
  background: #ff4d4f;
  color: #fff;
}
.action-btn.ignore {
  background: #f5f5f5;
  color: #666;
}
.loading, .error, .empty {
  text-align: center;
  padding: 40px;
}
.error {
  color: #ff4d4f;
}
</style>

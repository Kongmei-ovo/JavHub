<template>
  <div class="missing-page">
    <div class="page-header">
      <h1>缺失演员看板</h1>
      <button @click="refreshCache" class="refresh-btn">刷新缓存</button>
    </div>

    <div class="actress-list">
      <div
        v-for="item in actresses"
        :key="item.actress_id"
        class="actress-item"
        @click="goToDetail(item.actress_id)"
      >
        <div class="actress-info">
          <div class="actress-name">{{ item.actress_name }}</div>
          <div class="actress-count">缺失 {{ item.missing_count }}/{{ item.total_in_javinfo }} 部</div>
        </div>
        <div class="actress-action">查看详情 →</div>
      </div>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-if="error" class="error">{{ error }}</div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

const router = useRouter()
const actresses = ref([])
const loading = ref(false)
const error = ref('')

const fetchMissing = async () => {
  loading.value = true
  error.value = ''
  try {
    const res = await axios.get('/api/missing/actresses')
    actresses.value = res.data.data || []
  } catch (e) {
    error.value = '加载失败: ' + e.message
  } finally {
    loading.value = false
  }
}

const refreshCache = async () => {
  await axios.post('/api/missing/actresses/refresh')
  await fetchMissing()
}

const goToDetail = (actressId) => {
  router.push(`/missing/${actressId}`)
}

onMounted(fetchMissing)
</script>

<style scoped>
.missing-page {
  padding: 16px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.refresh-btn {
  background: #1890ff;
  color: #fff;
  border: none;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
}
.actress-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  background: #fff;
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: pointer;
}
.actress-item:hover {
  background: #f5f5f5;
}
.actress-name {
  font-weight: bold;
  margin-bottom: 4px;
}
.actress-count {
  color: #666;
  font-size: 14px;
}
.actress-action {
  color: #1890ff;
}
.loading, .error {
  text-align: center;
  padding: 20px;
}
.error {
  color: #ff4d4f;
}
</style>

<template>
  <div class="normalize-page">
    <div class="page-header">
      <h1>演员合并</h1>
      <button @click="showAddDialog = true" class="btn-primary">添加映射</button>
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <table v-else class="alias-table">
      <thead>
        <tr>
          <th>别名ID</th>
          <th>别名Name</th>
          <th>→</th>
          <th>规范ID</th>
          <th>规范Name</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="alias in aliasesWithNames" :key="alias.id">
          <td>{{ alias.alias_id }}</td>
          <td>{{ alias.alias_name }}</td>
          <td>→</td>
          <td>{{ alias.canonical_id }}</td>
          <td>{{ alias.canonical_name }}</td>
          <td>
            <button @click="removeAlias(alias.id)" class="btn-danger">删除</button>
          </td>
        </tr>
      </tbody>
    </table>

    <div v-if="!loading && aliases.length === 0" class="empty">
      暂无归一化映射
    </div>

    <!-- 添加映射弹窗 -->
    <div v-if="showAddDialog" class="dialog-overlay" @click.self="showAddDialog = false">
      <div class="dialog">
        <h3>添加演员归一化映射</h3>
        <div class="form-group">
          <label>别名演员</label>
          <select v-model="newAlias.alias_id">
            <option v-for="a in actors" :key="a.actress_id" :value="a.actress_id">
              {{ a.actress_name }}
            </option>
          </select>
        </div>
        <div class="form-group">
          <label>规范演员</label>
          <select v-model="newAlias.canonical_id">
            <option v-for="a in actors" :key="a.actress_id" :value="a.actress_id">
              {{ a.actress_name }}
            </option>
          </select>
        </div>
        <div class="dialog-actions">
          <button @click="showAddDialog = false" class="btn-secondary">取消</button>
          <button @click="addAlias" class="btn-primary">确认</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import axios from 'axios'

const aliases = ref([])
const actors = ref([])
const loading = ref(false)
const showAddDialog = ref(false)
const newAlias = ref({ alias_id: null, canonical_id: null })

const aliasesWithNames = computed(() => {
  return aliases.value.map(alias => ({
    ...alias,
    alias_name: getActorName(alias.alias_id),
    canonical_name: getActorName(alias.canonical_id)
  }))
})

const fetchAliases = async () => {
  loading.value = true
  const [aliasRes, actorRes] = await Promise.all([
    axios.get('/api/inventory/aliases'),
    axios.get('/api/inventory/actors'),
  ])
  aliases.value = aliasRes.data.data || []
  actors.value = actorRes.data.data || []
  loading.value = false
}

const getActorName = (actressId) => {
  if (!actressId) return ''
  const actor = actors.value.find(a => a.actress_id === actressId)
  return actor ? (actor.display_name || actor.actress_name) : actressId
}

const addAlias = async () => {
  if (!newAlias.value.alias_id || !newAlias.value.canonical_id) return
  await axios.post('/api/inventory/aliases', newAlias.value)
  showAddDialog.value = false
  newAlias.value = { alias_id: null, canonical_id: null }
  await fetchAliases()
}

const removeAlias = async (id) => {
  await axios.delete(`/api/inventory/aliases/${id}`)
  await fetchAliases()
}

onMounted(fetchAliases)
</script>

<style scoped>
.normalize-page { padding: 16px; }
.page-header {
  display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;
}
.btn-primary {
  background: #1890ff; color: #fff; border: none;
  padding: 8px 16px; border-radius: 4px; cursor: pointer;
}
.btn-secondary {
  background: #fff; color: #1890ff; border: 1px solid #1890ff;
  padding: 8px 16px; border-radius: 4px; cursor: pointer;
}
.btn-danger {
  background: #ff4d4f; color: #fff; border: none;
  padding: 4px 8px; border-radius: 4px; cursor: pointer;
}
.alias-table {
  width: 100%; border-collapse: collapse;
}
.alias-table th, .alias-table td {
  padding: 12px; text-align: center; border-bottom: 1px solid #eee;
}
.loading, .empty { text-align: center; padding: 40px; }
.dialog-overlay {
  position: fixed; top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center;
}
.dialog {
  background: #fff; padding: 24px; border-radius: 8px; width: 400px;
}
.form-group { margin-bottom: 12px; }
.form-group label { display: block; margin-bottom: 4px; }
.form-group select { width: 100%; padding: 8px; }
.dialog-actions { display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px; }
</style>

<template>
  <div class="actress-avatar" :style="{ width: size + 'px', height: size + 'px' }">
    <img v-if="avatarUrl && !errored" :src="avatarUrl" :alt="name" @error="errored = true" />
    <div v-else class="avatar-placeholder">{{ initials }}</div>
    <div v-if="badge !== null && badge !== undefined && badge > 0" class="avatar-badge">{{ badge }}</div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  name: { type: String, default: '' },
  avatarUrl: { type: String, default: '' },
  size: { type: Number, default: 60 },
  badge: { type: Number, default: null }
})

const errored = ref(false)

const initials = computed(() => {
  if (!props.name) return '?'
  return props.name.slice(0, 1).toUpperCase()
})
</script>

<style scoped>
.actress-avatar {
  position: relative;
  border-radius: 50%;
  overflow: hidden;
  flex-shrink: 0;
}
.actress-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.avatar-placeholder {
  width: 100%;
  height: 100%;
  background: #ddd;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: #999;
}
.avatar-badge {
  position: absolute;
  bottom: -2px;
  right: -2px;
  background: #ff4d4f;
  color: #fff;
  border-radius: 10px;
  padding: 2px 6px;
  font-size: 11px;
  min-width: 20px;
  text-align: center;
}
</style>

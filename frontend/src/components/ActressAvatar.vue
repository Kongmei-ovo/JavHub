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
  box-shadow: var(--glass-control-shadow);
}
.actress-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.avatar-placeholder {
  width: 100%;
  height: 100%;
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  color: var(--text-muted);
  border: 1px solid var(--glass-control-border);
  box-shadow: var(--glass-inner-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}
.avatar-badge {
  position: absolute;
  bottom: -2px;
  right: -2px;
  background: var(--surface-specular-edge), var(--surface-noise), var(--badge-error-bg);
  color: var(--badge-error-text);
  border: 1px solid var(--badge-error-border);
  border-radius: 10px;
  padding: 2px 6px;
  font-size: 11px;
  min-width: 20px;
  text-align: center;
  box-shadow: var(--glass-control-shadow);
}
</style>

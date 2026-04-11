<template>
  <div class="stat-card" @click="handleClick">
    <div class="stat-icon">{{ icon }}</div>
    <div class="stat-content">
      <div class="stat-value">{{ value }}</div>
      <div class="stat-label">{{ label }}</div>
    </div>
    <div class="stat-arrow">↗</div>
  </div>
</template>

<script setup>
defineProps({
  icon: { type: String, required: true },
  value: { type: [String, Number], required: true },
  label: { type: String, required: true },
  link: { type: String, default: null }
})

const handleClick = () => {
  if (defineProps.link) {
    // navigate using router
  }
}
</script>

<style scoped>
.stat-card {
  display: flex;
  align-items: center;
  background: #fff;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: box-shadow 0.2s;
}
.stat-card:hover {
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}
.stat-icon {
  font-size: 24px;
  margin-right: 12px;
}
.stat-content {
  flex: 1;
}
.stat-value {
  font-size: 24px;
  font-weight: bold;
}
.stat-label {
  color: #666;
  font-size: 14px;
}
.stat-arrow {
  color: #999;
}
</style>

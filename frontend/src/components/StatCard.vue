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
const props = defineProps({
  icon: { type: String, required: true },
  value: { type: [String, Number], required: true },
  label: { type: String, required: true },
  link: { type: String, default: null }
})

const handleClick = () => {
  if (props.link) {
    // navigate using router
  }
}
</script>

<style scoped>
.stat-card {
  display: flex;
  align-items: center;
  background: var(--card);
  border: 1px solid var(--hairline);
  border-radius: var(--radius-card);
  padding: 24px 32px;
  cursor: pointer;
  box-shadow: var(--shadow-card);
  transition: transform var(--motion-standard);
}
.stat-card:hover {
  background: var(--card-hover);
  transform: translateY(-2px);
  border-color: var(--hairline-strong);
  box-shadow: var(--shadow-card);
}
.stat-icon {
  font-size: var(--type-display-mobile);
  margin-right: 20px;
}
.stat-content {
  flex: 1;
}
.stat-value {
  font-size: var(--type-entity-title);
  font-weight: 700;
  color: var(--text-primary);
  font-family: var(--font-mono);
  letter-spacing: 0;
  margin-bottom: 4px;
}
.stat-label {
  color: var(--text-muted);
  font-size: var(--type-caption);
  font-weight: 600;
  letter-spacing: 0;
}
.stat-arrow {
  color: var(--text-muted);
  font-size: 20px;
  transition: transform var(--motion-standard);
}
.stat-card:hover .stat-arrow {
  color: var(--text-primary);
  transform: translate(4px, -4px);
}
</style>

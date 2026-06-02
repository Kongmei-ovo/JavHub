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
  background: var(--material-glass-control);
  border: 1px solid var(--glass-control-border);
  border-radius: var(--radius-card);
  padding: 24px 32px;
  cursor: pointer;
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  transition: background var(--motion-fast), border-color var(--motion-fast), box-shadow var(--motion-fast), transform var(--motion-fast);
}
.stat-card:hover {
  background: var(--material-glass-control-hover);
  transform: translateY(-3px);
  border-color: var(--glass-control-border-hover);
  box-shadow: var(--glass-control-shadow-hover);
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
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.12em;
}
.stat-arrow {
  color: var(--text-muted);
  font-size: 20px;
  transition: color var(--motion-fast), transform var(--motion-fast);
}
.stat-card:hover .stat-arrow {
  color: var(--text-primary);
  transform: translate(4px, -4px);
}
</style>

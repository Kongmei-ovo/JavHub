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
  background: var(--bg-card);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: var(--stroke-pro) solid var(--border);
  border-radius: var(--radius-pro);
  padding: 24px 32px;
  cursor: pointer;
  transition: var(--transition-pro);
  box-shadow: var(--shadow-card);
}
.stat-card:hover {
  transform: translateY(-4px);
  border-color: var(--accent);
  box-shadow: var(--shadow-hover);
}
.stat-icon {
  font-size: 32px;
  margin-right: 20px;
  filter: drop-shadow(0 0 10px var(--accent-glow));
}
.stat-content {
  flex: 1;
}
.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary);
  font-family: var(--font-mono);
  letter-spacing: var(--ls-pro);
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
  transition: var(--transition-pro);
}
.stat-card:hover .stat-arrow {
  color: var(--accent);
  transform: translate(4px, -4px);
}
</style>

<template>
  <div v-if="hasVariants" class="variant-group-disclosure">
    <button
      class="variant-group-disclosure__toggle"
      type="button"
      @click.stop="$emit('toggle', itemKey)"
    >
      <span v-if="expanded">收起版本</span>
      <span v-else>另 {{ hiddenCount }} 个版本</span>
    </button>
    <div v-if="expanded" class="variant-group-disclosure__list">
      <button
        v-for="variant in visibleItems"
        :key="variantKey(variant)"
        class="variant-group-disclosure__row"
        type="button"
        @click.stop="$emit('openVariant', variant)"
      >
        <span class="variant-group-disclosure__code">{{ displayCode(variant) }}</span>
        <span class="variant-group-disclosure__labels">
          <span
            v-for="label in variantLabels(variant)"
            :key="label.key || label.label || label.short_label"
          >{{ label.short_label || label.label }}</span>
        </span>
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  variantGroupCount: { type: Number, default: 0 },
  variantGroupItems: { type: Array, default: () => [] },
  expanded: { type: Boolean, default: false },
  itemKey: { type: String, default: '' },
})

defineEmits(['toggle', 'openVariant'])

const visibleItems = computed(() => Array.isArray(props.variantGroupItems) ? props.variantGroupItems : [])
const hiddenCount = computed(() => Math.max(0, Number(props.variantGroupCount || 0) - 1))
const hasVariants = computed(() => hiddenCount.value > 0 || visibleItems.value.length > 0)

function displayCode(variant) {
  return variant?.display_code || variant?.dvd_id || variant?.content_id || ''
}

function variantLabels(variant) {
  const labels = Array.isArray(variant?.variant_labels) ? variant.variant_labels : []
  return labels.slice(0, 2)
}

function variantKey(variant) {
  return [
    variant?.content_id || '',
    variant?.dvd_id || '',
    variant?.service_code || '',
    displayCode(variant),
  ].join('|')
}
</script>

<style scoped>
.variant-group-disclosure {
  min-width: 0;
}

.variant-group-disclosure__toggle {
  width: 100%;
  margin-top: 8px;
  min-height: 32px;
  border: 1px solid var(--glass-control-border);
  border-radius: var(--radius-control);
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  color: var(--text-secondary);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  transition: transform var(--motion-standard), opacity var(--motion-fast);
}

.variant-group-disclosure__toggle:hover {
  border-color: var(--glass-control-border-hover);
  color: var(--text-primary);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  box-shadow: var(--glass-control-shadow-hover);
  transform: translateY(-1px);
}

.variant-group-disclosure__toggle:active {
  transform: translateY(0) scale(0.99);
}

.variant-group-disclosure__toggle:focus-visible,
.variant-group-disclosure__row:focus-visible {
  outline: none;
  box-shadow: var(--glass-control-shadow), var(--focus-ring-wide-strong);
}

.variant-group-disclosure__list {
  display: grid;
  gap: 6px;
  margin-top: 8px;
}

.variant-group-disclosure__row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  min-height: 34px;
  padding: 6px 8px;
  border: 1px solid var(--glass-control-border);
  border-radius: 8px;
  background: var(--surface-specular-edge), var(--surface-noise), var(--material-glass-control);
  color: var(--text-secondary);
  cursor: pointer;
  text-align: left;
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  transition: transform var(--motion-standard), opacity var(--motion-fast);
}

.variant-group-disclosure__row:hover {
  border-color: var(--glass-control-border-hover);
  background: var(--surface-specular-edge-strong), var(--surface-noise), var(--material-glass-control-hover);
  color: var(--text-primary);
  box-shadow: var(--glass-control-shadow-hover);
  transform: translateY(-1px);
}

.variant-group-disclosure__row:active {
  transform: translateY(0) scale(0.99);
}

.variant-group-disclosure__code {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-family: var(--font-mono);
  font-size: 12px;
  font-weight: 650;
}

.variant-group-disclosure__labels {
  display: inline-flex;
  gap: 4px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.variant-group-disclosure__labels span {
  padding: 1px 5px;
  border-radius: 999px;
  background: var(--surface-specular-edge), var(--surface-noise), var(--badge-info-bg);
  border: 1px solid var(--badge-info-border);
  color: var(--badge-info-text);
  font-size: 10px;
  font-weight: 650;
  box-shadow: var(--glass-control-shadow);
  backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
  -webkit-backdrop-filter: blur(var(--glass-blur-control)) saturate(var(--glass-saturate-control));
}

@media (max-width: 768px) {
  .variant-group-disclosure__toggle,
  .variant-group-disclosure__row {
    min-height: 40px;
  }
}
</style>

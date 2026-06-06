<template>
  <button
    :class="['apple-switch', { 'apple-switch--on': modelValue }]"
    type="button"
    role="switch"
    :aria-checked="modelValue ? 'true' : 'false'"
    :aria-label="label || undefined"
    :disabled="disabled"
    @click="toggle"
  >
    <span class="apple-switch__track" aria-hidden="true">
      <span class="apple-switch__thumb"></span>
    </span>
  </button>
</template>

<script setup>
import '../assets/formControls.css'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  label: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue', 'change'])

function toggle() {
  if (props.disabled) return
  const nextValue = !props.modelValue
  emit('update:modelValue', nextValue)
  emit('change', nextValue)
}
</script>

<template>
  <button
    :class="[
      'apple-checkbox',
      {
        'apple-checkbox--checked': modelValue && !indeterminate,
        'apple-checkbox--indeterminate': indeterminate,
      },
    ]"
    type="button"
    role="checkbox"
    :aria-checked="ariaChecked"
    :aria-label="label || undefined"
    :disabled="disabled"
    @click="toggle"
  >
    <span class="apple-checkbox__box" aria-hidden="true">
      <svg class="apple-checkbox__glyph" viewBox="0 0 18 18">
        <path
          v-if="indeterminate"
          class="apple-checkbox__mixed-line"
          d="M5 9H13"
          pathLength="12"
        />
        <path
          v-else
          class="apple-checkbox__mark"
          d="M4.5 9.2L7.7 12.2L13.7 5.8"
          pathLength="18"
        />
      </svg>
    </span>
  </button>
</template>

<script setup>
import { computed } from 'vue'
import '../assets/formControls.css'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  indeterminate: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  label: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue', 'change'])

const ariaChecked = computed(() => props.indeterminate ? 'mixed' : props.modelValue ? 'true' : 'false')

function toggle() {
  if (props.disabled) return
  const nextValue = props.indeterminate ? true : !props.modelValue
  emit('update:modelValue', nextValue)
  emit('change', nextValue)
}
</script>

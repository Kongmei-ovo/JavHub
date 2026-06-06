<template>
  <label
    class="apple-text-field"
    :class="[
      `apple-text-field--${size}`,
      `apple-text-field--${tone}`,
      { 'apple-text-field--with-icon': prefixIcon, 'apple-text-field--clearable': showClearButton },
    ]"
  >
    <span v-if="prefixIcon" class="apple-text-field__icon" aria-hidden="true">{{ prefixIcon }}</span>
    <input
      class="apple-text-field__input"
      :value="modelValue"
      :placeholder="placeholder"
      type="text"
      @input="handleInput"
    />
    <button
      v-if="showClearButton"
      class="apple-text-field__clear"
      type="button"
      aria-label="清除输入"
      @click="clearInput"
    >
      <span aria-hidden="true">&times;</span>
    </button>
  </label>
</template>

<script setup>
import { computed } from 'vue'
import '../assets/textField.css'

/*
README:
<AppleTextField
  v-model="keyword"
  placeholder="搜索番号、标题或演员"
  prefix-icon="⌕"
  clearable
  tone="search"
/>
*/

const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  placeholder: { type: String, default: '' },
  clearable: { type: Boolean, default: false },
  prefixIcon: { type: String, default: '' },
  size: {
    type: String,
    default: 'regular',
    validator: value => ['regular', 'compact'].includes(value),
  },
  tone: {
    type: String,
    default: 'default',
    validator: value => ['default', 'search'].includes(value),
  },
})

const emit = defineEmits(['update:modelValue', 'clear'])

const showClearButton = computed(() => props.clearable && String(props.modelValue ?? '').length > 0)
const modelValue = computed(() => props.modelValue)
const placeholder = computed(() => props.placeholder)
const prefixIcon = computed(() => props.prefixIcon)
const size = computed(() => props.size)
const tone = computed(() => props.tone)

function handleInput(event) {
  emit('update:modelValue', event.target.value)
}

function clearInput() {
  emit('update:modelValue', '')
  emit('clear')
}
</script>

<template>
  <div
    ref="rootRef"
    class="glass-select"
    :class="[
      `glass-select--${size}`,
      `glass-select--${placement}`,
      { 'is-open': open, 'is-empty': selectedIndex === -1, 'glass-select--up': dropUp },
    ]"
    :style="{ '--glass-select-menu-max-height': menuMaxHeight ? `${menuMaxHeight}px` : undefined }"
  >
    <button
      ref="buttonRef"
      class="glass-select__button"
      type="button"
      :aria-label="ariaLabel || placeholder"
      :aria-expanded="open"
      aria-haspopup="listbox"
      @click="toggle"
      @keydown="handleButtonKeydown"
    >
      <span v-if="selectedOption?.color" class="glass-select__dot" :style="{ background: selectedOption.color }"></span>
      <span class="glass-select__copy">
        <span class="glass-select__label">{{ selectedOption?.label || placeholder }}</span>
        <span v-if="selectedOption?.hint" class="glass-select__hint">{{ selectedOption.hint }}</span>
      </span>
      <svg class="glass-select__chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polyline points="6 9 12 15 18 9"></polyline>
      </svg>
    </button>

    <transition name="glass-select-menu">
      <div v-if="open" ref="menuRef" class="glass-select__menu" role="listbox" :aria-label="ariaLabel || placeholder">
        <button
          v-for="(option, index) in normalizedOptions"
          :key="option.key"
          class="glass-select__option"
          type="button"
          role="option"
          :aria-selected="index === selectedIndex"
          :class="{ 'is-selected': index === selectedIndex, 'is-active': index === activeIndex }"
          @mouseenter="activeIndex = index"
          @click="selectOption(option)"
        >
          <span v-if="option.color" class="glass-select__dot" :style="{ background: option.color }"></span>
          <span class="glass-select__option-copy">
            <span>{{ option.label }}</span>
            <small v-if="option.hint">{{ option.hint }}</small>
          </span>
          <svg v-if="index === selectedIndex" class="glass-select__check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
        </button>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({
  modelValue: { default: '' },
  options: { type: Array, default: () => [] },
  placeholder: { type: String, default: '请选择' },
  size: {
    type: String,
    default: 'regular',
    validator: value => ['compact', 'regular'].includes(value),
  },
  placement: {
    type: String,
    default: 'left',
    validator: value => ['left', 'right'].includes(value),
  },
  ariaLabel: { type: String, default: '' },
})

const emit = defineEmits(['update:modelValue', 'change'])

const open = ref(false)
const activeIndex = ref(-1)
const dropUp = ref(false)
const menuMaxHeight = ref(0)
const rootRef = ref(null)
const buttonRef = ref(null)
const menuRef = ref(null)

const normalizedOptions = computed(() => props.options.map((option, index) => {
  const normalized = typeof option === 'object' && option !== null ? option : { value: option, label: String(option) }
  return {
    ...normalized,
    label: normalized.label ?? String(normalized.value ?? ''),
    key: `${typeof normalized.value}:${String(normalized.value)}:${index}`,
  }
}))

const selectedIndex = computed(() => normalizedOptions.value.findIndex(option => option.value === props.modelValue))
const selectedOption = computed(() => normalizedOptions.value[selectedIndex.value])

function openMenu() {
  if (open.value) return
  open.value = true
  dropUp.value = false
  menuMaxHeight.value = 0
  activeIndex.value = selectedIndex.value >= 0 ? selectedIndex.value : 0
  document.addEventListener('mousedown', handleOutside)
  document.addEventListener('focusin', handleOutside)
  nextTick(updateMenuPlacement)
}

function closeMenu() {
  if (!open.value) return
  open.value = false
  dropUp.value = false
  menuMaxHeight.value = 0
  document.removeEventListener('mousedown', handleOutside)
  document.removeEventListener('focusin', handleOutside)
}

function toggle() {
  if (open.value) closeMenu()
  else openMenu()
}

function handleOutside(event) {
  if (!rootRef.value?.contains(event.target)) closeMenu()
}

function selectOption(option) {
  emit('update:modelValue', option.value)
  emit('change', option.value)
  closeMenu()
  nextTick(() => buttonRef.value?.focus())
}

function updateMenuPlacement() {
  if (!rootRef.value || !menuRef.value) return
  const rootRect = rootRef.value.getBoundingClientRect()
  const menuHeight = menuRef.value.getBoundingClientRect().height || 240
  const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0
  const bottomLimit = findBottomOverlayLimit(rootRect, viewportHeight)
  const margin = 14
  const spaceBelow = bottomLimit - rootRect.bottom - margin
  const spaceAbove = rootRect.top - margin

  dropUp.value = spaceBelow < menuHeight && spaceAbove > spaceBelow
  const available = dropUp.value ? spaceAbove : spaceBelow
  menuMaxHeight.value = Math.max(160, Math.min(360, available))
}

function findBottomOverlayLimit(rootRect, viewportHeight) {
  let limit = viewportHeight
  const candidates = document.querySelectorAll('body *')
  candidates.forEach(element => {
    if (element === rootRef.value || rootRef.value?.contains(element)) return
    const style = window.getComputedStyle(element)
    if (!['fixed', 'sticky'].includes(style.position)) return
    const rect = element.getBoundingClientRect()
    if (rect.width <= 0 || rect.height <= 0) return
    if (rect.top < rootRect.bottom - 1) return
    if (rect.top > viewportHeight) return
    if (rect.right <= rootRect.left || rect.left >= rootRect.right) return
    limit = Math.min(limit, rect.top)
  })
  return limit
}

function moveActive(delta) {
  if (!normalizedOptions.value.length) return
  const count = normalizedOptions.value.length
  activeIndex.value = (activeIndex.value + delta + count) % count
}

function handleButtonKeydown(event) {
  if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
    event.preventDefault()
    if (!open.value) openMenu()
    else moveActive(event.key === 'ArrowDown' ? 1 : -1)
    return
  }
  if (event.key === 'Enter' || event.key === ' ') {
    event.preventDefault()
    if (!open.value) {
      openMenu()
      return
    }
    const option = normalizedOptions.value[activeIndex.value]
    if (option) selectOption(option)
    return
  }
  if (event.key === 'Escape') {
    closeMenu()
    buttonRef.value?.focus()
  }
}

watch(() => props.modelValue, () => {
  activeIndex.value = selectedIndex.value >= 0 ? selectedIndex.value : 0
})

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', handleOutside)
  document.removeEventListener('focusin', handleOutside)
})
</script>

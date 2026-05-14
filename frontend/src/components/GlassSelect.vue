<template>
  <div
    ref="rootRef"
    class="glass-select"
    :class="[
      `glass-select--${size}`,
      `glass-select--${placement}`,
      { 'is-open': open, 'is-empty': selectedIndex === -1, 'glass-select--up': dropUp },
    ]"
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

    <Teleport to="body">
      <transition name="glass-select-menu">
        <div
          v-if="open"
          ref="menuRef"
          class="glass-select__menu"
          :class="[
            `glass-select__menu--${placement}`,
            { 'glass-select__menu--up': dropUp },
          ]"
          :style="menuStyle"
          role="listbox"
          :aria-label="ariaLabel || placeholder"
        >
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
    </Teleport>
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

const MENU_MIN_WIDTH = 168
const MENU_MIN_HEIGHT = 44

const open = ref(false)
const activeIndex = ref(-1)
const dropUp = ref(false)
const rootRef = ref(null)
const buttonRef = ref(null)
const menuRef = ref(null)
const menuStyle = ref({})
let placementFrame = 0

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
  menuStyle.value = hiddenMenuStyle()
  activeIndex.value = selectedIndex.value >= 0 ? selectedIndex.value : 0
  document.addEventListener('mousedown', handleOutside)
  document.addEventListener('focusin', handleOutside)
  window.addEventListener('resize', requestMenuPlacement)
  window.addEventListener('scroll', requestMenuPlacement, true)
  window.visualViewport?.addEventListener('resize', requestMenuPlacement)
  window.visualViewport?.addEventListener('scroll', requestMenuPlacement)
  nextTick(requestMenuPlacement)
  scrollActiveOptionIntoView()
}

function closeMenu() {
  if (!open.value) return
  open.value = false
  dropUp.value = false
  menuStyle.value = {}
  document.removeEventListener('mousedown', handleOutside)
  document.removeEventListener('focusin', handleOutside)
  window.removeEventListener('resize', requestMenuPlacement)
  window.removeEventListener('scroll', requestMenuPlacement, true)
  window.visualViewport?.removeEventListener('resize', requestMenuPlacement)
  window.visualViewport?.removeEventListener('scroll', requestMenuPlacement)
  if (placementFrame) {
    window.cancelAnimationFrame(placementFrame)
    placementFrame = 0
  }
}

function toggle() {
  if (open.value) closeMenu()
  else openMenu()
}

function handleOutside(event) {
  if (rootRef.value?.contains(event.target) || menuRef.value?.contains(event.target)) return
  closeMenu()
}

function selectOption(option) {
  emit('update:modelValue', option.value)
  emit('change', option.value)
  closeMenu()
  nextTick(() => buttonRef.value?.focus())
}

function hiddenMenuStyle() {
  return {
    visibility: 'hidden',
    pointerEvents: 'none',
  }
}

function requestMenuPlacement() {
  if (placementFrame) return
  placementFrame = window.requestAnimationFrame(() => {
    placementFrame = 0
    updateMenuPlacement()
  })
}

function updateMenuPlacement() {
  if (!rootRef.value || !buttonRef.value || !menuRef.value) return
  const buttonRect = buttonRef.value.getBoundingClientRect()
  const viewport = currentViewport()
  const safeMargin = viewport.width <= 768 ? 10 : 12
  const gap = props.size === 'compact' ? 6 : 8
  const viewportWidth = Math.max(0, viewport.width - safeMargin * 2)
  const menuWidth = Math.min(
    Math.max(buttonRect.width, MENU_MIN_WIDTH),
    Math.max(0, viewportWidth),
  )
  const desiredHeight = menuNaturalHeight()
  const limits = findVerticalOverlayLimits(buttonRect, viewport)
  const minTop = limits.top + safeMargin
  const maxBottom = limits.bottom - safeMargin
  const spaceBelow = Math.max(0, maxBottom - buttonRect.bottom - gap)
  const spaceAbove = Math.max(0, buttonRect.top - gap - minTop)

  dropUp.value = spaceBelow < desiredHeight && spaceAbove > spaceBelow
  const available = dropUp.value ? spaceAbove : spaceBelow
  const menuHeight = Math.max(0, Math.min(desiredHeight, available))
  const unclampedLeft = props.placement === 'right' ? buttonRect.right - menuWidth : buttonRect.left
  const left = Math.min(
    Math.max(unclampedLeft, viewport.left + safeMargin),
    Math.max(viewport.left + safeMargin, viewport.right - menuWidth - safeMargin),
  )
  const unclampedTop = dropUp.value ? buttonRect.top - gap - menuHeight : buttonRect.bottom + gap
  const maxTop = Math.max(minTop, maxBottom - menuHeight)
  const top = dropUp.value
    ? Math.max(minTop, Math.min(unclampedTop, maxTop))
    : Math.min(Math.max(unclampedTop, minTop), maxTop)

  menuStyle.value = {
    left: `${left}px`,
    top: `${top}px`,
    width: `${menuWidth}px`,
    maxHeight: `${menuHeight}px`,
    visibility: 'visible',
    pointerEvents: 'auto',
    transformOrigin: dropUp.value
      ? (props.placement === 'right' ? 'bottom right' : 'bottom left')
      : (props.placement === 'right' ? 'top right' : 'top left'),
  }
}

function currentViewport() {
  const visualViewport = window.visualViewport
  const width = visualViewport?.width || window.innerWidth || document.documentElement.clientWidth || 0
  const height = visualViewport?.height || window.innerHeight || document.documentElement.clientHeight || 0
  const left = visualViewport?.offsetLeft || 0
  const top = visualViewport?.offsetTop || 0

  return {
    left,
    top,
    width,
    height,
    right: left + width,
    bottom: top + height,
  }
}

function menuNaturalHeight() {
  if (!menuRef.value) return MENU_MIN_HEIGHT
  const borderHeight = Math.max(0, menuRef.value.offsetHeight - menuRef.value.clientHeight)
  const fallback = normalizedOptions.value.length
    ? normalizedOptions.value.length * 38 + 10
    : MENU_MIN_HEIGHT
  return Math.max(MENU_MIN_HEIGHT, Math.ceil((menuRef.value.scrollHeight || fallback) + borderHeight))
}

function findVerticalOverlayLimits(buttonRect, viewport) {
  let top = viewport.top
  let bottom = viewport.bottom
  const candidates = document.querySelectorAll('body *')
  candidates.forEach(element => {
    if (element === rootRef.value || rootRef.value?.contains(element)) return
    if (element === menuRef.value || menuRef.value?.contains(element)) return
    const style = window.getComputedStyle(element)
    if (!['fixed', 'sticky'].includes(style.position)) return
    const rect = element.getBoundingClientRect()
    if (rect.width <= 0 || rect.height <= 0) return
    if (rect.bottom <= viewport.top || rect.top >= viewport.bottom) return
    if (rect.right <= buttonRect.left || rect.left >= buttonRect.right) return

    if (rect.top >= buttonRect.bottom - 1) bottom = Math.min(bottom, rect.top)
    if (rect.bottom <= buttonRect.top + 1) top = Math.max(top, rect.bottom)
  })
  return { top, bottom }
}

function moveActive(delta) {
  if (!normalizedOptions.value.length) return
  const count = normalizedOptions.value.length
  activeIndex.value = (activeIndex.value + delta + count) % count
  scrollActiveOptionIntoView()
}

function scrollActiveOptionIntoView() {
  if (!open.value) return
  nextTick(() => {
    menuRef.value
      ?.querySelector('.glass-select__option.is-active')
      ?.scrollIntoView({ block: 'nearest' })
  })
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

watch(normalizedOptions, () => {
  if (open.value) nextTick(requestMenuPlacement)
})

onBeforeUnmount(() => {
  document.removeEventListener('mousedown', handleOutside)
  document.removeEventListener('focusin', handleOutside)
  window.removeEventListener('resize', requestMenuPlacement)
  window.removeEventListener('scroll', requestMenuPlacement, true)
  window.visualViewport?.removeEventListener('resize', requestMenuPlacement)
  window.visualViewport?.removeEventListener('scroll', requestMenuPlacement)
  if (placementFrame) window.cancelAnimationFrame(placementFrame)
})
</script>

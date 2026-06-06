<template>
  <span
    ref="wrapperRef"
    class="tactile-press"
    :data-disabled="disabled ? 'true' : null"
    @pointerdown="onPointerDown"
    @pointerup="onPointerUp"
    @pointerleave="onPointerLeave"
  >
    <slot />
  </span>
</template>

<script setup>
import { onBeforeUnmount, ref } from 'vue'
import '../assets/tactilePress.css'

const props = defineProps({
  disabled: { type: Boolean, default: false },
  intensity: {
    type: String,
    default: 'medium',
    validator: value => ['light', 'medium', 'strong'].includes(value),
  },
})

const emit = defineEmits(['press', 'release', 'tap'])

const wrapperRef = ref(null)
let pressedTarget = null
let pressStartedAt = 0
let activePointerId = null

function pressTargetFrom(event) {
  const wrapper = wrapperRef.value
  if (!wrapper) return null
  const target = event.target instanceof Element ? event.target : null
  if (!target || target === wrapper) return wrapper.firstElementChild
  const explicitTarget = target.closest('[data-tactile-target]')
  if (explicitTarget && wrapper.contains(explicitTarget)) return explicitTarget
  return wrapper.firstElementChild
}

function clearPressTarget() {
  if (!pressedTarget) return
  pressedTarget.removeAttribute('data-press')
  pressedTarget.removeAttribute('data-press-intensity')
  pressedTarget = null
}

function release(event, { tap = false } = {}) {
  if (props.disabled || !pressedTarget) return

  const elapsed = Date.now() - pressStartedAt
  clearPressTarget()
  activePointerId = null
  emit('release', event)
  if (tap && elapsed < 200) emit('tap', event)
}

function onPointerDown(event) {
  if (props.disabled) return

  clearPressTarget()
  pressedTarget = pressTargetFrom(event)
  if (!pressedTarget) return

  pressStartedAt = Date.now()
  activePointerId = event.pointerId
  pressedTarget.dataset.press = 'true'
  pressedTarget.dataset.pressIntensity = props.intensity
  emit('press', event)
}

function onPointerUp(event) {
  if (activePointerId !== null && event.pointerId !== activePointerId) return
  release(event, { tap: true })
}

function onPointerLeave(event) {
  release(event)
}

onBeforeUnmount(() => {
  clearPressTarget()
})
</script>

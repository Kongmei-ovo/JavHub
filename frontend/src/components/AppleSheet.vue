<template>
  <div
    :class="['apple-sheet-shell', { 'apple-sheet-shell--open': open }]"
    :aria-hidden="open ? undefined : 'true'"
    :inert="open ? undefined : ''"
    :style="shellStyle"
  >
    <button
      class="apple-sheet-backdrop"
      type="button"
      aria-label="关闭面板"
      @click="closeSheet"
    ></button>
    <section
      ref="sheetRef"
      class="apple-sheet"
      role="dialog"
      aria-modal="true"
      :aria-label="title || undefined"
      :style="sheetStyle"
    >
      <header class="apple-sheet__header">
        <button
          class="apple-sheet__grabber-button"
          type="button"
          aria-label="拖动关闭面板"
          @touchstart="startDrag"
          @touchmove="moveDrag"
          @touchend="endDrag"
          @touchcancel="cancelDrag"
        >
          <span class="apple-sheet__grabber" aria-hidden="true"></span>
        </button>
        <h2 v-if="title" class="apple-sheet__title">{{ title }}</h2>
      </header>
      <div class="apple-sheet__body">
        <slot></slot>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import '../assets/sheet.css'

const props = defineProps({
  open: { type: Boolean, default: false },
  snapPoints: { type: Array, default: () => [0.5, 1] },
  title: { type: String, default: '' },
})

const emit = defineEmits(['update:open', 'snap'])

const sheetRef = ref(null)
const startY = ref(0)
const dragY = ref(0)
const isDragging = ref(false)
const activeSnap = ref(normalizedSnapPoints()[0])

const sheetStyle = computed(() => ({
  '--apple-sheet-drag-y': `${dragY.value}px`,
  '--apple-sheet-max-height': `${activeSnap.value * 100}dvh`,
}))

const shellStyle = computed(() => ({
  '--apple-sheet-progress': String(dragProgress()),
}))

watch(
  () => props.open,
  value => {
    if (value) {
      activeSnap.value = normalizedSnapPoints()[0]
      resetDrag()
    }
  }
)

function normalizedSnapPoints() {
  const points = props.snapPoints
    .map(Number)
    .filter(point => Number.isFinite(point) && point > 0 && point <= 1)
    .sort((a, b) => a - b)

  return points.length ? points : [0.5, 1]
}

function currentTouchY(event) {
  return event.touches?.[0]?.clientY ?? event.changedTouches?.[0]?.clientY ?? 0
}

function startDrag(event) {
  isDragging.value = true
  startY.value = currentTouchY(event)
}

function moveDrag(event) {
  if (!isDragging.value) return
  event.preventDefault?.()
  const delta = currentTouchY(event) - startY.value
  dragY.value = delta < 0 ? delta * 0.5 : delta
}

function endDrag() {
  if (!isDragging.value) return
  isDragging.value = false
  const sheetHeight = sheetRef.value?.offsetHeight || window.innerHeight || 1
  const closeThreshold = sheetHeight * 0.25

  if (dragY.value >= closeThreshold) {
    closeSheet()
    return
  }

  const nextSnap = nearestSnapPoint()
  activeSnap.value = nextSnap
  resetDrag()
  emit('snap', nextSnap)
}

function cancelDrag() {
  isDragging.value = false
  resetDrag()
}

function nearestSnapPoint() {
  const points = normalizedSnapPoints()
  const sheetHeight = sheetRef.value?.offsetHeight || window.innerHeight || 1
  const current = activeSnap.value - dragY.value / sheetHeight

  return points.reduce((nearest, point) => (
    Math.abs(point - current) < Math.abs(nearest - current) ? point : nearest
  ), points[0])
}

function dragProgress() {
  const sheetHeight = sheetRef.value?.offsetHeight || window.innerHeight || 1
  const distance = Math.max(0, dragY.value)
  return Math.max(0, Math.min(1, 1 - distance / sheetHeight))
}

function resetDrag() {
  dragY.value = 0
}

function closeSheet() {
  resetDrag()
  emit('update:open', false)
}
</script>

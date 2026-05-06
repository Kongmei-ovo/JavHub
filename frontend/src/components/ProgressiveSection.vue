<template>
  <section ref="sectionRef" :class="['progressive-section', { 'is-visible': visible }]">
    <slot v-if="visible || eager" />
    <slot v-else name="placeholder" />
  </section>
</template>

<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'

const props = defineProps({
  eager: { type: Boolean, default: false },
  rootMargin: { type: String, default: '240px 0px' },
})

const sectionRef = ref(null)
const visible = ref(props.eager)
let observer = null

onMounted(() => {
  if (visible.value || typeof IntersectionObserver === 'undefined' || !sectionRef.value) {
    visible.value = true
    return
  }
  observer = new IntersectionObserver((entries) => {
    if (entries.some(entry => entry.isIntersecting)) {
      visible.value = true
      observer?.disconnect()
      observer = null
    }
  }, { rootMargin: props.rootMargin })
  observer.observe(sectionRef.value)
})

onBeforeUnmount(() => {
  observer?.disconnect()
})
</script>

<style scoped>
.progressive-section.is-visible {
  animation: apple-content-reveal var(--motion-reveal);
}
</style>

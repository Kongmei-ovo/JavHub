<template>
  <AppleVideoCard
    :video="video"
    :cover-url="coverUrl"
    @open="$emit('click')"
  />
</template>

<script setup>
import { computed } from 'vue'
import AppleVideoCard from './AppleVideoCard.vue'

const props = defineProps({
  contentId: { type: String, required: true },
  dvdId: { type: String, default: '' },
  coverUrl: { type: String, default: '' },
  title: { type: String, default: '' },
  serviceCode: { type: String, default: '' },
  releaseDate: { type: String, default: '' },
  runtimeMins: { type: [String, Number], default: '' },
  sampleUrl: { type: String, default: '' },
})

defineEmits(['click'])

const video = computed(() => ({
  content_id: props.contentId,
  dvd_id: props.dvdId || props.contentId,
  title_ja: props.title,
  jacket_thumb_url: props.coverUrl,
  service_code: props.serviceCode,
  release_date: props.releaseDate,
  runtime_mins: props.runtimeMins,
  sample_url: props.sampleUrl,
}))
</script>

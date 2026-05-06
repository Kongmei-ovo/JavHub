<template>
  <AppleVideoCard
    :video="video"
    :cover-url="coverUrl"
    :favorited="isFavorited"
    :show-favorite="true"
    @open="$emit('click')"
    @toggle-favorite="$emit('toggle-favorite')"
  />
</template>

<script setup>
import { computed } from 'vue'
import AppleVideoCard from './AppleVideoCard.vue'

const props = defineProps({
  contentId: { type: String, required: true },
  coverUrl: { type: String, default: '' },
  title: { type: String, default: '' },
  serviceCode: { type: String, default: '' },
  releaseDate: { type: String, default: '' },
  runtimeMins: { type: [String, Number], default: '' },
  sampleUrl: { type: String, default: '' },
  isFavorited: { type: Boolean, default: false }
})

defineEmits(['click', 'toggle-favorite'])

const video = computed(() => ({
  content_id: props.contentId,
  dvd_id: props.contentId,
  title_ja: props.title,
  jacket_thumb_url: props.coverUrl,
  service_code: props.serviceCode,
  release_date: props.releaseDate,
  runtime_mins: props.runtimeMins,
  sample_url: props.sampleUrl,
}))
</script>

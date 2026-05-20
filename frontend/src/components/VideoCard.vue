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
  title: { type: String, default: '' },
  coverUrl: { type: String, default: '' },
  actressNames: { type: String, default: '' },
  releaseDate: { type: String, default: '' },
  serviceCode: { type: String, default: '' }
})

defineEmits(['click'])

const video = computed(() => ({
  content_id: props.contentId,
  dvd_id: props.contentId,
  title_ja: props.title || props.actressNames,
  jacket_thumb_url: props.coverUrl,
  release_date: props.releaseDate,
  service_code: props.serviceCode,
}))

</script>

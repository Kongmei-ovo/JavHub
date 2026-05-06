<template>
  <AppleVideoCard
    :video="video"
    :cover-url="coverUrl"
    :favorited="isFavorited"
    :show-favorite="true"
    @open="$emit('click')"
    @toggle-favorite="toggleFavorite"
  />
</template>

<script setup>
import { computed } from 'vue'
import AppleVideoCard from './AppleVideoCard.vue'
import favoriteState from '../utils/favoriteState'

const props = defineProps({
  contentId: { type: String, required: true },
  title: { type: String, default: '' },
  coverUrl: { type: String, default: '' },
  actressNames: { type: String, default: '' },
  releaseDate: { type: String, default: '' }
})

defineEmits(['click'])

const video = computed(() => ({
  content_id: props.contentId,
  dvd_id: props.contentId,
  title_ja: props.title || props.actressNames,
  jacket_thumb_url: props.coverUrl,
  release_date: props.releaseDate,
}))

const isFavorited = computed(() => favoriteState.isFavorited('video', props.contentId))

const toggleFavorite = async () => {
  await favoriteState.toggle('video', props.contentId)
}
</script>

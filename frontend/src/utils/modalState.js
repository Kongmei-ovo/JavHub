import { reactive } from 'vue'
import defaultApi from '../api/index.js'
import { normalizeVideo, videoCodeOf } from './videoNormalize.js'

let modalRequestId = 0

export const modalState = reactive({
  selectedVideo: null,
  visible: false,
  openedOnRoute: null, // 记录弹窗是在哪个页面打开的
  interrupted: false   // 记录是否因为点击 Tag 导航而暂时隐藏
})

function withLoadingState(video, contentId, api) {
  const normalized = normalizeVideo(video)
  const fetchPrimaryDetails = shouldFetchPrimaryDetails(video, contentId)
  const fetchSupplementDetails = shouldFetchSupplementDetails(video, contentId, api)
  return {
    ...normalized,
    _loading: {
      javinfo: Boolean(fetchPrimaryDetails && api?.getVideo),
      metatube: Boolean(fetchPrimaryDetails && api?.getVideoMetadata),
      supplement: Boolean(fetchSupplementDetails),
      cover: true,
      gallery: false,
      ...(video._loading || {})
    },
    _errors: {
      javinfo: null,
      metatube: null,
      cover: null,
      gallery: null,
      stream: null,
      ...(video._errors || {})
    }
  }
}

function shouldFetchPrimaryDetails(video, contentId) {
  if (!contentId) return false
  if (String(contentId).startsWith('supp:')) return false
  if (video?.data_origin === 'supplement') return false
  if (String(video?.resolved_id || '').startsWith('supp:')) return false
  return true
}

function supplementMovieIdOf(video, contentId) {
  for (const value of [contentId, video?.resolved_id, video?.content_id]) {
    const match = String(value || '').match(/^supp:(\d+)$/)
    if (match) return Number(match[1])
  }
  return null
}

function shouldFetchSupplementDetails(video, contentId, api) {
  return Boolean(api?.getSupplementMovieSources && supplementMovieIdOf(video, contentId))
}

function parsedJSONValue(value) {
  if (typeof value !== 'string') return value
  try {
    return JSON.parse(value)
  } catch {
    return value
  }
}

function namedEntity(name, fields = ['name_ja', 'name_en']) {
  const value = String(name || '').trim()
  if (!value || value === '----') return undefined
  const entity = {}
  for (const field of fields) {
    entity[field] = value
  }
  return entity
}

function arrayField(value) {
  const parsed = parsedJSONValue(value)
  if (!Array.isArray(parsed)) return []
  return parsed.map(item => String(item || '').trim()).filter(Boolean)
}

function supplementSourcesToVideo(data = {}) {
  const fields = {}
  const translatedFields = {}
  for (const field of data.chosen_fields || []) {
    if (!field?.field_name) continue
    fields[field.field_name] = field.field_value
    if (field.field_value_translated) {
      translatedFields[field.field_name] = field.field_value_translated
    }
  }

  const categories = arrayField(fields.category_names).map(name => ({
    id: name,
    name_ja: name,
    name_en: name,
  }))
  const translatedCategories = arrayField(translatedFields.category_names)
  categories.forEach((category, index) => {
    if (translatedCategories[index] && translatedCategories[index] !== category.name_ja) {
      category.name_ja_translated = translatedCategories[index]
      category.name_en_translated = translatedCategories[index]
    }
  })
  const actresses = arrayField(fields.actor_names).map(name => ({
    id: name,
    name_kanji: name,
    name_romaji: name,
  }))
  const translatedActresses = arrayField(translatedFields.actor_names)
  actresses.forEach((actress, index) => {
    if (translatedActresses[index] && translatedActresses[index] !== actress.name_kanji) {
      actress.name_kanji_translated = translatedActresses[index]
      actress.name_romaji_translated = translatedActresses[index]
    }
  })
  const patch = {
    title_ja: fields.title,
    title_ja_translated: translatedFields.title,
    summary: fields.summary || fields.description,
    summary_translated: translatedFields.summary || translatedFields.description,
    dvd_id: fields.display_number || fields.raw_number,
    release_date: fields.release_date,
    runtime_mins: fields.runtime_mins ? Number(fields.runtime_mins) : undefined,
    maker: namedEntity(fields.maker_name),
    label: namedEntity(fields.label_name),
    series: namedEntity(fields.series_name),
    categories: categories.length ? categories : undefined,
    actresses: actresses.length ? actresses : undefined,
    jacket_full_url: fields.cover_url,
    jacket_thumb_url: fields.cover_thumb_url,
    sample_url: fields.sample_movie_url,
    sample_image_urls: arrayField(fields.sample_image_urls),
    _supplementSources: data,
  }
  for (const [key, fieldName] of [['maker', 'maker_name'], ['label', 'label_name'], ['series', 'series_name']]) {
    if (patch[key] && translatedFields[fieldName]) {
      patch[key].name_ja_translated = translatedFields[fieldName]
      patch[key].name_en_translated = translatedFields[fieldName]
      patch[key].name_translated = translatedFields[fieldName]
    }
  }
  for (const key of Object.keys(patch)) {
    if (patch[key] === undefined || patch[key] === '') {
      delete patch[key]
    }
  }
  if (!patch.sample_image_urls?.length) delete patch.sample_image_urls
  return patch
}

function isCurrentRequest(requestId, contentId) {
  return modalRequestId === requestId && videoCodeOf(modalState.selectedVideo) === contentId
}

function errorMessage(error) {
  return error?.response?.data?.detail
    || error?.response?.data?.message
    || error?.message
    || '网络错误'
}

export function openVideoModal(video, routePath = null, api = defaultApi) {
  const requestId = ++modalRequestId
  const contentId = videoCodeOf(video)
  const fetchPrimaryDetails = shouldFetchPrimaryDetails(video, contentId)
  modalState.selectedVideo = withLoadingState(video, contentId, api)
  modalState.visible = true
  modalState.interrupted = false
  if (routePath) {
    modalState.openedOnRoute = routePath
  }

  if (fetchPrimaryDetails && api?.getVideo) {
    api.getVideo(contentId)
      .then(response => {
        if (isCurrentRequest(requestId, contentId)) {
          modalState.selectedVideo = {
            ...modalState.selectedVideo,
            ...(response?.data || {}),
            _loading: {
              ...modalState.selectedVideo._loading,
              javinfo: false,
            },
          }
        }
      })
      .catch(error => {
        if (isCurrentRequest(requestId, contentId)) {
          modalState.selectedVideo._loading.javinfo = false
          modalState.selectedVideo._errors.javinfo = errorMessage(error)
        }
      })
  }

  if (fetchPrimaryDetails && api?.getVideoMetadata) {
    api.getVideoMetadata(contentId)
      .then(response => {
        if (isCurrentRequest(requestId, contentId)) {
          modalState.selectedVideo = {
            ...modalState.selectedVideo,
            ...(response?.data || {}),
            _loading: {
              ...modalState.selectedVideo._loading,
              metatube: false,
            },
          }
        }
      })
      .catch(error => {
        if (isCurrentRequest(requestId, contentId)) {
          modalState.selectedVideo._loading.metatube = false
          modalState.selectedVideo._errors.metatube = errorMessage(error)
        }
      })
  }

  const supplementMovieId = supplementMovieIdOf(video, contentId)
  if (supplementMovieId && api?.getSupplementMovieSources) {
    api.getSupplementMovieSources(supplementMovieId)
      .then(response => {
        if (isCurrentRequest(requestId, contentId)) {
          modalState.selectedVideo = {
            ...modalState.selectedVideo,
            ...supplementSourcesToVideo(response?.data || {}),
            _loading: {
              ...modalState.selectedVideo._loading,
              supplement: false,
            },
          }
        }
      })
      .catch(error => {
        if (isCurrentRequest(requestId, contentId)) {
          modalState.selectedVideo._loading.supplement = false
          modalState.selectedVideo._errors.supplement = errorMessage(error)
        }
      })
  }
}

export function closeVideoModal() {
  modalState.visible = false
  modalState.interrupted = false
  // 延迟清除数据，给动画留时间
  setTimeout(() => {
    if (!modalState.visible && !modalState.interrupted) {
      modalState.selectedVideo = null
      modalState.openedOnRoute = null
    }
  }, 300)
}

// 暂时隐藏弹窗（用于跳转到 Tag 页面）
export function interruptModal() {
  if (modalState.visible) {
    modalState.visible = false
    modalState.interrupted = true
  }
}

// 恢复弹窗（从 Tag 页面返回时）
export function resumeModal() {
  if (modalState.interrupted && modalState.selectedVideo) {
    modalState.visible = true
    modalState.interrupted = false
  }
}

export function resetModal() {
  modalRequestId += 1
  modalState.selectedVideo = null
  modalState.visible = false
  modalState.openedOnRoute = null
  modalState.interrupted = false
}

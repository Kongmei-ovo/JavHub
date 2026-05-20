import { videoCodeOf } from './videoNormalize.js'

export function shouldFallbackToVideoModal(video = {}) {
  return String(videoCodeOf(video)).startsWith('supp:')
    || String(video?.resolved_id || '').startsWith('supp:')
    || video?.data_origin === 'supplement'
}

export function openVideoDetail(video, router, route, fallbackOpenModal) {
  const contentId = videoCodeOf(video)
  if (!contentId) return
  if (shouldFallbackToVideoModal(video)) {
    if (typeof fallbackOpenModal === 'function') {
      fallbackOpenModal(video, route?.fullPath || route?.path || null)
    }
    return
  }
  const serviceCode = String(video?.service_code || '').trim()
  router.push({
    name: 'VideoDetail',
    params: { contentId },
    ...(serviceCode ? { query: { service_code: serviceCode } } : {}),
  })
}

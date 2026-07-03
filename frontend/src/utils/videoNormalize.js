import { dmmCoverCandidates } from './imageUrl.js'

export function videoCodeOf(video = {}) {
  const code = [video?.content_id, video?.dvd_id, video?.code, video?.id]
    .find(identifier => identifier != null && identifier !== '')
  return code == null ? '' : String(code)
}

export function normalizeVideo(video = {}) {
  const code = videoCodeOf(video)
  const title = video.title_ja || video.title_en || video.title || ''
  const cover = video.jacket_thumb_url || video.jacket_full_url || video.cover_url || ''
  const releaseDate = video.release_date || video.date || ''

  return {
    ...video,
    content_id: video.content_id || code,
    dvd_id: video.dvd_id || code,
    display_code: video.display_code || video.dvd_id || code,
    canonical_code: video.canonical_code || '',
    variant_labels: Array.isArray(video.variant_labels) ? video.variant_labels : [],
    variant_explanations: Array.isArray(video.variant_explanations) ? video.variant_explanations : [],
    title_ja: video.title_ja || title,
    jacket_thumb_url: video.jacket_thumb_url || cover,
    release_date: video.release_date || releaseDate,
  }
}

// 卡片封面候选统一走 imageUrl.js 的单一实现（老库 800px 优先、@error 逐级降级）。
export function videoCoverCandidates(video = {}, preferredCoverUrl = '') {
  return dmmCoverCandidates(video, { preferred: preferredCoverUrl })
}

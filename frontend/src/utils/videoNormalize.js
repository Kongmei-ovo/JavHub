export function videoCodeOf(video = {}) {
  const code = video?.content_id ?? video?.dvd_id ?? video?.code ?? video?.id ?? ''
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
    title_ja: video.title_ja || title,
    jacket_thumb_url: video.jacket_thumb_url || cover,
    release_date: video.release_date || releaseDate,
  }
}

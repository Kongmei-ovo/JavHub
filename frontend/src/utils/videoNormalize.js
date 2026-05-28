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

export function videoCoverCandidates(video = {}, preferredCoverUrl = '') {
  const candidates = []
  const add = (value) => {
    const url = String(value || '').trim()
    if (url && !candidates.includes(url)) candidates.push(url)
  }
  const sourceUrls = [
    preferredCoverUrl,
    video.jacket_thumb_url,
    video.jacket_full_url,
    video.cover_url,
  ]

  for (const url of sourceUrls) {
    add(url)
  }
  for (const url of sourceUrls) {
    add(deriveDmmHdCoverUrl(url))
  }
  return candidates
}

function deriveDmmHdCoverUrl(url) {
  const text = String(url || '').trim()
  if (!text) return ''
  const match = text.match(/\/([a-z0-9_]+)(?:ps|pl)\.jpg$/i)
  if (!match) return ''
  const id = match[1]
  const padded = padDmmContentId(id)
  if (/\/dig\/mono\/movie\//i.test(text)) {
    const hostMatch = text.match(/^https?:\/\/([^/]+)/i)
    const host = hostMatch ? hostMatch[1] : 'awsimgsrc.dmm.co.jp'
    return `https://${host}/dig/mono/movie/${id}/${id}ps.jpg`
  }
  return `https://awsimgsrc.dmm.co.jp/pics_dig/digital/video/${padded}/${padded}ps.jpg`
}

function padDmmContentId(id) {
  return id.replace(/^([a-z_]+)(\d+)$/i, (match, prefix, num) => {
    if (prefix.length >= 5) return id
    return prefix + num.padStart(5, '0')
  })
}

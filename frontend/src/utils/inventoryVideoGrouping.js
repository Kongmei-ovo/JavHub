export function extractCode(title) {
  if (!title) return ''
  const match = String(title).match(/([A-Z]+-\d+)/i)
  return match ? match[1].toUpperCase() : ''
}

function extractYearFromTitle(title) {
  if (!title) return null
  const match = String(title).match(/\b(19\d{2}|20\d{2})\b/)
  return match ? Number.parseInt(match[1], 10) : null
}

function yearFromDate(date) {
  if (!date) return null
  const match = String(date).match(/^(19\d{2}|20\d{2})/)
  return match ? Number.parseInt(match[1], 10) : null
}

function normalizeYear(year) {
  if (year === null || year === undefined || year === '') return null
  const normalized = Number.parseInt(year, 10)
  return Number.isNaN(normalized) ? null : normalized
}

function embyVideoYear(video) {
  return (
    normalizeYear(video.production_year) ||
    yearFromDate(video.premiere_date) ||
    extractYearFromTitle(video.title)
  )
}

function missingVideoYear(video) {
  return yearFromDate(video.release_date) || extractYearFromTitle(video.title)
}

function sortYearKeys(keys) {
  return keys.sort((a, b) => {
    if (a === '未知') return 1
    if (b === '未知') return -1
    return a.localeCompare(b)
  })
}

function groupByYear(videos, yearOf, mapVideo = (video) => video) {
  const groups = {}
  for (const video of videos || []) {
    const year = yearOf(video)
    const yearKey = year ? String(year) : '未知'
    if (!groups[yearKey]) groups[yearKey] = []
    groups[yearKey].push(mapVideo(video))
  }

  return sortYearKeys(Object.keys(groups)).reduce((acc, key) => {
    acc[key] = groups[key]
    return acc
  }, {})
}

export function groupEmbyVideosByYear(videos) {
  return groupByYear(videos, embyVideoYear, (video) => ({
    ...video,
    displayCode: video._code || extractCode(video.title),
  }))
}

export function groupMissingVideosByYear(videos) {
  return groupByYear(videos, missingVideoYear)
}

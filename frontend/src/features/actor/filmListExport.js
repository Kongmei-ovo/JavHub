// Pure helpers for the actress film-library list view (Actor.vue): ownership
// keys, list sorting, and CSV export. Kept out of the SFC so the component stays
// lean and these stay unit-testable.

// Every identifier a film might be owned under (content_id / dvd_id / canonical
// 番号). A film counts as owned when ANY of these matches a ready 115 resource.
export function movieOwnKeys(movie) {
  return [movie.id, movie.code, movie.display_code, movie.canonical_code, movie._raw?.content_id, movie._raw?.dvd_id]
    .map(key => String(key || '').trim())
    .filter(Boolean)
}

// Stable sort by 番号 / 时长 / 出演时间; undated rows sink last regardless of dir.
export function sortFilmList(movies, key, dir) {
  const d = dir === 'asc' ? 1 : -1
  return [...movies].sort((a, b) => {
    if (key === 'runtime') {
      return (Number(a._raw?.runtime_mins || 0) - Number(b._raw?.runtime_mins || 0)) * d
    }
    if (key === 'code') {
      return String(a.display_code || a.code || '').localeCompare(String(b.display_code || b.code || '')) * d
    }
    const av = String(a.date || '')
    const bv = String(b.date || '')
    if (av === bv) return 0
    if (!av) return 1
    if (!bv) return -1
    return av < bv ? -d : d
  })
}

// Quote/escape a CSV field and neutralize spreadsheet formula injection.
export function csvEscape(value) {
  let s = String(value ?? '')
  if (/^[=+@]/.test(s)) s = `'${s}`
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s
}

// Build the film-library CSV (with header) from normalized movies + an owned test.
export function filmsToCsv(movies, isOwned) {
  const header = ['番号', '片名', '时长(分钟)', '出演时间', '115拥有']
  const rows = movies.map(m => [
    m.display_code || m.code || m.id || '',
    m.title || '',
    m._raw?.runtime_mins || '',
    m.date || '',
    isOwned(m) ? '是' : '否',
  ])
  return [header, ...rows].map(r => r.map(csvEscape).join(',')).join('\r\n')
}

// Trigger a client-side CSV download (UTF-8 BOM so Excel reads CJK correctly).
export function downloadCsv(content, filename) {
  const blob = new Blob(['﻿' + content], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

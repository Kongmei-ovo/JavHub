// Shared formatting + file-kind helpers for the 115 drive views (grid + list).
// Pure functions, no Vue — so grid and list render identically.

export const VIDEO_EXT = new Set(['mp4', 'mkv', 'avi', 'wmv', 'ts', 'm4v', 'mov', 'flv', 'rmvb', 'webm', 'mpg', 'mpeg'])
export const IMAGE_EXT = new Set(['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'heic', 'heif', 'avif'])

export function kindOf(file) {
  if (file.is_dir) return 'folder'
  const ext = String(file.extension || '').toLowerCase()
  if (VIDEO_EXT.has(ext)) return 'video'
  if (IMAGE_EXT.has(ext)) return 'image'
  return 'file'
}

export function glyph(file) {
  return { folder: '📁', video: '🎬', image: '🖼', file: '📄' }[kindOf(file)]
}

export function formatSize(bytes) {
  const n = Number(bytes || 0)
  if (!n) return '—'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let v = n
  let i = 0
  while (v >= 1024 && i < units.length - 1) { v /= 1024; i++ }
  return `${v >= 100 || i === 0 ? Math.round(v) : v.toFixed(1)} ${units[i]}`
}

export function formatDuration(sec) {
  const s = Math.round(Number(sec || 0))
  if (!s) return ''
  const h = Math.floor(s / 3600)
  const m = Math.floor((s % 3600) / 60)
  const ss = s % 60
  const pad = (x) => String(x).padStart(2, '0')
  return h ? `${h}:${pad(m)}:${pad(ss)}` : `${m}:${pad(ss)}`
}

export function formatDate(epochSeconds) {
  const s = Number(epochSeconds || 0)
  if (!s) return '—'
  const d = new Date(s * 1000)
  if (Number.isNaN(d.getTime())) return '—'
  const pad = (x) => String(x).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// 类型标签:文件夹优先,其次大写扩展名,最后“文件”。用于列表视图的“类型”列与按类型排序。
export function typeLabel(file) {
  if (file.is_dir) return '文件夹'
  const ext = String(file.extension || '').toLowerCase()
  return ext ? ext.toUpperCase() : '文件'
}

// 已加载页内的客户端排序。文件夹永远置顶;名称/大小/类型/时间四种键。
// 名称/大小/时间在服务端已排好(115 的 o/asc);类型 115 无原生支持,只能页内排。
export function sortFilesByType(files, asc = true) {
  const dir = asc ? 1 : -1
  return [...files].sort((a, b) => {
    if (a.is_dir !== b.is_dir) return a.is_dir ? -1 : 1
    const at = typeLabel(a)
    const bt = typeLabel(b)
    if (at !== bt) return at < bt ? -dir : dir
    return String(a.name).localeCompare(String(b.name)) * dir
  })
}

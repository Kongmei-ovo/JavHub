// Shared magnet-link parsing for the "添加下载" sheet. Pure functions, no Vue —
// extracted from the old MagnetParse view so the download-task and 115 entry
// points parse identically.

const MAGNET_RE = /magnet:\?xt=urn:btih:([A-Fa-f0-9]+)(?:&dn=([^&]+))?/i

export function decodeMagnetName(value) {
  if (!value) return ''
  try {
    return decodeURIComponent(value.replace(/\+/g, ' '))
  } catch {
    return value
  }
}

/**
 * Parse a textarea of one-link-per-line magnets.
 * @returns {{ parsed: Array<{magnet:string, hash:string, name:string}>, duplicates:number, invalid:Array<{index:number, text:string}> }}
 * Duplicate hashes are counted (not re-added); non-magnet / hash-less lines are
 * collected as invalid with their 1-based line number.
 */
export function parseMagnetInput(text) {
  const lines = String(text || '').split('\n')
  const parsed = []
  const invalid = []
  const seen = new Set()
  let duplicates = 0

  lines.forEach((rawLine, index) => {
    const line = rawLine.trim()
    if (!line) return

    const match = MAGNET_RE.exec(line)
    const fallbackHash = line.match(/btih:([A-Za-z0-9]+)/i)?.[1] || ''
    const hash = (match?.[1] || fallbackHash).toUpperCase()

    if (!/^magnet:/i.test(line) || !hash) {
      invalid.push({ index: index + 1, text: line })
      return
    }
    if (seen.has(hash)) {
      duplicates += 1
      return
    }
    seen.add(hash)
    parsed.push({ magnet: line, hash, name: decodeMagnetName(match?.[2]) })
  })

  return { parsed, duplicates, invalid }
}

export function countInputLines(text) {
  if (!String(text || '').trim()) return 0
  return String(text).split('\n').filter(line => line.trim()).length
}

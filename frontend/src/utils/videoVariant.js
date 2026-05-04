/**
 * AV 影片变体识别
 * 同一部影片可能存在三个版本：
 * - 标准版: MIAA-784
 * - 蓝光版: TKMIAA-784 (TK 前缀)
 * - 加长版: MIAA-784BOD (BOD 后缀)
 */

/**
 * 从 dvd_id 中提取标准版番号
 * @param {string} dvdId - 如 "TKMIAA-784" 或 "MIAA-784BOD"
 * @returns {{ base: string, variant: 'tk' | 'bod' | null }}
 */
export function parseVariant(dvdId) {
  if (!dvdId) return { base: dvdId, variant: null }

  let code = dvdId.toUpperCase()

  // TK 前缀 → 蓝光版
  if (code.startsWith('TK') && code.length > 2 && /[A-Z]/.test(code[2])) {
    return { base: code.slice(2), variant: 'tk' }
  }

  // BOD 后缀 → 加长版
  if (code.endsWith('BOD') && code.length > 3) {
    return { base: code.slice(0, -3), variant: 'bod' }
  }

  return { base: code, variant: null }
}

/**
 * 将影片列表按标准版分组
 * 会直接在 movie 对象上写入 _variant / _baseCode / _variantCount
 * @param {Array} movies - normalizeMovie 后的影片列表
 * @returns {{ canonical: Array, totalVariants: number }}
 */
export function groupByVariant(movies) {
  const canonical = []
  const variants = []

  for (const m of movies) {
    const { base, variant } = parseVariant(m.code)
    m._variant = variant
    m._baseCode = base
    if (variant) {
      variants.push(m)
    } else {
      canonical.push(m)
    }
  }

  return { canonical, variants, totalVariants: variants.length }
}

/**
 * 获取变体的显示标签
 * @param {'tk' | 'bod'} variant
 * @returns {string}
 */
export function variantLabel(variant) {
  if (variant === 'tk') return '蓝光'
  if (variant === 'bod') return '加长'
  return ''
}

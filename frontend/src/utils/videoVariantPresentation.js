export function movieCardVariantProps(item = {}) {
  const displayCode = item.display_code || item.dvd_id || item.content_id || ''
  return {
    contentId: displayCode,
    dvdId: displayCode,
    displayCode,
    canonicalCode: item.canonical_code || '',
    variantLabels: Array.isArray(item.variant_labels) ? item.variant_labels : [],
    variantExplanations: Array.isArray(item.variant_explanations) ? item.variant_explanations : [],
  }
}

export function variantGroupKey(item = {}) {
  return item.canonical_code || item.display_code || item.dvd_id || item.content_id || ''
}

export function visibleVariantItems(item = {}) {
  const items = Array.isArray(item.variant_group_items) ? item.variant_group_items : []
  if (!items.length) return []

  const primaryIdentity = variantIdentity(item)
  return items.filter((variant, index) => {
    if (primaryIdentity && variantIdentity(variant) === primaryIdentity) return false
    if (!primaryIdentity && index === 0) return false
    return true
  })
}

function variantIdentity(item = {}) {
  const contentId = item.content_id || ''
  const dvdId = item.dvd_id || ''
  const serviceCode = item.service_code || ''
  if (contentId || dvdId || serviceCode) return `${contentId}|${dvdId}|${serviceCode}`
  return ''
}

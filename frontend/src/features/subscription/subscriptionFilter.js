export function normalizeSubscriptionKeyword(value) {
  return String(value ?? '').trim().toLocaleLowerCase()
}

export function subscriptionMatchesKeyword(subscription, actorMeta, keyword) {
  const normalizedKeyword = normalizeSubscriptionKeyword(keyword)
  if (!normalizedKeyword) return true

  const meta = actorMeta || {}
  const searchable = [
    meta.name_kanji_translated,
    meta.name_romaji_translated,
    meta.name_kanji,
    meta.name_kana,
    meta.name_romaji,
    subscription?.actress_name,
    subscription?.actress_id,
  ]
    .filter(value => value !== null && value !== undefined && value !== '')
    .join(' ')
    .toLocaleLowerCase()

  return searchable.includes(normalizedKeyword)
}

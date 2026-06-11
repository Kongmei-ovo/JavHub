export async function hydrateSubscriptionActorMeta(subscriptions = [], currentMetaMap = {}, fetchActress) {
  const nextMetaMap = { ...(currentMetaMap || {}) }
  if (typeof fetchActress !== 'function') return nextMetaMap

  const seen = new Set()
  const missingIds = []
  for (const sub of subscriptions || []) {
    const rawId = sub?.actress_id
    const key = String(rawId ?? '').trim()
    if (!key || seen.has(key) || nextMetaMap[key]) continue
    seen.add(key)
    missingIds.push(rawId)
  }

  const results = await Promise.allSettled(missingIds.map(async (actressId) => {
    const response = await fetchActress(actressId)
    const data = response?.data ?? response
    return [String(actressId), data]
  }))

  for (const result of results) {
    if (result.status !== 'fulfilled') continue
    const [key, data] = result.value
    if (data) nextMetaMap[key] = data
  }

  return nextMetaMap
}

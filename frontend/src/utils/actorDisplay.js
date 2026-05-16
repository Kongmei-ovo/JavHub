import { displayName } from './displayLang.js'
import { actressImgUrl } from './imageUrl.js'

export function actorName(actor, fallback = '') {
  if (!actor) return fallback || ''
  return displayName(actor, 'name_kanji', 'name_romaji')
    || actor.name_kanji_translated
    || actor.name_romaji_translated
    || actor.name_translated
    || actor.name_ja_translated
    || actor.name_en_translated
    || actor.name_kanji
    || actor.name_romaji
    || actor.name_ja
    || actor.name_en
    || actor.name
    || fallback
    || ''
}

export function actorOriginalName(actor) {
  if (!actor) return ''
  const primary = actorName(actor)
  const original = actor.name_kanji
    || actor.name_romaji
    || actor.name_ja
    || actor.name_en
    || actor.name
    || ''
  return original && original !== primary ? original : ''
}

export function actorAvatar(actor) {
  if (!actor) return ''
  return actressImgUrl(actor.image_url || actor.avatar_url || actor.javinfo_avatar_url) || ''
}

export function actorInitial(actor, fallback = '') {
  const name = actorName(actor, fallback)
  return (name || '?').slice(0, 1).toUpperCase()
}

export function actorRouteTarget(actor, fallbackId = '') {
  const id = actor?.id || actor?.actress_id || actor?.javinfo_actress_id || fallbackId
  const name = actorName(actor, actor?.actress_name || actor?.javinfo_actress_name || String(fallbackId || ''))
  return {
    name,
    value: String(id || name),
    query: name ? { name } : {},
  }
}

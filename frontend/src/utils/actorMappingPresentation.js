export function candidateName(candidate = {}) {
  return candidate.javinfo_actress_name
    || candidate.name_kanji
    || candidate.name_romaji
    || candidate.name_ja
    || candidate.name_en
    || candidate.name
    || String(candidate.id || '')
}

export function candidateKey(candidate = {}) {
  return String(candidate.id || candidate.javinfo_actress_id || candidate.javinfo_actress_name || candidateName(candidate))
}

export function confidenceText(value) {
  return `${Math.round((Number(value) || 0) * 100)}%`
}

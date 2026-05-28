export { candidateKey, candidateName, confidenceText } from './actorMappingPresentation.js'

export function initials(name) {
  return String(name || '?').slice(0, 1).toUpperCase()
}

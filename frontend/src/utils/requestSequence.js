export function createRequestSequence() {
  let current = 0
  return {
    next() { current += 1; return current },
    isCurrent(token) { return token === current },
    invalidate() { current += 1 },
  }
}

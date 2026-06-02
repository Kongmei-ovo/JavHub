export function applyImageFallback(eventOrElement, options = {}) {
  const image = eventOrElement?.target || eventOrElement
  if (!image || image.dataset?.fallbackApplied === 'true') return

  const label = String(options.label || image.getAttribute?.('alt') || '?').trim() || '?'
  image.dataset.fallbackApplied = 'true'
  image.classList?.add('image-fallback__media')
  image.setAttribute?.('aria-hidden', 'true')
  image.removeAttribute?.('src')

  const container = image.parentElement
  if (!container) return
  container.classList.add(options.className || 'image-fallback')
  container.dataset.fallbackLabel = label
}

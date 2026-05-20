const MESSAGE_EVENT = 'javhub-message'

function normalizeMessage(input) {
  if (typeof input === 'string') return input
  if (input && typeof input === 'object') return input.message || String(input)
  return String(input ?? '')
}

function dispatchMessage(type, input) {
  const message = normalizeMessage(input)
  if (!message) return
  if (typeof window !== 'undefined' && typeof window.dispatchEvent === 'function') {
    window.dispatchEvent(new CustomEvent(MESSAGE_EVENT, {
      detail: { type, message },
    }))
  }
}

export const ElMessage = {
  success(input) { dispatchMessage('success', input) },
  error(input) { dispatchMessage('error', input) },
  warning(input) { dispatchMessage('warning', input) },
  info(input) { dispatchMessage('info', input) },
}

export { MESSAGE_EVENT }

export const JAVHUB_API_KEY_STORAGE_KEY = 'javhub_api_key'

export function getStoredApiKey() {
  try {
    return localStorage.getItem(JAVHUB_API_KEY_STORAGE_KEY) || ''
  } catch {
    return ''
  }
}

export function saveStoredApiKey(value = '') {
  const apiKey = String(value || '').trim()
  try {
    if (apiKey) {
      localStorage.setItem(JAVHUB_API_KEY_STORAGE_KEY, apiKey)
    } else {
      localStorage.removeItem(JAVHUB_API_KEY_STORAGE_KEY)
    }
  } catch {}
  return apiKey
}

export function attachApiKey(config = {}) {
  const apiKey = getStoredApiKey()
  if (!apiKey) return config
  config.headers = config.headers || {}
  config.headers['X-API-Key'] = apiKey
  return config
}

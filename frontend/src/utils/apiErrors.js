export function apiErrorMessage(error, fallback = '网络错误') {
  return error?.response?.data?.detail
    || error?.response?.data?.message
    || error?.message
    || fallback
}

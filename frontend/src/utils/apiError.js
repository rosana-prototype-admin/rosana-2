export function apiErrorMessage(error, fallback) {
  const data = error?.response?.data
  if (typeof data?.detail === 'string') return data.detail
  if (Array.isArray(data)) return data[0] || fallback
  if (data && typeof data === 'object') {
    const first = Object.values(data).flat().find((value) => typeof value === 'string')
    if (first) return first
  }
  return fallback
}

export function formatDate(dateValue: string) {
  return new Date(dateValue).toLocaleDateString()
}

export function formatDateTime(dateValue: string) {
  return new Date(dateValue).toLocaleString()
}

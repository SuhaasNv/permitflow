/** Case-insensitive, whitespace-tolerant substring match: every word of the query must appear in at least one field. */
export function matchesQuery(query: string, fields: ReadonlyArray<string | null | undefined>): boolean {
  const words = query.toLowerCase().split(/\s+/).filter(Boolean)
  if (words.length === 0) return true
  const haystack = fields.filter((f): f is string => typeof f === 'string' && f.length > 0).map((f) => f.toLowerCase())
  return words.every((w) => haystack.some((h) => h.includes(w)))
}

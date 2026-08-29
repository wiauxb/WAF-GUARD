/**
 * Turn any API error into a string safe to hand to a toast.
 *
 * FastAPI's `detail` is NOT always a string. A 422 from request validation returns an
 * ARRAY of objects:
 *
 *   [{ type: "string_too_short", loc: ["body","title"], msg: "String should have at
 *      least 1 character", input: "", ctx: { min_length: 1 } }]
 *
 * Passing that straight to `toast.error(...)` — which 23 call sites did — hands an array of
 * objects to React as children, and React throws "Objects are not valid as a React child",
 * taking the whole page down. A validation mistake became a crash.
 */
export function errorMessage(error: any, fallback = 'Something went wrong'): string {
  const detail = error?.response?.data?.detail

  if (typeof detail === 'string' && detail.trim()) return detail

  // Pydantic validation errors: surface the human-readable part, naming the offending
  // field where it is known, so "title: String should have at least 1 character" rather
  // than a bare complaint about nothing in particular.
  if (Array.isArray(detail)) {
    const parts = detail
      .map((d) => {
        const msg = typeof d?.msg === 'string' ? d.msg : null
        if (!msg) return null
        const field = Array.isArray(d?.loc) ? d.loc[d.loc.length - 1] : null
        return field && field !== 'body' ? `${field}: ${msg}` : msg
      })
      .filter(Boolean)
    if (parts.length) return parts.join('; ')
  }

  if (detail && typeof detail === 'object') {
    const msg = (detail as any).msg ?? (detail as any).message
    if (typeof msg === 'string') return msg
  }

  if (typeof error?.message === 'string' && error.message) return error.message
  return fallback
}

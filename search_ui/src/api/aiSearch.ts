/** Wrappers de fetch para el AI Engine (a través del CDN server) */

function authHeaders(): HeadersInit {
  const token = localStorage.getItem('cdn_token') ?? ''
  return {
    'Content-Type':  'application/json',
    'Authorization': `Bearer ${token}`,
  }
}

/** Búsqueda JSON completa (sin streaming) — útil para pruebas */
export async function searchJSON(query: string) {
  const res = await fetch('/api/ai/search', {
    method:  'POST',
    headers: authHeaders(),
    body:    JSON.stringify({ query }),
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

/** Health check del AI Engine */
export async function getAIHealth() {
  const res = await fetch('/api/ai/health', {
    headers: { 'Authorization': `Bearer ${localStorage.getItem('cdn_token') ?? ''}` },
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

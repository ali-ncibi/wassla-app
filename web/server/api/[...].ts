export default defineEventHandler(async (event) => {
  const { apiBase } = useRuntimeConfig(event)
  const path = event.path.replace(/^\/api/, '') || '/'
  if (event.method !== 'GET' && event.method !== 'HEAD') {
    throw createError({ statusCode: 405, statusMessage: 'Read-only API proxy' })
  }

  if (path.startsWith('/ingest')) {
    throw createError({ statusCode: 404, statusMessage: 'Not found' })
  }

  const target = new URL(path, apiBase.endsWith('/') ? apiBase : apiBase + '/')
  const query = getQuery(event)
  for (const [k, v] of Object.entries(query)) {
    if (v !== undefined && v !== null) target.searchParams.set(k, String(v))
  }

  const headers: Record<string, string> = {}
  const contentType = getRequestHeader(event, 'content-type')
  if (contentType) headers['content-type'] = contentType
  try {
    const resp = await $fetch.raw(target.toString(), { method: event.method as 'GET', headers })

    return resp._data
  }
  catch (err: unknown) {
    const e = err as { response?: { status?: number, _data?: unknown }, message?: string }
    const detail = (e.response?._data as { detail?: string })?.detail ?? e.message ?? 'Upstream error'
    throw createError({ statusCode: e.response?.status ?? 502, statusMessage: String(detail) })
  }
})

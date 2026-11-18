import { beforeEach, describe, expect, it } from 'vitest'
import handler from '../server/api/[...].ts'
import { fetchMock, nitroMocks, resetNuxtMocks } from './setup'

interface FakeEvent {
  path: string
  method: string
  query?: Record<string, unknown>
  headers?: Record<string, string>
  body?: unknown
}

type Handler = (event: FakeEvent) => Promise<unknown>
const call = handler as unknown as Handler

describe('server/api/[...].ts read-only proxy', () => {
  beforeEach(() => {
    resetNuxtMocks()
    fetchMock.raw.mockResolvedValue({ _data: { ok: true } })
  })

  it('forwards GET requests with query params and returns the upstream body', async () => {
    const result = await call({ path: '/api/articles', method: 'GET', query: { lang: 'ar', skip: undefined, n: 3 } })
    expect(fetchMock.raw).toHaveBeenCalledTimes(1)
    const [url, opts] = fetchMock.raw.mock.calls[0] as [string, { method: string, headers: Record<string, string>, body: unknown }]
    expect(url).toBe('http://pipeline.test/articles?lang=ar&n=3')
    expect(opts.method).toBe('GET')
    expect(opts.headers).toEqual({})
    expect(opts.body).toBeUndefined()
    expect(result).toEqual({ ok: true })
  })

  it('maps /api alone to the upstream root', async () => {
    await call({ path: '/api', method: 'GET', query: {} })
    expect(fetchMock.raw.mock.calls[0]?.[0]).toBe('http://pipeline.test/')
  })

  it('drops null query params like undefined ones', async () => {
    await call({ path: '/api/articles', method: 'GET', query: { lang: 'en', skip: null, n: 2 } })
    expect(fetchMock.raw.mock.calls[0]?.[0]).toBe('http://pipeline.test/articles?lang=en&n=2')
  })

  it('does not double the slash when the api base already ends with one', async () => {
    nitroMocks.useRuntimeConfig.mockReturnValue({ apiBase: 'http://pipeline.test/' })
    await call({ path: '/api/articles', method: 'GET', query: {} })
    expect(fetchMock.raw.mock.calls[0]?.[0]).toBe('http://pipeline.test/articles')
  })

  it('forwards the content-type header but no body for HEAD', async () => {
    await call({ path: '/api/stats', method: 'HEAD', query: {}, headers: { 'content-type': 'application/json' } })
    const [, opts] = fetchMock.raw.mock.calls[0] as [string, { method: string, headers: Record<string, string>, body: unknown }]
    expect(opts.method).toBe('HEAD')
    expect(opts.headers).toEqual({ 'content-type': 'application/json' })
    expect(opts.body).toBeUndefined()
  })

  it('rejects non-GET/HEAD methods with 405', async () => {
    await expect(call({ path: '/api/articles', method: 'POST', query: {}, body: '{}' }))
      .rejects.toMatchObject({ statusCode: 405, statusMessage: 'Read-only API proxy' })
    expect(fetchMock.raw).not.toHaveBeenCalled()
  })

  it('blocks /ingest/* with 404 even for GET', async () => {
    await expect(call({ path: '/api/ingest/run', method: 'GET', query: {} }))
      .rejects.toMatchObject({ statusCode: 404, statusMessage: 'Not found' })
    expect(fetchMock.raw).not.toHaveBeenCalled()
  })

  it('maps upstream error responses to their status and detail', async () => {
    fetchMock.raw.mockRejectedValue({ response: { status: 400, _data: { detail: 'Unsupported language: de' } }, message: 'fail' })
    await expect(call({ path: '/api/articles', method: 'GET', query: { lang: 'de' } }))
      .rejects.toMatchObject({ statusCode: 400, statusMessage: 'Unsupported language: de' })
  })

  it('maps errors without an upstream response to 502', async () => {
    fetchMock.raw.mockRejectedValue(new Error('network down'))
    await expect(call({ path: '/api/stats', method: 'GET', query: {} }))
      .rejects.toMatchObject({ statusCode: 502, statusMessage: 'network down' })
  })

  it('falls back to the error message when the upstream body has no detail', async () => {
    fetchMock.raw.mockRejectedValue({ response: { status: 500, _data: {} }, message: 'boom' })
    await expect(call({ path: '/api/stats', method: 'GET', query: {} }))
      .rejects.toMatchObject({ statusCode: 500, statusMessage: 'boom' })
  })

  it('falls back to a generic message for non-Error rejections', async () => {
    fetchMock.raw.mockRejectedValue('plain failure')
    await expect(call({ path: '/api/stats', method: 'GET', query: {} }))
      .rejects.toMatchObject({ statusCode: 502, statusMessage: 'Upstream error' })
  })
})

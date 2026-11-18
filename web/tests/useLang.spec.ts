import { beforeEach, describe, expect, it } from 'vitest'
import { useLang } from '~/composables/useLang'
import { mockRoute, mockRouter, resetNuxtMocks } from './setup'

describe('useLang', () => {
  beforeEach(() => resetNuxtMocks())

  it('defaults to en when the query has no lang', () => {
    expect(useLang().lang.value).toBe('en')
  })

  it('reads a supported lang from the query', () => {
    mockRoute.query = { lang: 'ar' }
    expect(useLang().lang.value).toBe('ar')
  })

  it('falls back to en for an unsupported lang', () => {
    mockRoute.query = { lang: 'de' }
    expect(useLang().lang.value).toBe('en')
  })

  it('setLang pushes a new query preserving existing params', () => {
    mockRoute.query = { q: 'news', lang: 'fr' }
    const { setLang } = useLang()
    setLang('ar')
    expect(mockRouter.push).toHaveBeenCalledTimes(1)
    expect(mockRouter.push).toHaveBeenCalledWith({ query: { q: 'news', lang: 'ar' } })
  })
})

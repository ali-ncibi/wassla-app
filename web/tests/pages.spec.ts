import type { ArticlesResponse, ArticleDetail, CategoryCount, SearchResponse, StatsResponse } from '~/types/api'
import type { Component } from 'vue'
import { flushPromises, mount } from '@vue/test-utils'
import { Suspense, defineComponent, h, nextTick, ref } from 'vue'
import { afterEach, beforeEach, describe, expect, it } from 'vitest'
import ArticlePage from '~/pages/article/[id].vue'
import IndexPage from '~/pages/index.vue'
import SearchPage from '~/pages/search.vue'
import StatsPage from '~/pages/stats.vue'
import { allComponents, fetchMock, mockRoute, mockRouter, resetNuxtMocks, useFetchMock, useHeadMock } from './setup'

const categories: CategoryCount[] = [
  { name: 'world', count: 5 },
  { name: 'technology', count: 2 },
]

const articlesResponse: ArticlesResponse = {
  total: 2,
  items: [
    {
      id: 1, title: 'First story', summary: 'Summary one', category: 'world', source_name: 'BBC',
      url: 'http://example.com/1', published_at: '2026-01-02T10:00:00.000Z', scraped_at: '2026-01-02T11:00:00.000Z',
    },
    {
      id: 2, title: 'Second story', summary: null, category: 'technology', source_name: 'DW',
      url: 'http://example.com/2', published_at: null, scraped_at: '2026-01-01T11:00:00.000Z',
    },
  ],
}

const searchResponse: SearchResponse = {
  query: 'ukraine war',
  lang: 'en',
  answer: 'Grounded answer [1]',
  hits: [
    {
      article_id: 1, title: 'Hit one', summary: 's1', category: 'world', source_name: 'BBC',
      url: 'http://example.com/1', published_at: '2026-01-02T10:00:00.000Z', score: 0.9123,
    },
    {
      article_id: 2, title: 'Hit two', summary: null, category: null, source_name: 'DW',
      url: 'http://example.com/2', published_at: null, score: 0.5,
    },
  ],
}

const statsResponse: StatsResponse = {
  total_articles: 12,
  needs_review: 3,
  avg_eval_score: 7.26,
  last_scraped_at: '2026-01-03T10:00:00.000Z',
  by_category: [
    { name: 'world', count: 5 },
    { name: 'sports', count: 2 },
  ],
  by_language: [
    { name: 'en', count: 12 },
    { name: 'ar', count: 12 },
  ],
  per_day_target: 200,
}

const articleDetail: ArticleDetail = {
  id: 7,
  title: 'Deep dive',
  body: 'First paragraph\n\nSecond paragraph\nThird paragraph',
  summary: 'The summary',
  category: 'technology',
  lang: 'en',
  source_language: 'en',
  source_name: 'NPR',
  url: 'http://example.com/7',
  published_at: '2026-01-02T10:00:00.000Z',
  scraped_at: '2026-01-02T11:00:00.000Z',
  eval_score: 8,
  eval_verdict: 'pass',
  available_langs: ['en', 'fr', 'ar'],
}

const mounted: Array<{ unmount: () => void }> = []
function mountPage(page: Component) {
  const wrapper = defineComponent({
    name: 'PageWrapper',
    setup() {
      return () => h(Suspense, null, { default: () => h(page) })
    },
  })
  const w = mount(wrapper, { global: { components: allComponents } })
  mounted.push(w)

  return w
}

describe('pages', () => {
  beforeEach(() => resetNuxtMocks())
  afterEach(() => {
    while (mounted.length) mounted.pop()?.unmount()
  })

  describe('index.vue', () => {
    beforeEach(() => {
      useFetchMock.mockImplementation((url: string) => {
        if (url === '/api/articles') return { data: ref(articlesResponse) }
        if (url === '/api/categories') return { data: ref(categories) }
        throw new Error(`unexpected useFetch url: ${url}`)
      })
    })

    function articlesQuery(): Record<string, unknown> {
      const call = useFetchMock.mock.calls.find(([url]) => url === '/api/articles')
      const opts = call?.[1] as { query: { value: Record<string, unknown> } }

      return opts.query.value
    }

    it('fetches articles and categories and renders the grid and chips', async () => {
      const wrapper = mountPage(IndexPage)
      await flushPromises()
      expect(articlesQuery()).toMatchObject({ lang: 'en', limit: 30, offset: 0 })
      expect(wrapper.text()).toContain('Latest news')
      expect(wrapper.text()).toContain('2')
      const cards = wrapper.findAll('a[data-to]')
      expect(cards).toHaveLength(2)
      expect(cards[0]?.attributes('data-to')).toContain('/article/1')
      expect(wrapper.text()).toContain('First story')
      expect(wrapper.text()).toContain('Second story')
      const buttons = wrapper.findAll('button')
      expect(buttons).toHaveLength(3)
      expect(buttons[1]?.text()).toContain('world')
      expect(wrapper.find('nav[aria-label="Pagination"]').exists()).toBe(false)
    })

    it('derives the API offset from the page query param', async () => {
      mockRoute.query = { page: '3' }
      mountPage(IndexPage)
      await flushPromises()
      expect(articlesQuery()).toMatchObject({ limit: 30, offset: 60 })
    })

    it('passes the category filter to the API', async () => {
      mockRoute.query = { category: 'world' }
      mountPage(IndexPage)
      await flushPromises()
      expect(articlesQuery()).toMatchObject({ category: 'world', limit: 30, offset: 0 })
    })

    it('falls back to page 1 for invalid page params', async () => {
      for (const bad of ['0', '-2', 'abc', '2.5']) {
        resetNuxtMocks()
        useFetchMock.mockImplementation((url: string) => {
          if (url === '/api/articles') return { data: ref(articlesResponse) }

          return { data: ref(categories) }
        })
        mockRoute.query = { page: bad }
        mountPage(IndexPage)
        await flushPromises()
        expect(articlesQuery()).toMatchObject({ offset: 0 })
      }
    })

    it('shows zero total and the empty state when the fetch returns null', async () => {
      useFetchMock.mockImplementation((url: string) => {
        if (url === '/api/articles') return { data: ref(null) }

        return { data: ref(categories) }
      })
      const wrapper = mountPage(IndexPage)
      await flushPromises()
      expect(wrapper.text()).toContain('0')
      expect(wrapper.text()).toContain('Loading...')
      expect(wrapper.find('nav[aria-label="Pagination"]').exists()).toBe(false)
    })

    it('renders pagination when there are multiple pages and navigates on click', async () => {
      useFetchMock.mockImplementation((url: string) => {
        if (url === '/api/articles') return { data: ref({ ...articlesResponse, total: 65 }) }

        return { data: ref(categories) }
      })
      const wrapper = mountPage(IndexPage)
      await flushPromises()
      const nav = wrapper.find('nav[aria-label="Pagination"]')
      expect(nav.exists()).toBe(true)
      const buttons = nav.findAll('button')
      expect(buttons.map(b => b.text())).toEqual(['Previous', '1', '2', '3', 'Next'])
      await buttons[2]?.trigger('click')
      expect(mockRouter.push).toHaveBeenCalledWith({ query: { page: 2 } })
    })

    it('shows a loading placeholder when there are no articles', async () => {
      useFetchMock.mockImplementation((url: string) => {
        if (url === '/api/articles') return { data: ref({ total: 0, items: [] }) }

        return { data: ref(categories) }
      })
      const wrapper = mountPage(IndexPage)
      await flushPromises()
      expect(wrapper.text()).toContain('Loading...')
    })
  })

  describe('search.vue', () => {
    beforeEach(() => {
      fetchMock.mockResolvedValue(searchResponse)
    })

    it('submits the query and renders the AI answer and scored hits', async () => {
      mockRoute.query = { q: 'ukraine war' }
      const wrapper = mountPage(SearchPage)
      await flushPromises()
      await wrapper.find('form').trigger('submit')
      await flushPromises()
      expect(fetchMock).toHaveBeenCalledWith('/api/search', { query: { q: 'ukraine war', lang: 'en' } })
      const text = wrapper.text()
      expect(text).toContain('AI answer')
      expect(text).toContain('Grounded answer [1]')
      expect(text).toContain('Hit one')
      expect(text).toContain('0.912')
      expect(text).toContain('0.500')
    })

    it('re-runs the search when the language changes', async () => {
      mockRoute.query = { q: 'news' }
      const wrapper = mountPage(SearchPage)
      await flushPromises()
      await wrapper.find('form').trigger('submit')
      await flushPromises()
      const callsAfterSubmit = fetchMock.mock.calls.length
      expect(callsAfterSubmit).toBeGreaterThan(0)
      mockRoute.query = { q: 'news', lang: 'ar' }
      await nextTick()
      await flushPromises()
      expect(fetchMock.mock.calls.length).toBe(callsAfterSubmit + 1)
      expect(fetchMock).toHaveBeenLastCalledWith('/api/search', { query: { q: 'news', lang: 'ar' } })
    })

    it('shows the empty state when nothing clears the threshold', async () => {
      fetchMock.mockResolvedValue({ query: 'zzz', lang: 'en', answer: null, hits: [] })
      mockRoute.query = { q: 'zzz' }
      const wrapper = mountPage(SearchPage)
      await flushPromises()
      await wrapper.find('form').trigger('submit')
      await flushPromises()
      expect(wrapper.text()).toContain('No results above the similarity threshold')
      expect(wrapper.text()).not.toContain('AI answer')
    })

    it('does not submit an empty query', async () => {
      mockRoute.query = {}
      const wrapper = mountPage(SearchPage)
      await flushPromises()
      await wrapper.find('form').trigger('submit')
      await flushPromises()
      expect(fetchMock).not.toHaveBeenCalled()
    })

    it('does not re-run the search on language change before the first submit', async () => {
      mockRoute.query = {}
      mountPage(SearchPage)
      await flushPromises()
      mockRoute.query = { lang: 'ar' }
      await nextTick()
      await flushPromises()
      expect(fetchMock).not.toHaveBeenCalled()
    })

    it('submits the typed query', async () => {
      fetchMock.mockResolvedValue(searchResponse)
      mockRoute.query = {}
      const wrapper = mountPage(SearchPage)
      await flushPromises()
      await wrapper.find('input').setValue('typed query')
      await wrapper.find('form').trigger('submit')
      await flushPromises()
      expect(fetchMock).toHaveBeenCalledWith('/api/search', { query: { q: 'typed query', lang: 'en' } })
    })
  })

  describe('stats.vue', () => {
    beforeEach(() => {
      useFetchMock.mockImplementation((url: string) => {
        if (url === '/api/stats') return { data: ref(statsResponse) }
        throw new Error(`unexpected useFetch url: ${url}`)
      })
    })

    it('renders the KPI cards, category bars and language counts', async () => {
      const wrapper = mountPage(StatsPage)
      await flushPromises()
      const text = wrapper.text()
      expect(text).toContain('Pipeline')
      expect(text).toContain('12')
      expect(text).toContain('7.3')
      expect(text).toContain('3')
      expect(text).toContain('200')
      expect(text).toContain('Articles processed')
      expect(text).toContain('Needs review')
      expect(text).toContain('Last ingest')
      expect(text).toContain('world')
      expect(text).toContain('sports')
      expect(text).toContain('By category')
      expect(text).toContain('Translations by language')
      const bars = wrapper.findAll('.bg-brand-500')
      expect(bars).toHaveLength(2)
      expect(bars[0]?.attributes('style')).toContain('width: 100%')
      expect(bars[1]?.attributes('style')).toContain('width: 40%')
    })

    it('renders nothing while stats are loading', async () => {
      useFetchMock.mockImplementation(() => ({ data: ref(null) }))
      const wrapper = mountPage(StatsPage)
      await flushPromises()
      expect(wrapper.find('h1').exists()).toBe(false)
      const vm = wrapper.findComponent(StatsPage).vm as unknown as { maxCategory: number }
      expect(vm.maxCategory).toBe(1)
    })

    it('shows dashes for a missing avg score and missing last ingest date', async () => {
      useFetchMock.mockImplementation((url: string) => {
        if (url === '/api/stats') return { data: ref({ ...statsResponse, avg_eval_score: null, last_scraped_at: null }) }
        throw new Error(`unexpected useFetch url: ${url}`)
      })
      const wrapper = mountPage(StatsPage)
      await flushPromises()
      const text = wrapper.text()
      expect(text).toContain('Avg QA score')
      expect(text).toContain('—')
      expect(text).not.toContain('7.3')
    })

    it('shows a dash for an unparseable last ingest date', async () => {
      useFetchMock.mockImplementation((url: string) => {
        if (url === '/api/stats') return { data: ref({ ...statsResponse, last_scraped_at: 'not-a-date' }) }
        throw new Error(`unexpected useFetch url: ${url}`)
      })
      const wrapper = mountPage(StatsPage)
      await flushPromises()
      expect(wrapper.text()).toContain('Last ingest: —')
    })

    it('handles a missing category list', async () => {
      useFetchMock.mockImplementation((url: string) => {
        if (url === '/api/stats') return { data: ref({ ...statsResponse, by_category: undefined as unknown as CategoryCount[] }) }
        throw new Error(`unexpected useFetch url: ${url}`)
      })
      const wrapper = mountPage(StatsPage)
      await flushPromises()
      expect(wrapper.text()).toContain('By category')
      expect(wrapper.findAll('.bg-brand-500')).toHaveLength(0)
    })

    it('formats the last ingest date in the fr and ar locales', async () => {
      for (const lang of ['fr', 'ar']) {
        resetNuxtMocks()
        useFetchMock.mockImplementation((url: string) => {
          if (url === '/api/stats') return { data: ref(statsResponse) }
          throw new Error(`unexpected useFetch url: ${url}`)
        })
        mockRoute.query = { lang }
        const wrapper = mountPage(StatsPage)
        await flushPromises()
        expect(wrapper.find('h1').exists()).toBe(true)
        expect(wrapper.find('p.mb-8').text()).not.toContain('—')
      }
    })
  })

  describe('article/[id].vue', () => {
    beforeEach(() => {
      mockRoute.params = { id: '7' }
      useFetchMock.mockImplementation((url: string) => {
        if (url === '/api/articles/7') return { data: ref(articleDetail) }
        throw new Error(`unexpected useFetch url: ${url}`)
      })
    })

    it('fetches the article in the current lang and renders it', async () => {
      const wrapper = mountPage(ArticlePage)
      await flushPromises()
      expect(useFetchMock).toHaveBeenCalledWith('/api/articles/7', expect.objectContaining({ query: expect.objectContaining({ lang: expect.anything() }) }))
      const text = wrapper.text()
      expect(text).toContain('Deep dive')
      expect(text).toContain('The summary')
      expect(text).toContain('QA score 8.0/10')
      expect(text).toContain('NPR')
      expect(text).toContain('technology')
      const paragraphs = wrapper.findAll('article .space-y-4 p')
      expect(paragraphs.map(p => p.text())).toEqual(['First paragraph', 'Second paragraph', 'Third paragraph'])
      const original = wrapper.find('a[href="http://example.com/7"]')
      expect(original.exists()).toBe(true)
      expect(original.text()).toContain('Read original')
    })

    it('shows the loading placeholder without data', async () => {
      useFetchMock.mockImplementation(() => ({ data: ref(null) }))
      const wrapper = mountPage(ArticlePage)
      await flushPromises()
      expect(wrapper.text()).toContain('Loading...')
    })

    it('uses an empty article title in useHead while loading', async () => {
      useFetchMock.mockImplementation(() => ({ data: ref(null) }))
      mountPage(ArticlePage)
      await flushPromises()
      const head = useHeadMock.mock.calls[0]?.[0] as { title: () => string }
      expect(head.title()).toBe('Wassla — ')
    })

    it('renders fallbacks for null category, summary, QA score and date', async () => {
      useFetchMock.mockImplementation((url: string) => {
        if (url === '/api/articles/7') {
          return { data: ref({ ...articleDetail, category: null, summary: null, eval_score: null, published_at: null }) }
        }

        throw new Error(`unexpected useFetch url: ${url}`)
      })
      const wrapper = mountPage(ArticlePage)
      await flushPromises()
      const text = wrapper.text()
      expect(text).toContain('—')
      expect(text).not.toContain('QA score')
      expect(text).not.toContain('The summary')
    })

    it('renders an empty date for an unparseable published date', async () => {
      useFetchMock.mockImplementation((url: string) => {
        if (url === '/api/articles/7') return { data: ref({ ...articleDetail, published_at: 'not-a-date' }) }
        throw new Error(`unexpected useFetch url: ${url}`)
      })
      const wrapper = mountPage(ArticlePage)
      await flushPromises()
      expect(wrapper.find('article .mb-4 span.text-slate-400').text()).toBe('')
    })

    it('renders no paragraphs when the body is null', async () => {
      useFetchMock.mockImplementation((url: string) => {
        if (url === '/api/articles/7') return { data: ref({ ...articleDetail, body: null as unknown as string }) }
        throw new Error(`unexpected useFetch url: ${url}`)
      })
      const wrapper = mountPage(ArticlePage)
      await flushPromises()
      expect(wrapper.findAll('article .space-y-4 p')).toHaveLength(0)
    })

    it('formats the published date in the fr and ar locales', async () => {
      for (const lang of ['fr', 'ar']) {
        resetNuxtMocks()
        mockRoute.params = { id: '7' }
        useFetchMock.mockImplementation((url: string) => {
          if (url === '/api/articles/7') return { data: ref(articleDetail) }
          throw new Error(`unexpected useFetch url: ${url}`)
        })
        mockRoute.query = { lang }
        const wrapper = mountPage(ArticlePage)
        await flushPromises()
        expect(wrapper.find('article .mb-4 span.text-slate-400').text()).not.toBe('')
      }
    })
  })
})

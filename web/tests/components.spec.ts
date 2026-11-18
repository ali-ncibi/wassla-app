import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'
import ArticleCard from '~/components/ArticleCard.vue'
import CategoryChips from '~/components/CategoryChips.vue'
import LangSwitcher from '~/components/LangSwitcher.vue'
import Pagination from '~/components/Pagination.vue'
import SiteHeader from '~/components/SiteHeader.vue'
import type { ArticleCardItem } from '~/types/api'
import { allComponents, mockRoute, mockRouter, resetNuxtMocks } from './setup'

const article: ArticleCardItem = {
  id: 1,
  title: 'Hello world',
  summary: 'A short summary',
  category: 'world',
  source_name: 'BBC',
  url: 'http://example.com/a',
  published_at: '2026-01-01T10:00:00.000Z',
  scraped_at: '2026-01-01T11:00:00.000Z',
}

describe('ArticleCard', () => {
  beforeEach(() => resetNuxtMocks())

  it('renders category, source, date, title and summary', () => {
    const wrapper = mount(ArticleCard, { props: { article }, global: { components: allComponents } })
    const text = wrapper.text()
    expect(text).toContain('world')
    expect(text).toContain('BBC')
    expect(text).toContain('Hello world')
    expect(text).toContain('A short summary')
    expect(wrapper.find('h3').text()).toBe('Hello world')
  })

  it('links to the article page carrying the current lang', () => {
    mockRoute.query = { lang: 'fr' }
    const wrapper = mount(ArticleCard, { props: { article }, global: { components: allComponents } })
    const to = JSON.parse(wrapper.find('a').attributes('data-to') ?? '{}') as { path: string, query: { lang: string } }
    expect(to.path).toBe('/article/1')
    expect(to.query.lang).toBe('fr')
  })

  it('omits the summary paragraph when there is none and shows a dash for missing category', () => {
    const wrapper = mount(ArticleCard, {
      props: { article: { ...article, summary: null, category: null } },
      global: { components: allComponents },
    })
    expect(wrapper.text()).not.toContain('A short summary')
    expect(wrapper.text()).toContain('—')
  })
})

describe('CategoryChips', () => {
  beforeEach(() => resetNuxtMocks())

  const categories = [
    { name: 'world', count: 4 },
    { name: 'sports', count: 2 },
  ]

  it('renders All plus one chip per category with counts', () => {
    const wrapper = mount(CategoryChips, { props: { categories }, global: { components: allComponents } })
    const buttons = wrapper.findAll('button')
    expect(buttons).toHaveLength(3)
    expect(buttons[0]?.text()).toContain('All')
    expect(buttons[1]?.text()).toContain('world')
    expect(buttons[1]?.text()).toContain('4')
    expect(buttons[2]?.text()).toContain('sports')
  })

  it('selecting a category pushes the category query param', async () => {
    const wrapper = mount(CategoryChips, { props: { categories }, global: { components: allComponents } })
    await wrapper.findAll('button')[1]?.trigger('click')
    expect(mockRouter.push).toHaveBeenCalledWith({ query: { category: 'world' } })
  })

  it('selecting All clears the category param', async () => {
    mockRoute.query = { category: 'world', lang: 'en' }
    const wrapper = mount(CategoryChips, { props: { categories }, global: { components: allComponents } })
    await wrapper.findAll('button')[0]?.trigger('click')
    expect(mockRouter.push).toHaveBeenCalledWith({ query: { category: undefined, lang: 'en' } })
  })

  it('resets the page param when the category changes', async () => {
    mockRoute.query = { page: '3' }
    const wrapper = mount(CategoryChips, { props: { categories }, global: { components: allComponents } })
    await wrapper.findAll('button')[2]?.trigger('click')
    expect(mockRouter.push).toHaveBeenCalledWith({ query: { category: 'sports', page: undefined } })
  })

  it('marks the active category from the current query', () => {
    mockRoute.query = { category: 'sports' }
    const wrapper = mount(CategoryChips, { props: { categories }, global: { components: allComponents } })
    const buttons = wrapper.findAll('button')
    expect(buttons[2]?.classes()).toContain('bg-brand-600')
    expect(buttons[0]?.classes()).not.toContain('bg-brand-600')
  })
})

describe('Pagination', () => {
  beforeEach(() => resetNuxtMocks())

  it('renders all page numbers and marks the current page', () => {
    const wrapper = mount(Pagination, { props: { page: 2, totalPages: 4 }, global: { components: allComponents } })
    const buttons = wrapper.findAll('button')
    expect(buttons.map(b => b.text())).toEqual(['Previous', '1', '2', '3', '4', 'Next'])
    expect(buttons[2]?.attributes('aria-current')).toBe('page')
    expect(buttons[1]?.attributes('aria-current')).toBeUndefined()
  })

  it('windows the page numbers with ellipses when there are many pages', () => {
    const wrapper = mount(Pagination, { props: { page: 10, totalPages: 20 }, global: { components: allComponents } })
    const labels = wrapper.findAll('button').map(b => b.text())
    expect(labels).toEqual(['Previous', '1', '9', '10', '11', '20', 'Next'])
    expect(wrapper.text()).toContain('…')
  })

  it('disables previous on the first page and next on the last page', () => {
    const first = mount(Pagination, { props: { page: 1, totalPages: 5 }, global: { components: allComponents } })
    const firstButtons = first.findAll('button')
    expect(firstButtons[0]?.attributes('disabled')).toBeDefined()
    expect(firstButtons[firstButtons.length - 1]?.attributes('disabled')).toBeUndefined()
    first.unmount()
    const last = mount(Pagination, { props: { page: 5, totalPages: 5 }, global: { components: allComponents } })
    const lastButtons = last.findAll('button')
    expect(lastButtons[0]?.attributes('disabled')).toBeUndefined()
    expect(lastButtons[lastButtons.length - 1]?.attributes('disabled')).toBeDefined()
  })

  it('pushes the page query param and omits it for page 1', async () => {
    mockRoute.query = { lang: 'en' }
    const wrapper = mount(Pagination, { props: { page: 3, totalPages: 5 }, global: { components: allComponents } })
    const buttons = wrapper.findAll('button')
    await buttons[2]?.trigger('click')
    expect(mockRouter.push).toHaveBeenCalledWith({ query: { lang: 'en', page: 2 } })
    await buttons[1]?.trigger('click')
    expect(mockRouter.push).toHaveBeenCalledWith({ query: { lang: 'en', page: undefined } })
  })

  it('does not render anything when there is a single page', () => {
    const wrapper = mount(Pagination, { props: { page: 1, totalPages: 1 }, global: { components: allComponents } })
    expect(wrapper.find('nav').exists()).toBe(false)
  })

  it('ignores clicks on the current page', async () => {
    const wrapper = mount(Pagination, { props: { page: 2, totalPages: 4 }, global: { components: allComponents } })
    await wrapper.findAll('button')[2]?.trigger('click')
    expect(mockRouter.push).not.toHaveBeenCalled()
  })

  it('navigates with the previous and next buttons', async () => {
    const wrapper = mount(Pagination, { props: { page: 2, totalPages: 4 }, global: { components: allComponents } })
    const buttons = wrapper.findAll('button')
    await buttons[0]?.trigger('click')
    expect(mockRouter.push).toHaveBeenCalledWith({ query: { page: undefined } })
    await buttons[buttons.length - 1]?.trigger('click')
    expect(mockRouter.push).toHaveBeenCalledWith({ query: { page: 3 } })
  })
})

describe('LangSwitcher', () => {
  beforeEach(() => resetNuxtMocks())

  it('renders EN/FR/AR and highlights the active language', () => {
    mockRoute.query = { lang: 'fr' }
    const wrapper = mount(LangSwitcher, { global: { components: allComponents } })
    const buttons = wrapper.findAll('button')
    expect(buttons.map(b => b.text())).toEqual(['EN', 'FR', 'AR'])
    expect(buttons[1]?.classes()).toContain('bg-brand-500')
    expect(buttons[0]?.classes()).not.toContain('bg-brand-500')
  })

  it('switches language via router push', async () => {
    mockRoute.query = { lang: 'en', q: 'x' }
    const wrapper = mount(LangSwitcher, { global: { components: allComponents } })
    await wrapper.findAll('button')[2]?.trigger('click')
    expect(mockRouter.push).toHaveBeenCalledWith({ query: { lang: 'ar', q: 'x' } })
  })
})

describe('SiteHeader', () => {
  beforeEach(() => resetNuxtMocks())

  it('renders the brand, tagline and three nav links carrying the lang', () => {
    mockRoute.query = { lang: 'ar' }
    const wrapper = mount(SiteHeader, { global: { components: allComponents } })
    expect(wrapper.text()).toContain('Wassla')
    expect(wrapper.text()).toContain('أخبار بالذكاء الاصطناعي بلغات متعددة')
    const links = wrapper.findAll('nav a')
    expect(links).toHaveLength(3)
    const paths = links.map(l => (JSON.parse(l.attributes('data-to') ?? '{}') as { path: string }).path)
    expect(paths).toEqual(['/', '/search', '/stats'])
    for (const l of links) {
      expect(l.attributes('data-to')).toContain('"lang":"ar"')
    }
  })

  it('marks the nav link of the current route as active', () => {
    mockRoute.path = '/search'
    const wrapper = mount(SiteHeader, { global: { components: allComponents } })
    const links = wrapper.findAll('nav a')
    expect(links[0]?.classes()).not.toContain('bg-white/15')
    expect(links[1]?.classes()).toContain('bg-white/15')
    expect(links[2]?.classes()).not.toContain('bg-white/15')
  })
})

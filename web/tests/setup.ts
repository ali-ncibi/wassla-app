import type { Component } from 'vue'
import { computed, defineComponent, h, reactive, ref, watch } from 'vue'
import { vi } from 'vitest'
import ArticleCard from '~/components/ArticleCard.vue'
import CategoryChips from '~/components/CategoryChips.vue'
import LangSwitcher from '~/components/LangSwitcher.vue'
import Pagination from '~/components/Pagination.vue'
import SiteHeader from '~/components/SiteHeader.vue'

vi.stubGlobal('ref', ref)
vi.stubGlobal('computed', computed)
vi.stubGlobal('watch', watch)
vi.stubGlobal('defineComponent', defineComponent)

export const mockRoute = reactive({
  path: '/',
  query: {} as Record<string, string>,
  params: {} as Record<string, string>,
})
export const mockRouter = { push: vi.fn() }

export const useHeadMock = vi.fn()
export const useFetchMock = vi.fn()
export const fetchMock = Object.assign(vi.fn(), { raw: vi.fn() })

vi.stubGlobal('useRoute', () => mockRoute)
vi.stubGlobal('useRouter', () => mockRouter)
vi.stubGlobal('useHead', useHeadMock)
vi.stubGlobal('useFetch', useFetchMock)
vi.stubGlobal('$fetch', fetchMock)

export const nitroMocks = {
  defineEventHandler: vi.fn((fn: unknown) => fn),
  useRuntimeConfig: vi.fn(() => ({ apiBase: 'http://pipeline.test' })),
  getQuery: vi.fn((event: { query?: Record<string, unknown> }) => event.query ?? {}),
  getRequestHeader: vi.fn((event: { headers?: Record<string, string> }, name: string) => event.headers?.[name]),
  readRawBody: vi.fn(async (event: { body?: unknown }) => event.body),
  createError: vi.fn((opts: { statusCode: number, statusMessage: string }) =>
    Object.assign(new Error(opts.statusMessage), opts)),
}
vi.stubGlobal('defineEventHandler', nitroMocks.defineEventHandler)
vi.stubGlobal('useRuntimeConfig', nitroMocks.useRuntimeConfig)
vi.stubGlobal('getQuery', nitroMocks.getQuery)
vi.stubGlobal('getRequestHeader', nitroMocks.getRequestHeader)
vi.stubGlobal('readRawBody', nitroMocks.readRawBody)
vi.stubGlobal('createError', nitroMocks.createError)

const NuxtLinkStub = defineComponent({
  name: 'NuxtLink',
  props: { to: { type: [String, Object], required: true } },
  setup(props, { slots }) {
    return () => h('a', { 'data-to': JSON.stringify(props.to) }, slots.default?.())
  },
})
const renderSlot = defineComponent({
  setup(_, { slots }) {
    return () => h('div', slots.default?.())
  },
})
export const nuxtComponentStubs: Record<string, Component> = {
  NuxtLink: NuxtLinkStub,
  NuxtPage: renderSlot,
  NuxtLayout: renderSlot,
}

export const allComponents: Record<string, Component> = {
  ...nuxtComponentStubs,
  ArticleCard,
  CategoryChips,
  LangSwitcher,
  Pagination,
  SiteHeader,
}

export function resetNuxtMocks(): void {
  mockRoute.path = '/'
  mockRoute.query = {}
  mockRoute.params = {}
  mockRouter.push.mockReset()
  useHeadMock.mockReset()
  useFetchMock.mockReset()
  fetchMock.mockReset()
  fetchMock.raw.mockReset()
  for (const mock of Object.values(nitroMocks)) mock.mockReset()
  nitroMocks.useRuntimeConfig.mockReturnValue({ apiBase: 'http://pipeline.test' })
  nitroMocks.getQuery.mockImplementation((event: { query?: Record<string, unknown> }) => event.query ?? {})
  nitroMocks.getRequestHeader.mockImplementation((event: { headers?: Record<string, string> }, name: string) => event.headers?.[name])
  nitroMocks.readRawBody.mockImplementation(async (event: { body?: unknown }) => event.body)
  nitroMocks.createError.mockImplementation((opts: { statusCode: number, statusMessage: string }) =>
    Object.assign(new Error(opts.statusMessage), opts))
}

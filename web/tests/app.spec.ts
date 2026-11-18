import { mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it } from 'vitest'
import App from '~/app.vue'
import DefaultLayout from '~/layouts/default.vue'
import { allComponents, mockRoute, resetNuxtMocks, useHeadMock } from './setup'

describe('app.vue', () => {
  beforeEach(() => resetNuxtMocks())

  it('renders the layout wrapping the page', () => {
    const wrapper = mount(App, { global: { components: allComponents } })
    expect(wrapper.findAll('div')).toHaveLength(2)
  })
})

describe('layouts/default.vue', () => {
  beforeEach(() => resetNuxtMocks())

  function headAttrs(): { htmlAttrs: { lang: () => string, dir: () => string } } {
    return useHeadMock.mock.calls[0]?.[0] as { htmlAttrs: { lang: () => string, dir: () => string } }
  }

  it('renders header, slot and footer', () => {
    const wrapper = mount(DefaultLayout, {
      slots: { default: '<p>page content</p>' },
      global: { components: allComponents },
    })
    expect(wrapper.text()).toContain('page content')
    expect(wrapper.text()).toContain('Wassla — AI-powered multilingual news')
    expect(wrapper.find('header').exists()).toBe(true)
    expect(wrapper.find('main').exists()).toBe(true)
    expect(wrapper.find('footer').exists()).toBe(true)
  })

  it('sets html lang and rtl dir for arabic', () => {
    mockRoute.query = { lang: 'ar' }
    mount(DefaultLayout, { slots: { default: '<p>x</p>' }, global: { components: allComponents } })
    expect(headAttrs().htmlAttrs.lang()).toBe('ar')
    expect(headAttrs().htmlAttrs.dir()).toBe('rtl')
  })

  it('sets html lang and ltr dir for other languages', () => {
    mockRoute.query = { lang: 'fr' }
    mount(DefaultLayout, { slots: { default: '<p>x</p>' }, global: { components: allComponents } })
    expect(headAttrs().htmlAttrs.lang()).toBe('fr')
    expect(headAttrs().htmlAttrs.dir()).toBe('ltr')
  })
})

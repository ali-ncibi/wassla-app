import { describe, expect, it } from 'vitest'
import { langLabels, langs, t, ui } from '~/utils/i18n'

describe('i18n', () => {
  it('supports exactly en, fr and ar', () => {
    expect(langs).toEqual(['en', 'fr', 'ar'])
  })

  it('has a label for every supported language', () => {
    for (const lang of langs) {
      expect(langLabels[lang]).toBeTruthy()
    }

    expect(Object.keys(langLabels).sort()).toEqual([...langs].sort())
  })

  it('gives every language the same UI keys as english', () => {
    const enKeys = Object.keys(ui.en).sort()
    expect(enKeys.length).toBeGreaterThan(10)
    for (const lang of langs) {
      expect(Object.keys(ui[lang]).sort()).toEqual(enKeys)
    }
  })

  it('translates known keys in each language', () => {
    expect(t('en', 'home')).toBe('Home')
    expect(t('fr', 'home')).toBe('Accueil')
    expect(t('ar', 'home')).toBe('الرئيسية')
  })

  it('falls back to the key itself for unknown keys', () => {
    expect(t('en', 'no-such-key')).toBe('no-such-key')
    expect(t('fr', 'no-such-key')).toBe('no-such-key')
  })
})

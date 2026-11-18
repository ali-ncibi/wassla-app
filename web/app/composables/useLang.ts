import type { Lang } from '~/utils/i18n'
import { langs } from '~/utils/i18n'

export function useLang() {
  const route = useRoute()
  const router = useRouter()
  const lang = computed<Lang>(() => {
    const q = route.query.lang

    return langs.includes(q as Lang) ? (q as Lang) : 'en'
  })
  function setLang(l: Lang) {
    router.push({ query: { ...route.query, lang: l } })
  }

  return { lang, setLang }
}

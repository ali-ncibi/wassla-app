<script setup lang="ts">
import { t } from '~/utils/i18n'
import { useLang } from '~/composables/useLang'

const props = defineProps<{ page: number, totalPages: number }>()

const { lang } = useLang()
const route = useRoute()
const router = useRouter()

const pages = computed<(number | '…')[]>(() => {
  const total = props.totalPages
  if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
  const wanted = new Set(
    [1, total, props.page - 1, props.page, props.page + 1].filter(p => p >= 1 && p <= total),
  )
  const sorted = [...wanted].sort((a, b) => a - b)
  const out: (number | '…')[] = []
  let prev = 0
  for (const p of sorted) {
    if (p - prev > 1) out.push('…')
    out.push(p)
    prev = p
  }

  return out
})

function go(p: number) {
  if (p === props.page) return
  router.push({ query: { ...route.query, page: p === 1 ? undefined : p } })
  window.scrollTo({ top: 0, behavior: 'smooth' })
}
</script>

<template>
  <nav
    v-if="totalPages > 1"
    class="flex flex-wrap items-center justify-center gap-1.5"
    aria-label="Pagination"
  >
    <button
      type="button"
      class="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-semibold text-slate-600 transition-colors hover:border-brand-400 disabled:cursor-not-allowed disabled:opacity-40"
      :disabled="page === 1"
      :aria-label="t(lang, 'previous')"
      @click="go(page - 1)"
    >
      {{ t(lang, 'previous') }}
    </button>
    <template
      v-for="(p, i) in pages"
      :key="i"
    >
      <span
        v-if="p === '…'"
        class="px-1 text-sm text-slate-400"
      >…</span>
      <button
        v-else
        type="button"
        class="rounded-lg border px-3 py-1.5 text-sm font-semibold transition-colors"
        :class="p === page ? 'border-brand-600 bg-brand-600 text-white' : 'border-slate-300 bg-white text-slate-600 hover:border-brand-400'"
        :aria-current="p === page ? 'page' : undefined"
        @click="go(p)"
      >
        {{ p }}
      </button>
    </template>
    <button
      type="button"
      class="rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-semibold text-slate-600 transition-colors hover:border-brand-400 disabled:cursor-not-allowed disabled:opacity-40"
      :disabled="page === totalPages"
      :aria-label="t(lang, 'next')"
      @click="go(page + 1)"
    >
      {{ t(lang, 'next') }}
    </button>
  </nav>
</template>

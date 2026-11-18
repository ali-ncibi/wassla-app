<script setup lang="ts">
import { t } from '~/utils/i18n'
import { useLang } from '~/composables/useLang'
import type { SearchResponse } from '~/types/api'

const { lang } = useLang()
const route = useRoute()

const q = ref((route.query.q as string) || '')
const submitted = ref((route.query.q as string) || '')
const results = ref<SearchResponse | null>(null)
const pending = ref(false)

async function submit() {
  if (!q.value.trim()) return
  pending.value = true
  submitted.value = q.value.trim()
  results.value = await $fetch<SearchResponse>('/api/search', { query: { q: submitted.value, lang: lang.value } })
  pending.value = false
}

watch(lang, () => {
  if (submitted.value) submit()
})

useHead({ title: 'Wassla — ' + t(lang.value, 'search') })
</script>

<template>
  <div class="mx-auto max-w-5xl">
    <h1 class="mb-1 text-2xl font-extrabold tracking-tight">
      {{ t(lang, 'search') }}
    </h1>
    <p class="mb-5 text-sm text-slate-400">
      {{ t(lang, 'searchHint') }}
    </p>

    <form
      class="mb-8 flex gap-2"
      @submit.prevent="submit"
    >
      <input
        v-model="q"
        type="search"
        :placeholder="t(lang, 'searchPlaceholder')"
        class="flex-1 rounded-xl border border-slate-300 bg-white px-4 py-2.5 text-sm outline-none focus:border-brand-500 focus:ring-2 focus:ring-brand-200"
      >
      <button
        type="submit"
        class="rounded-xl bg-brand-600 px-5 py-2.5 text-sm font-semibold text-white transition-colors hover:bg-brand-700 disabled:opacity-50"
        :disabled="pending"
      >
        {{ pending ? t(lang, 'loading') : t(lang, 'search') }}
      </button>
    </form>

    <div
      v-if="pending"
      class="text-sm text-slate-400"
    >
      {{ t(lang, 'loading') }}
    </div>

    <template v-if="results">
      <div
        v-if="results.answer"
        class="mb-8 rounded-xl border border-brand-200 bg-brand-50 p-5"
      >
        <h2 class="mb-2 text-xs font-bold uppercase tracking-wide text-brand-700">
          {{ t(lang, 'aiAnswer') }}
        </h2>
        <p class="whitespace-pre-line text-sm leading-relaxed text-slate-800">
          {{ results.answer }}
        </p>
      </div>

      <h2 class="mb-3 text-xs font-bold uppercase tracking-wide text-slate-400">
        {{ t(lang, 'sources') }}
      </h2>
      <div
        v-if="results.hits.length"
        class="space-y-3"
      >
        <NuxtLink
          v-for="hit in results.hits"
          :key="hit.article_id"
          :to="{ path: `/article/${hit.article_id}`, query: { lang } }"
          class="block rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition-shadow hover:shadow-md"
        >
          <div class="mb-1 flex items-center gap-2 text-xs">
            <span class="rounded-full bg-brand-100 px-2 py-0.5 font-semibold text-brand-800 capitalize">{{ hit.category ?? '—' }}</span>
            <span class="text-slate-400">{{ hit.source_name }}</span>
            <span class="ms-auto font-mono text-emerald-600">{{ hit.score.toFixed(3) }}</span>
          </div>
          <h3 class="text-sm font-bold leading-snug">{{ hit.title }}</h3>
          <p
            v-if="hit.summary"
            class="mt-1 line-clamp-2 text-xs text-slate-600"
          >{{ hit.summary }}</p>
        </NuxtLink>
      </div>
      <p
        v-else
        class="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-400"
      >
        {{ t(lang, 'noResults') }}
      </p>
    </template>
  </div>
</template>

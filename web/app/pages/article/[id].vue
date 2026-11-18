<script setup lang="ts">
import { t } from '~/utils/i18n'
import { useLang } from '~/composables/useLang'
import type { ArticleDetail } from '~/types/api'

const route = useRoute()
const { lang } = useLang()

const { data: article } = await useFetch<ArticleDetail>(`/api/articles/${route.params.id}`, {
  query: { lang },
})

useHead({ title: () => `Wassla — ${article.value?.title ?? ''}` })

const paragraphs = computed(() =>
  (article.value?.body ?? '').split(/\n+/).map(p => p.trim()).filter(Boolean),
)

function formatDate(value: string | null): string {
  const d = value ? new Date(value) : null
  if (!d || Number.isNaN(d.getTime())) return ''

  return d.toLocaleString(lang.value === 'ar' ? 'ar' : lang.value === 'fr' ? 'fr-FR' : 'en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<template>
  <article
    v-if="article"
    class="mx-auto max-w-5xl"
  >
    <div class="mb-4 flex flex-wrap items-center gap-2 text-xs">
      <span class="rounded-full bg-brand-100 px-2.5 py-1 font-semibold text-brand-800 capitalize">
        {{ article.category ?? '—' }}
      </span>
      <span class="text-slate-500">{{ article.source_name }}</span>
      <span class="text-slate-400">{{ formatDate(article.published_at) }}</span>
      <span
        v-if="article.eval_score !== null"
        class="rounded-full bg-emerald-100 px-2.5 py-1 font-semibold text-emerald-700"
      >
        {{ t(lang, 'qaScore') }} {{ article.eval_score.toFixed(1) }}/10
      </span>
      <LangSwitcher class="ms-auto border-slate-300! [&_button]:text-slate-600!" />
    </div>

    <h1 class="mb-4 text-3xl font-extrabold leading-tight">
      {{ article.title }}
    </h1>

    <div
      v-if="article.summary"
      class="mb-6 rounded-xl border-s-4 border-brand-500 bg-brand-50 p-4"
    >
      <h2 class="mb-1 text-xs font-bold uppercase tracking-wide text-brand-700">
        {{ t(lang, 'summary') }}
      </h2>
      <p class="text-sm leading-relaxed text-slate-700">
        {{ article.summary }}
      </p>
    </div>

    <div class="space-y-4 text-[1.05rem] leading-relaxed text-slate-800">
      <p
        v-for="(p, i) in paragraphs"
        :key="i"
      >
        {{ p }}
      </p>
    </div>

    <div class="mt-8 border-t border-slate-200 pt-4">
      <a
        :href="article.url"
        target="_blank"
        rel="noopener"
        class="text-sm font-semibold text-brand-700 hover:underline"
      >
        {{ t(lang, 'readOriginal') }} ↗
      </a>
    </div>
  </article>
  <p
    v-else
    class="p-10 text-center text-slate-400"
  >
    {{ t(lang, 'loading') }}
  </p>
</template>

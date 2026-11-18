<script setup lang="ts">
import { useLang } from '~/composables/useLang'
import type { ArticleCardItem } from '~/types/api'

defineProps<{ article: ArticleCardItem }>()

const { lang } = useLang()

function formatDate(value: string | null): string {
  const d = value ? new Date(value) : null
  if (!d || Number.isNaN(d.getTime())) return ''

  return d.toLocaleString(lang.value === 'ar' ? 'ar' : lang.value === 'fr' ? 'fr-FR' : 'en-GB', {
    day: 'numeric',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<template>
  <NuxtLink
    :to="{ path: `/article/${article.id}`, query: { lang } }"
    class="group flex flex-col rounded-xl border border-slate-200 bg-white p-4 shadow-sm transition-shadow hover:shadow-md"
  >
    <div class="mb-2 flex items-center gap-2 text-xs">
      <span class="rounded-full bg-brand-100 px-2 py-0.5 font-semibold text-brand-800 capitalize">
        {{ article.category ?? '—' }}
      </span>
      <span class="text-slate-400">{{ article.source_name }}</span>
      <span class="ms-auto text-slate-400">{{ formatDate(article.published_at) }}</span>
    </div>
    <h3 class="mb-1 text-base font-bold leading-snug group-hover:text-brand-700">{{ article.title }}</h3>
    <p
      v-if="article.summary"
      class="line-clamp-3 text-sm text-slate-600"
    >{{ article.summary }}</p>
  </NuxtLink>
</template>

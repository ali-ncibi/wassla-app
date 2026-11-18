<script setup lang="ts">
import { t } from '~/utils/i18n'
import { useLang } from '~/composables/useLang'
import type { StatsResponse } from '~/types/api'

const { lang } = useLang()
const { data: stats } = await useFetch<StatsResponse>('/api/stats')

useHead({ title: 'Wassla — ' + t(lang.value, 'stats') })

function formatDate(value: string | null): string {
  const d = value ? new Date(value) : null
  if (!d || Number.isNaN(d.getTime())) return '—'

  return d.toLocaleString(lang.value === 'ar' ? 'ar' : lang.value === 'fr' ? 'fr-FR' : 'en-GB')
}

const maxCategory = computed(() => {
  const counts = stats.value?.by_category ?? []

  return Math.max(1, ...counts.map(c => c.count))
})
</script>

<template>
  <div
    v-if="stats"
    class="mx-auto max-w-5xl"
  >
    <h1 class="mb-5 text-2xl font-extrabold tracking-tight">
      {{ t(lang, 'stats') }}
    </h1>

    <div class="mb-8 grid grid-cols-2 gap-3 sm:grid-cols-4">
      <div class="rounded-xl border border-slate-200 bg-white p-4">
        <div class="text-2xl font-extrabold text-brand-700">
          {{ stats.total_articles }}
        </div>
        <div class="text-xs text-slate-400">
          {{ t(lang, 'totalArticles') }}
        </div>
      </div>
      <div class="rounded-xl border border-slate-200 bg-white p-4">
        <div class="text-2xl font-extrabold text-emerald-600">
          {{ stats.avg_eval_score?.toFixed(1) ?? '—' }}
        </div>
        <div class="text-xs text-slate-400">
          {{ t(lang, 'avgQa') }}
        </div>
      </div>
      <div class="rounded-xl border border-slate-200 bg-white p-4">
        <div class="text-2xl font-extrabold text-amber-500">
          {{ stats.needs_review }}
        </div>
        <div class="text-xs text-slate-400">
          {{ t(lang, 'needsReview') }}
        </div>
      </div>
      <div class="rounded-xl border border-slate-200 bg-white p-4">
        <div class="text-2xl font-extrabold text-slate-700">
          {{ stats.per_day_target }}
        </div>
        <div class="text-xs text-slate-400">
          {{ t(lang, 'perDayTarget') }}
        </div>
      </div>
    </div>

    <p class="mb-8 text-xs text-slate-400">
      {{ t(lang, 'lastIngest') }}: {{ formatDate(stats.last_scraped_at) }}
    </p>

    <div class="mb-8 rounded-xl border border-slate-200 bg-white p-5">
      <h2 class="mb-4 text-xs font-bold uppercase tracking-wide text-slate-400">
        {{ t(lang, 'byCategory') }}
      </h2>
      <div class="space-y-2">
        <div
          v-for="c in stats.by_category"
          :key="c.name"
          class="flex items-center gap-3 text-sm"
        >
          <span class="w-28 shrink-0 capitalize text-slate-600">{{ c.name }}</span>
          <div class="h-2.5 flex-1 rounded-full bg-slate-100">
            <div
              class="h-2.5 rounded-full bg-brand-500"
              :style="{ width: `${(c.count / maxCategory) * 100}%` }"
            />
          </div>
          <span class="w-8 text-end text-xs text-slate-400">{{ c.count }}</span>
        </div>
      </div>
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-5">
      <h2 class="mb-4 text-xs font-bold uppercase tracking-wide text-slate-400">
        {{ t(lang, 'byLanguage') }}
      </h2>
      <div class="flex gap-3">
        <div
          v-for="l in stats.by_language"
          :key="l.name"
          class="flex-1 rounded-lg bg-slate-50 p-3 text-center"
        >
          <div class="text-lg font-extrabold text-brand-700">
            {{ l.count }}
          </div>
          <div class="text-xs uppercase text-slate-400">
            {{ l.name }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

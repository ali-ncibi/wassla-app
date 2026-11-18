<script setup lang="ts">
import { t } from '~/utils/i18n'
import { useLang } from '~/composables/useLang'
import type { ArticlesResponse, CategoryCount } from '~/types/api'

const PAGE_SIZE = 30

const { lang } = useLang()
const route = useRoute()
const category = computed(() => (route.query.category as string) || '')
const page = computed(() => {
  const p = Number(route.query.page)

  return Number.isInteger(p) && p >= 1 ? p : 1
})

const { data: articles } = await useFetch<ArticlesResponse>('/api/articles', {
  query: computed(() => ({
    lang: lang.value,
    category: category.value || undefined,
    limit: PAGE_SIZE,
    offset: (page.value - 1) * PAGE_SIZE,
  })),
})
const { data: categories } = await useFetch<CategoryCount[]>('/api/categories')

const totalPages = computed(() => Math.max(1, Math.ceil((articles.value?.total ?? 0) / PAGE_SIZE)))

useHead({ title: 'Wassla — ' + t(lang.value, 'latest') })
</script>

<template>
  <div>
    <div class="mb-5 flex flex-wrap items-end justify-between gap-3">
      <h1 class="text-2xl font-extrabold tracking-tight">
        {{ t(lang, 'latest') }}
      </h1>
      <span class="text-sm text-slate-400">{{ articles?.total ?? 0 }}</span>
    </div>
    <CategoryChips
      v-if="categories"
      :categories="categories"
      class="mb-6"
    />
    <div
      v-if="articles?.items?.length"
      class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3"
    >
      <ArticleCard
        v-for="item in articles.items"
        :key="item.id"
        :article="item"
      />
    </div>
    <p
      v-else
      class="rounded-xl border border-dashed border-slate-300 bg-white p-10 text-center text-slate-400"
    >
      {{ t(lang, 'loading') }}
    </p>
    <Pagination
      v-if="totalPages > 1"
      :page="page"
      :total-pages="totalPages"
      class="mt-8"
    />
  </div>
</template>

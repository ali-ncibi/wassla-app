<script setup lang="ts">
import { t } from '~/utils/i18n'
import { useLang } from '~/composables/useLang'

interface CategoryCount {
  name: string
  count: number
}

defineProps<{ categories: CategoryCount[] }>()

const { lang } = useLang()
const route = useRoute()
const router = useRouter()

const active = computed(() => (route.query.category as string) || '')

function select(name: string) {
  router.push({ query: { ...route.query, category: name || undefined, page: undefined } })
}
</script>

<template>
  <div class="flex flex-wrap items-center gap-2">
    <button
      type="button"
      class="rounded-full border px-3 py-1 text-xs font-semibold capitalize transition-colors"
      :class="active === '' ? 'border-brand-600 bg-brand-600 text-white' : 'border-slate-300 bg-white text-slate-600 hover:border-brand-400'"
      @click="select('')"
    >
      {{ t(lang, 'all') }}
    </button>
    <button
      v-for="c in categories"
      :key="c.name"
      type="button"
      class="rounded-full border px-3 py-1 text-xs font-semibold capitalize transition-colors"
      :class="active === c.name ? 'border-brand-600 bg-brand-600 text-white' : 'border-slate-300 bg-white text-slate-600 hover:border-brand-400'"
      @click="select(c.name)"
    >
      {{ c.name }} <span class="opacity-60">{{ c.count }}</span>
    </button>
  </div>
</template>

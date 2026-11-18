<script setup lang="ts">
import { t } from '~/utils/i18n'
import { useLang } from '~/composables/useLang'

const { lang } = useLang()
const route = useRoute()

const links = computed(() => [
  { to: { path: '/', query: { lang: lang.value } }, label: t(lang.value, 'home'), active: route.path === '/' },
  { to: { path: '/search', query: { lang: lang.value } }, label: t(lang.value, 'search'), active: route.path === '/search' },
  { to: { path: '/stats', query: { lang: lang.value } }, label: t(lang.value, 'stats'), active: route.path === '/stats' },
])
</script>

<template>
  <header class="bg-brand-950 text-white sticky top-0 z-20 shadow-md">
    <div class="mx-auto flex max-w-5xl items-center gap-6 px-4 py-3">
      <NuxtLink
        :to="{ path: '/', query: { lang } }"
        class="flex items-baseline gap-2"
      >
        <span class="text-2xl font-extrabold tracking-tight">Wassla</span>
        <span class="hidden text-xs text-brand-200 sm:inline">{{ t(lang, 'wasslaTagline') }}</span>
      </NuxtLink>
      <nav class="ms-auto flex items-center gap-1">
        <NuxtLink
          v-for="link in links"
          :key="link.to.path"
          :to="link.to"
          class="rounded-md px-3 py-1.5 text-sm font-medium transition-colors"
          :class="link.active ? 'bg-white/15 text-white' : 'text-brand-100 hover:bg-white/10 hover:text-white'"
        >
          {{ link.label }}
        </NuxtLink>
        <LangSwitcher class="ms-2" />
      </nav>
    </div>
  </header>
</template>

<script setup lang="ts">
import { useLang } from '~/composables/useLang'

const { lang } = useLang()

useHead({
  htmlAttrs: {
    lang: () => lang.value,
    dir: () => (lang.value === 'ar' ? 'rtl' : 'ltr'),
  },
})
</script>

<template>
  <div class="min-h-screen flex flex-col">
    <SiteHeader />
    <main class="flex-1 mx-auto w-full max-w-5xl px-4 py-6">
      <slot />
    </main>
    <footer class="border-t border-slate-200 py-4 text-center text-xs text-slate-400">
      Wassla — AI-powered multilingual news
    </footer>
  </div>
</template>

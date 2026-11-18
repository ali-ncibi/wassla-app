<script setup lang="ts">
import { langs, langLabels } from '~/utils/i18n'
import { useLang } from '~/composables/useLang'

const { lang, setLang } = useLang()
</script>

<template>
  <div class="flex overflow-hidden rounded-md border border-white/25 text-xs font-semibold">
    <button
      v-for="l in langs"
      :key="l"
      type="button"
      class="px-2.5 py-1.5 transition-colors"
      :class="lang === l ? 'bg-brand-500 text-white' : 'bg-transparent text-brand-100 hover:bg-white/10'"
      @click="setLang(l)"
    >
      {{ langLabels[l] }}
    </button>
  </div>
</template>

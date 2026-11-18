import tailwindcss from '@tailwindcss/vite'

export default defineNuxtConfig({
  modules: ['@nuxt/eslint'],
  devtools: { enabled: false },
  css: ['~/assets/css/main.css'],
  runtimeConfig: {
    apiBase: process.env.NUXT_API_BASE || 'http://localhost:8000',
  },
  compatibilityDate: '2026-01-01',
  nitro: {
    preset: 'node-server',
  },
  vite: {
    plugins: [tailwindcss()],
  },
  typescript: {
    tsConfig: {
      compilerOptions: {
        noUncheckedIndexedAccess: true,
      },
    },
  },
  eslint: {
    config: {
      stylistic: true,
    },
  },
})

import withNuxt from './.nuxt/eslint.config.mjs'

export default withNuxt({
  rules: {
    '@typescript-eslint/no-explicit-any': 'error',
    'vue/multi-word-component-names': 'off',
    'padding-line-between-statements': [
      'error',
      { blankLine: 'always', prev: '*', next: 'return' },
      { blankLine: 'always', prev: 'block-like', next: '*' },
    ],
    'function-call-argument-newline': ['error', 'consistent'],
    'vue/max-attributes-per-line': [
      'error',
      { singleline: { max: 3 }, multiline: { max: 1 } },
    ],
    'vue/first-attribute-linebreak': [
      'error',
      { singleline: 'beside', multiline: 'below' },
    ],
  },
})

import { defineConfig } from 'vitest/config'

/**
 * Separate from `vite.config.ts` so tests skip route generation and Tailwind.
 * Node by default: most of what is worth testing is pure. Component tests opt in
 * to a DOM with a `@vitest-environment happy-dom` docblock.
 */
const config = defineConfig({
  test: {
    include: ['test/**/*.test.{ts,tsx}'],
    environment: 'node',
  },
  resolve: { tsconfigPaths: true },
})

export default config

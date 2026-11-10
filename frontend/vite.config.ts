import { defineConfig } from 'vite'
import { tanstackRouter } from '@tanstack/router-plugin/vite'
import viteReact from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

/**
 * In development the Django API runs on its own port and this dev server proxies
 * to it, so the browser only ever talks to one origin - the same shape as
 * production, where Django serves the built app and the API together. Nothing
 * in `src/` knows the API's address.
 */
const API_ORIGIN = process.env.API_ORIGIN ?? 'http://127.0.0.1:8000'

const config = defineConfig({
  resolve: { tsconfigPaths: true },
  plugins: [
    // Must run before the React plugin: it generates `src/routeTree.gen.ts`
    // and splits each route file into its own chunk.
    tanstackRouter({ target: 'react', autoCodeSplitting: true }),
    viteReact(),
    tailwindcss(),
  ],
  server: {
    proxy: {
      '/rpc': API_ORIGIN,
      '/healthz': API_ORIGIN,
      '/readyz': API_ORIGIN,
    },
  },
  build: {
    // Django serves `dist/index.html` for every page route and WhiteNoise serves
    // `dist/assets/` at `/assets/` - keep both names in step with server/settings.py.
    outDir: 'dist',
    assetsDir: 'assets',
    rolldownOptions: {
      output: {
        codeSplitting: {
          // MapLibre is most of the bundle and changes far less often than the
          // app; its own chunk stays cached across app releases.
          groups: [{ name: 'maplibre', test: /node_modules[\\/].*maplibre/ }],
        },
      },
    },
    // MapLibre alone is ~1.07 MB minified (~290 kB gzipped) and cannot be split
    // further; anything else crossing this line is a real regression.
    chunkSizeWarningLimit: 1100,
  },
})

export default config

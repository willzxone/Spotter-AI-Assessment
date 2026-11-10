import { setWorkerUrl } from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'
import 'maplibre-gl/dist/maplibre-gl.css'

// MapLibre resolves its worker from a computed URL that bundlers cannot see, so
// it would 404 in dev and be missing from the build. Hand it the emitted asset.
setWorkerUrl(workerUrl)

/** OpenFreeMap's light vector basemap: free, no key, and quiet enough for risk colours to read on top. */
export const BASEMAP_STYLE_URL = 'https://tiles.openfreemap.org/styles/positron'

/** The basemap's glyph fonts, for our own labels. */
export const MAP_FONT = ['Noto Sans Bold']

/** The contiguous US, as [west, south, east, north]. */
export const US_BOUNDS: [number, number, number, number] = [
  -125.0, 24.5, -66.9, 49.4,
]

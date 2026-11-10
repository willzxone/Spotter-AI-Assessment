import { Map as MaplibreMap, NavigationControl } from 'maplibre-gl'
import type { StyleSpecification } from 'maplibre-gl'
import { useEffect, useRef, useState } from 'react'
import { BASEMAP_STYLE_URL, US_BOUNDS } from './setup'

/**
 * Used when the basemap style cannot be fetched: a plain background, so the
 * map still loads and the app's own layers (routes, risk, heatmap) still draw.
 */
const FALLBACK_STYLE: StyleSpecification = {
  version: 8,
  glyphs: 'https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf',
  sources: {},
  layers: [
    {
      id: 'background',
      type: 'background',
      paint: { 'background-color': '#eef0f2' },
    },
  ],
}

/**
 * Own one MapLibre map for the component's lifetime. `map` stays null until the
 * style has loaded, so a caller can add sources and layers as soon as it is set.
 */
export function useMaplibre() {
  const containerRef = useRef<HTMLDivElement>(null)
  const [map, setMap] = useState<MaplibreMap | null>(null)

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const instance = new MaplibreMap({
      container,
      style: BASEMAP_STYLE_URL,
      bounds: US_BOUNDS,
      fitBoundsOptions: { padding: 24 },
      attributionControl: { compact: true },
      // Rotation and pitch only get in the way of reading a route.
      dragRotate: false,
      pitchWithRotate: false,
      touchPitch: false,
    })
    instance.touchZoomRotate.disableRotation()
    instance.keyboard.disableRotation()
    instance.addControl(
      new NavigationControl({ showCompass: false }),
      'top-right',
    )

    let loaded = false
    let fellBack = false
    instance.once('load', () => {
      loaded = true
      setMap(instance)
    })
    instance.on('error', () => {
      // Before the first load, an error means the basemap itself is unreachable.
      if (loaded || fellBack) return
      fellBack = true
      instance.setStyle(FALLBACK_STYLE)
    })

    return () => {
      setMap(null)
      instance.remove()
    }
  }, [])

  return { containerRef, map }
}

import type {
  FilterSpecification,
  GeoJSONSource,
  Map as MaplibreMap,
  MapMouseEvent,
} from 'maplibre-gl'
import { useEffect, useEffectEvent } from 'react'
import { MAP_FONT } from '@/integrations/maplibre/setup'
import { useMaplibre } from '@/integrations/maplibre/use-maplibre'
import type {
  CheckpointOut,
  Coord,
  PlanInput,
  PlanOutput,
  RouteOut,
} from '@/integrations/rpc/api.gen'
import { ROUTE_WIDTH } from '../constants'
import { boundsOf } from '../utils/geo'
import {
  EMPTY,
  checkpointPoints,
  endpointPoints,
  heatmapCells,
  routeLines,
  segmentLines,
  truckPoint,
} from '../utils/map-data'
import {
  ALTERNATIVE_COLOR,
  LAYER,
  LEVEL_COLOR,
  SOURCE,
  TRUCK_COLOR,
  heatColor,
  heatOpacity,
} from '../utils/map-style'

export interface RouteMapOptions {
  input: PlanInput | null
  plan: PlanOutput | null
  route: RouteOut | null
  hour: number
  truck: Coord | null
  inspected: CheckpointOut | null
  onSelectRoute: (id: string) => void
  onInspect: (index: number) => void
}

const ROUND = { 'line-join': 'round', 'line-cap': 'round' } as const
/** Clicks within this many pixels of a line or point still hit it (fingers are wide). */
const HIT_TOLERANCE_PX = 6

function setData(map: MaplibreMap, source: string, data: GeoJSON.GeoJSON) {
  map.getSource<GeoJSONSource>(source)?.setData(data)
}

function byRouteId(op: '==' | '!=', id: string): FilterSpecification {
  return [op, ['get', 'id'], id]
}

function addLayers(map: MaplibreMap) {
  for (const id of Object.values(SOURCE)) {
    map.addSource(id, { type: 'geojson', data: EMPTY })
  }
  map.addLayer({
    id: LAYER.heatmap,
    type: 'fill',
    source: SOURCE.heatmap,
    paint: {
      'fill-color': heatColor(0),
      'fill-opacity': heatOpacity(0),
      'fill-antialias': false,
    },
  })
  map.addLayer({
    id: LAYER.otherRoutes,
    type: 'line',
    source: SOURCE.routes,
    layout: ROUND,
    paint: {
      'line-color': ALTERNATIVE_COLOR,
      'line-width': ROUTE_WIDTH.other,
      'line-opacity': 0.8,
    },
  })
  // An invisible wide copy of the alternatives, so they are easy to click.
  map.addLayer({
    id: LAYER.otherRoutesHit,
    type: 'line',
    source: SOURCE.routes,
    layout: ROUND,
    paint: { 'line-color': '#000000', 'line-opacity': 0, 'line-width': 18 },
  })
  map.addLayer({
    id: LAYER.casing,
    type: 'line',
    source: SOURCE.routes,
    filter: byRouteId('==', ''),
    layout: ROUND,
    paint: { 'line-color': '#ffffff', 'line-width': ROUTE_WIDTH.selected + 4 },
  })
  map.addLayer({
    id: LAYER.segments,
    type: 'line',
    source: SOURCE.segments,
    layout: ROUND,
    paint: { 'line-color': LEVEL_COLOR, 'line-width': ROUTE_WIDTH.selected },
  })
  map.addLayer({
    id: LAYER.checkpoints,
    type: 'circle',
    source: SOURCE.checkpoints,
    paint: {
      'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 3.5, 10, 6.5],
      'circle-color': LEVEL_COLOR,
      'circle-stroke-color': '#ffffff',
      'circle-stroke-width': 1.5,
    },
  })
  map.addLayer({
    id: LAYER.checkpointActive,
    type: 'circle',
    source: SOURCE.checkpoints,
    filter: ['==', ['get', 'index'], -1],
    paint: {
      'circle-radius': 11,
      'circle-color': 'rgba(0, 0, 0, 0)',
      'circle-stroke-color': TRUCK_COLOR,
      'circle-stroke-width': 2.5,
    },
  })
  map.addLayer({
    id: LAYER.endpoints,
    type: 'circle',
    source: SOURCE.endpoints,
    paint: {
      'circle-radius': 7,
      'circle-color': [
        'match',
        ['get', 'role'],
        'origin',
        '#2563eb',
        TRUCK_COLOR,
      ],
      'circle-stroke-color': '#ffffff',
      'circle-stroke-width': 2.5,
    },
  })
  map.addLayer({
    id: LAYER.endpointLabels,
    type: 'symbol',
    source: SOURCE.endpoints,
    layout: {
      'text-field': ['get', 'label'],
      'text-font': MAP_FONT,
      'text-size': 12,
      'text-anchor': 'top',
      'text-offset': [0, 1],
      'text-max-width': 12,
    },
    paint: {
      'text-color': TRUCK_COLOR,
      'text-halo-color': '#ffffff',
      'text-halo-width': 1.5,
    },
  })
  map.addLayer({
    id: LAYER.truckHalo,
    type: 'circle',
    source: SOURCE.truck,
    paint: {
      'circle-radius': 12,
      'circle-color': '#ffffff',
      'circle-opacity': 0.9,
      'circle-blur': 0.2,
    },
  })
  map.addLayer({
    id: LAYER.truck,
    type: 'circle',
    source: SOURCE.truck,
    paint: {
      'circle-radius': 7,
      'circle-color': TRUCK_COLOR,
      'circle-stroke-color': '#ffffff',
      'circle-stroke-width': 2,
    },
  })
}

/** Padding that fits inside the map, however small the screen. */
function fitPadding(map: MaplibreMap) {
  const { clientWidth: w, clientHeight: h } = map.getContainer()
  const side = Math.min(48, w * 0.1)
  return {
    top: Math.min(56, h * 0.12),
    // Room for the heatmap slider laid over the bottom of the map: it is about
    // 120px from the map's bottom edge on a desktop, a little more when its legend wraps.
    bottom: Math.min(150, h * 0.35),
    left: side,
    right: side,
  }
}

export function useRouteMap({
  input,
  plan,
  route,
  hour,
  truck,
  inspected,
  onSelectRoute,
  onInspect,
}: RouteMapOptions) {
  const { containerRef, map } = useMaplibre()

  const handleClick = useEffectEvent((event: MapMouseEvent) => {
    if (!map) return
    const { x, y } = event.point
    const hits = map.queryRenderedFeatures(
      [
        [x - HIT_TOLERANCE_PX, y - HIT_TOLERANCE_PX],
        [x + HIT_TOLERANCE_PX, y + HIT_TOLERANCE_PX],
      ],
      // Checkpoints sit on top of the lines, so they win a shared click.
      { layers: [LAYER.checkpoints, LAYER.otherRoutesHit] },
    )
    const hit = hits[0]
    if (!hit) return
    if (hit.layer.id === LAYER.checkpoints) {
      onInspect(Number(hit.properties.index))
    } else {
      onSelectRoute(String(hit.properties.id))
    }
  })

  // Sources and layers, then the pointer handlers. Must stay the first effect:
  // the effects below write into these sources in the same commit.
  useEffect(() => {
    if (!map) return
    if (!map.getSource(SOURCE.routes)) addLayers(map)

    const interactive = [LAYER.checkpoints, LAYER.otherRoutesHit]
    const pointer = () => {
      map.getCanvas().style.cursor = 'pointer'
    }
    const reset = () => {
      map.getCanvas().style.cursor = ''
    }
    const click = (event: MapMouseEvent) => handleClick(event)
    map.on('click', click)
    for (const layer of interactive) {
      map.on('mouseenter', layer, pointer)
      map.on('mouseleave', layer, reset)
    }
    return () => {
      map.off('click', click)
      for (const layer of interactive) {
        map.off('mouseenter', layer, pointer)
        map.off('mouseleave', layer, reset)
      }
    }
  }, [map])

  // A new plan: draw every route and the heatmap, then frame the routes.
  useEffect(() => {
    if (!map) return
    setData(map, SOURCE.routes, plan ? routeLines(plan.routes) : EMPTY)
    setData(map, SOURCE.heatmap, plan ? heatmapCells(plan.heatmap) : EMPTY)
    if (!plan) return
    const bounds = boundsOf(plan.routes.flatMap((r) => r.geometry))
    if (bounds) {
      // The first plan also mounts the checkpoint table, which shrinks the map in this
      // same commit. MapLibre's own resize observer fires later, so without this the
      // camera would frame the routes for the old, taller canvas and cut off the end.
      map.resize()
      map.fitBounds(bounds, {
        padding: fitPadding(map),
        maxZoom: 10,
        duration: 700,
      })
    }
  }, [map, plan])

  useEffect(() => {
    if (!map) return
    setData(
      map,
      SOURCE.endpoints,
      input ? endpointPoints(input.origin, input.destination) : EMPTY,
    )
  }, [map, input])

  // The selected route is coloured by risk; the others stay grey and clickable.
  useEffect(() => {
    if (!map) return
    const id = route?.id ?? ''
    map.setFilter(LAYER.casing, byRouteId('==', id))
    map.setFilter(LAYER.otherRoutes, byRouteId('!=', id))
    map.setFilter(LAYER.otherRoutesHit, byRouteId('!=', id))
    setData(map, SOURCE.segments, route ? segmentLines(route) : EMPTY)
    setData(map, SOURCE.checkpoints, route ? checkpointPoints(route) : EMPTY)
  }, [map, route])

  useEffect(() => {
    if (!map) return
    map.setPaintProperty(LAYER.heatmap, 'fill-color', heatColor(hour))
    map.setPaintProperty(LAYER.heatmap, 'fill-opacity', heatOpacity(hour))
  }, [map, hour])

  const truckLon = truck?.[0]
  const truckLat = truck?.[1]
  useEffect(() => {
    if (!map) return
    setData(
      map,
      SOURCE.truck,
      truckLon === undefined || truckLat === undefined
        ? EMPTY
        : truckPoint([truckLon, truckLat]),
    )
  }, [map, truckLon, truckLat])

  // Ring the inspected checkpoint, and bring it into view if it is off screen.
  useEffect(() => {
    if (!map) return
    map.setFilter(LAYER.checkpointActive, [
      '==',
      ['get', 'index'],
      inspected?.index ?? -1,
    ])
    if (!inspected) return
    const at: Coord = [inspected.lon, inspected.lat]
    if (!map.getBounds().contains(at)) {
      map.easeTo({ center: at, duration: 500 })
    }
  }, [map, inspected])

  return { containerRef, ready: map !== null }
}

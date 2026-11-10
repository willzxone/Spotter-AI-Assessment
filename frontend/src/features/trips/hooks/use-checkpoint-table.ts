import { useEffect, useRef } from 'react'

/** Keep the inspected row in view when it is picked on the map. */
export function useCheckpointTable(inspected: number | null) {
  const rows = useRef(new Map<number, HTMLTableRowElement>())

  useEffect(() => {
    if (inspected === null) return
    rows.current.get(inspected)?.scrollIntoView({ block: 'nearest' })
  }, [inspected])

  /** A ref callback for row `index`; React 19 runs the returned cleanup on unmount. */
  function rowRef(index: number) {
    return (el: HTMLTableRowElement | null) => {
      if (!el) return
      rows.current.set(index, el)
      return () => {
        rows.current.delete(index)
      }
    }
  }

  return { rowRef }
}

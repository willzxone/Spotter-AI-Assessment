import { keepPreviousData, useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'
import type { Place } from '@/integrations/rpc/api.gen'
import { errorMessage } from '@/integrations/rpc/client'
import { placeSearchQueryOptions } from '../api/queries'
import { DEBOUNCE_MS, MIN_QUERY_LENGTH } from '../constants'

/** The latest `value`, once it has stopped changing for `delayMs`. */
function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs)
    return () => clearTimeout(timer)
  }, [value, delayMs])
  return debounced
}

interface Options {
  onSelect: (place: Place) => void
  /** Called when the picker closes, so a form can mark the field touched. */
  onBlur?: () => void
}

export function usePlaceSearch({ onSelect, onBlur }: Options) {
  const [open, setOpen] = useState(false)
  const [text, setText] = useState('')
  const query = useDebouncedValue(text.trim(), DEBOUNCE_MS)

  const search = useQuery({
    ...placeSearchQueryOptions(query),
    // Keep the last list on screen while the next one loads, so it does not flicker.
    placeholderData: keepPreviousData,
  })

  const tooShort = text.trim().length < MIN_QUERY_LENGTH
  const settled = query === text.trim() && !search.isFetching

  function onOpenChange(next: boolean) {
    setOpen(next)
    if (!next) onBlur?.()
  }

  function select(place: Place) {
    onSelect(place)
    onOpenChange(false)
    setText('')
  }

  return {
    open,
    onOpenChange,
    text,
    setText,
    places: tooShort ? [] : (search.data?.places ?? []),
    tooShort,
    isSearching: !tooShort && !settled,
    isEmpty: !tooShort && settled && search.data?.places.length === 0,
    error: search.isError ? errorMessage(search.error) : null,
    select,
  }
}

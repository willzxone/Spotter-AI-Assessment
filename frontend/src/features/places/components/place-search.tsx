import { ChevronsUpDown, Loader2, MapPin } from 'lucide-react'
import { cn } from 'cn'
import { Button } from '@/components/ui/button'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import type { Place } from '@/integrations/rpc/api.gen'
import { MAX_QUERY_LENGTH, MIN_QUERY_LENGTH } from '../constants'
import { usePlaceSearch } from '../hooks/use-place-search'

interface Props {
  id: string
  /** The chosen place's label, or null when nothing is chosen yet. */
  value: string | null
  placeholder: string
  onSelect: (place: Place) => void
  onBlur?: () => void
  invalid?: boolean
}

export function PlaceSearch({
  id,
  value,
  placeholder,
  onSelect,
  onBlur,
  invalid,
}: Props) {
  const {
    open,
    onOpenChange,
    text,
    setText,
    places,
    tooShort,
    isSearching,
    isEmpty,
    error,
    select,
  } = usePlaceSearch({ onSelect, onBlur })

  return (
    <Popover open={open} onOpenChange={onOpenChange}>
      <PopoverTrigger asChild>
        <Button
          id={id}
          variant="outline"
          role="combobox"
          aria-expanded={open}
          aria-invalid={invalid}
          className="w-full justify-between font-normal"
        >
          <span className={cn('truncate', !value && 'text-muted-foreground')}>
            {value ?? placeholder}
          </span>
          <ChevronsUpDown className="opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent
        className="w-(--radix-popover-trigger-width) min-w-72 p-0"
        align="start"
      >
        {/* Results come from the server already ranked; cmdk must not re-filter them. */}
        <Command shouldFilter={false}>
          <CommandInput
            placeholder="Search a city or address…"
            value={text}
            onValueChange={setText}
            maxLength={MAX_QUERY_LENGTH}
          />
          <CommandList>
            {tooShort ? (
              <p className="text-muted-foreground px-3 py-6 text-center text-sm">
                Type at least {MIN_QUERY_LENGTH} characters.
              </p>
            ) : error ? (
              <p className="text-destructive px-3 py-6 text-center text-sm">
                {error}
              </p>
            ) : isSearching && places.length === 0 ? (
              <p className="text-muted-foreground flex items-center justify-center gap-2 px-3 py-6 text-sm">
                <Loader2 className="size-4 animate-spin" /> Searching…
              </p>
            ) : isEmpty ? (
              <CommandEmpty>No places found.</CommandEmpty>
            ) : (
              <CommandGroup>
                {places.map((place) => (
                  <CommandItem
                    key={place.id}
                    value={place.id}
                    onSelect={() => select(place)}
                  >
                    <MapPin className="text-muted-foreground" />
                    <div className="flex min-w-0 flex-col">
                      <span className="truncate">{place.name}</span>
                      <span className="text-muted-foreground truncate text-xs">
                        {place.label}
                      </span>
                    </div>
                  </CommandItem>
                ))}
              </CommandGroup>
            )}
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  )
}

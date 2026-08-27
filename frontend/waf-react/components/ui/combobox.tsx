'use client'

import { useEffect, useRef, useState } from 'react'
import { Loader2 } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { cn } from '@/lib/utils'

export interface ComboboxOption {
  /** The raw value sent to the API — quotes and all. */
  value: string
  /** How it reads in the list. Defaults to `value`. */
  label?: string
  /** Optional right-aligned count. */
  count?: number
}

interface ComboboxProps {
  /** The text in the input. Owned by the parent so it can drive the server-side search. */
  query: string
  onQueryChange: (q: string) => void
  onSelect: (value: string) => void
  options: ComboboxOption[]
  loading?: boolean
  placeholder?: string
  /** Fires on Enter when nothing is highlighted — lets a typed value be submitted as-is. */
  onSubmitRaw?: () => void
  className?: string
}

/**
 * Text input with a filtered suggestion list.
 *
 * Written rather than pulled in: the project has no `cmdk` and no popover primitive, and
 * `@radix-ui/react-select` (the only combobox-ish thing present) cannot host a text input
 * without fighting its focus management.
 *
 * Suggestions are supplied by the parent, which fetches them from the server as `query`
 * changes — the value count grows with the configuration, so the search cannot live here.
 * Free typing is always allowed: a value absent from the list is still submittable, which
 * matters for tags the top-N cut off.
 */
export function Combobox({
  query,
  onQueryChange,
  onSelect,
  options,
  loading,
  placeholder,
  onSubmitRaw,
  className,
}: ComboboxProps) {
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(-1)
  const wrap = useRef<HTMLDivElement>(null)

  // Close when focus or a click leaves the whole widget. Listening on the container rather
  // than the input's blur keeps a click on a suggestion from closing the list first.
  useEffect(() => {
    const away = (e: MouseEvent | FocusEvent) => {
      if (wrap.current && !wrap.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', away)
    document.addEventListener('focusin', away)
    return () => {
      document.removeEventListener('mousedown', away)
      document.removeEventListener('focusin', away)
    }
  }, [])

  // A new result set invalidates whatever was highlighted.
  useEffect(() => setActive(-1), [options])

  const choose = (value: string) => {
    onSelect(value)
    setOpen(false)
    setActive(-1)
  }

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      setOpen(false)
      return
    }
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      e.preventDefault()
      setOpen(true)
      setActive((i) => {
        const n = options.length
        if (!n) return -1
        return e.key === 'ArrowDown' ? (i + 1) % n : (i <= 0 ? n : i) - 1
      })
      return
    }
    if (e.key === 'Enter') {
      if (open && active >= 0 && options[active]) {
        e.preventDefault()
        choose(options[active].value)
      } else if (onSubmitRaw) {
        e.preventDefault()
        onSubmitRaw()
        // Close as a pick would: the list otherwise stays open over the chip row and hides
        // the filter that was just added.
        setOpen(false)
      }
    }
  }

  return (
    <div ref={wrap} className={cn('relative', className)}>
      <Input
        value={query}
        onChange={(e) => {
          onQueryChange(e.target.value)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        // Also on click, not just focus: selecting an option keeps focus on the input (the
        // option uses mousedown+preventDefault), so after one pick the input is already
        // focused and clicking it would never re-fire onFocus — leaving no way to reopen
        // the list short of typing. Picking two tags in a row goes through here.
        onClick={() => setOpen(true)}
        onKeyDown={onKeyDown}
        placeholder={placeholder}
        className="font-mono"
        role="combobox"
        aria-expanded={open}
        aria-autocomplete="list"
      />

      {loading && (
        <Loader2 className="absolute right-2 top-2.5 h-4 w-4 animate-spin text-muted-foreground" />
      )}

      {open && (
        <ul
          role="listbox"
          className="absolute z-50 mt-1 max-h-72 w-full overflow-y-auto rounded-md border bg-popover p-1 text-popover-foreground shadow-md"
        >
          {options.map((o, i) => (
            <li key={o.value}>
              <button
                type="button"
                role="option"
                aria-selected={i === active}
                // mousedown, not click: the input's blur would otherwise tear the list
                // down before the click landed.
                onMouseDown={(e) => {
                  e.preventDefault()
                  choose(o.value)
                }}
                onMouseEnter={() => setActive(i)}
                className={cn(
                  'flex w-full items-center justify-between gap-3 rounded-sm px-2 py-1.5 text-left text-sm',
                  i === active ? 'bg-accent text-accent-foreground' : ''
                )}
              >
                <span className="truncate font-mono">{o.label ?? o.value}</span>
                {o.count != null && (
                  <span className="shrink-0 tabular-nums text-xs text-muted-foreground">
                    {o.count.toLocaleString()}
                  </span>
                )}
              </button>
            </li>
          ))}

          {options.length === 0 && (
            <li className="px-2 py-3 text-center text-sm text-muted-foreground">
              {loading ? 'Searching…' : query ? 'No match — press Enter to use as typed' : 'No values'}
            </li>
          )}
        </ul>
      )}
    </div>
  )
}

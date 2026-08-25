import * as React from 'react'
import { cn } from '@/lib/utils'

interface EmptyStateProps {
  icon?: React.ElementType
  title: string
  description?: React.ReactNode
  action?: React.ReactNode
  variant?: 'default' | 'warning'
  className?: string
}

/**
 * Placeholder for "no results" and for the not-parsed / empty-graph panels.
 * `warning` is used when the state is actionable rather than merely empty.
 */
export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  variant = 'default',
  className,
}: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center rounded-lg border border-dashed px-6 py-12 text-center',
        variant === 'warning' && 'border-amber-300 bg-amber-50/60',
        className
      )}
    >
      {Icon && (
        <Icon
          className={cn(
            'mb-3 h-8 w-8',
            variant === 'warning' ? 'text-amber-500' : 'text-muted-foreground/60'
          )}
        />
      )}
      <p
        className={cn(
          'font-medium',
          variant === 'warning' ? 'text-amber-900' : 'text-foreground'
        )}
      >
        {title}
      </p>
      {description && (
        <div
          className={cn(
            'mt-1 max-w-prose text-sm',
            variant === 'warning' ? 'text-amber-800' : 'text-muted-foreground'
          )}
        >
          {description}
        </div>
      )}
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

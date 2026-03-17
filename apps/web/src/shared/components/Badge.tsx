import type { PropsWithChildren } from 'react'
import { cn } from '@/shared/lib/cn'

interface BadgeProps extends PropsWithChildren {
  tone?: 'default' | 'muted'
}

export function Badge({ children, tone = 'default' }: BadgeProps) {
  return (
    <span
      className={cn(
        'rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.15em]',
        tone === 'default' && 'bg-secondary text-secondary-foreground',
        tone === 'muted' && 'bg-muted text-muted-foreground',
      )}
    >
      {children}
    </span>
  )
}

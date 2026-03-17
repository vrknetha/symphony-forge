import type { PropsWithChildren } from 'react'
import { Button } from './Button'

interface ModalProps extends PropsWithChildren {
  description: string
  isOpen: boolean
  onClose: () => void
  title: string
}

export function Modal({ children, description, isOpen, onClose, title }: ModalProps) {
  if (!isOpen) {
    return null
  }

  return (
    <div
      aria-labelledby="modal-title"
      aria-modal="true"
      className="fixed inset-0 z-50 flex items-center justify-center bg-foreground/40 px-4"
      role="dialog"
    >
      <div className="w-full max-w-lg rounded-lg border border-border bg-card p-6 shadow-lg">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 className="font-display text-2xl" id="modal-title">
              {title}
            </h2>
            <p className="mt-2 text-sm text-muted-foreground">{description}</p>
          </div>
          <Button aria-label="Close dialog" onClick={onClose} variant="ghost">
            Close
          </Button>
        </div>
        <div className="mt-6">{children}</div>
      </div>
    </div>
  )
}

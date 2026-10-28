import { Drawer } from 'vaul';
import type { ReactNode } from 'react';

export interface SheetProps {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
  /** Max height as a CSS value. Defaults to "90dvh". */
  maxHeight?: string;
  /** Whether to render the drag handle bar. Defaults to true. */
  showHandle?: boolean;
  /** Optional sticky title above content. */
  title?: string;
  /** Optional sticky footer below content. */
  footer?: ReactNode;
}

export function Sheet({ open, onClose, children, maxHeight = '90dvh', showHandle = true, title, footer }: SheetProps) {
  return (
    <Drawer.Root open={open} onOpenChange={(o) => !o && onClose()}>
      <Drawer.Portal>
        <Drawer.Overlay className="fixed inset-0 z-40 bg-ink/50" />
        <Drawer.Content
          className="fixed bottom-0 left-0 right-0 z-50 rounded-t-3xl overflow-hidden bg-cream flex flex-col"
          style={{ maxHeight }}
        >
          {showHandle && (
            <div className="flex justify-center pt-3 pb-2 shrink-0">
              <div className="w-10 h-1 rounded-full bg-border" />
            </div>
          )}
          {title ? (
            <div className="px-5 pb-3 shrink-0 border-b border-border">
              <Drawer.Title className="text-base font-semibold text-ink">{title}</Drawer.Title>
            </div>
          ) : (
            // Accessible name for screen readers when the consumer renders its
            // own heading inside children (keeps Radix/vaul from warning).
            <Drawer.Title
              style={{
                position: 'absolute', width: 1, height: 1, padding: 0, margin: -1,
                overflow: 'hidden', clip: 'rect(0,0,0,0)', whiteSpace: 'nowrap', border: 0,
              }}
            >
              Details
            </Drawer.Title>
          )}
          <div className="flex-1 overflow-y-auto">{children}</div>
          {footer && (
            <div className="shrink-0 border-t border-border p-4">{footer}</div>
          )}
        </Drawer.Content>
      </Drawer.Portal>
    </Drawer.Root>
  );
}

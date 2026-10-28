/**
 * DocumentSheet — Vaul bottom drawer that composes DocumentViewer.
 * Opens a full-height (92dvh) drawer to display a document URL.
 */

import { X } from 'lucide-react';
import { DocumentViewer } from '../DocumentViewer';
import { Button , Sheet } from '@scope/ui';

interface DocumentSheetProps {
  open: boolean;
  onClose: () => void;
  src: string;
  title: string;
}

export function DocumentSheet({ open, onClose, src, title }: DocumentSheetProps) {
  return (
    <Sheet open={open} onClose={onClose}>
          <div className="shrink-0 flex items-center justify-end px-3 py-2 border-b border-border bg-cream/80 backdrop-blur-sm">
            <Button variant="secondary" className="p-1.5 text-muted" type="button" onClick={onClose}><X size={18} /></Button>
          </div>
          <div className="flex-1 flex flex-col overflow-hidden p-4">
            <DocumentViewer src={src} title={title} className="flex-1 flex flex-col" fullHeight />
          </div>
        </Sheet>
  );
}

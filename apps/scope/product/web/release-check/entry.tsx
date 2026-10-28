import { createRoot } from 'react-dom/client';
import { LeoBubble } from 'source-bubbles';
import { OriginalLeoBubble } from './OriginalBubble';
const original = '<img src="data:image/png;base64,invalid" onerror="window.originalExecuted=true">';
const patched = '<img src="data:image/png;base64,invalid" onerror="window.patchedExecuted=true"> **Readable formatting**';
createRoot(document.getElementById('root')!).render(<><section id="before"><OriginalLeoBubble text={original}/></section><section id="after"><LeoBubble text={patched}/></section></>);

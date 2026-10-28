import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { fileURLToPath } from 'node:url';
import { resolve, dirname } from 'node:path';
const here=dirname(fileURLToPath(import.meta.url));
const root=resolve(here,'../../../../..');
export default defineConfig({root:here,base:'./',plugins:[react()],resolve:{dedupe:['react','react-dom'],alias:{'source-bubbles':resolve(root,'packages/ui/src/ChatBubbles.tsx'),'marked':resolve(root,'packages/ui/node_modules/marked/lib/marked.esm.js')}},build:{outDir:resolve(root,'.local/markdown-boundary'),emptyOutDir:true}});

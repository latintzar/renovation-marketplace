# Leo Brand Assets

## Logo SVGs

Two variants, both transparent background, both Playfair Display SemiBold paths:

| File | Color | Use on |
|------|-------|--------|
| `leo-charcoal.svg` | `#1C1917` charcoal | Cream (`#FAF8F4`) or any light surface |
| `leo-cream.svg` | `#FAF8F4` cream | Charcoal (`#1C1917`) or any dark surface |

**Rules:**
- Logo is **never terra** (`#DA654D`). Never any other color.
- Font is **Playfair Display SemiBold** — stored as SVG paths (no font dependency at render time).
- Never render the logo as live text — always use these SVG files.

## Regenerating

Requires `fonttools` (`pip install fonttools`) and the Playfair Display SemiBold TTF.

```bash
python3 scope-app/public/brand/generate-logo.py
```

The script downloads the font from Google Fonts CDN and writes both SVG files into `/tmp/`, then you copy them here. To change size or text, edit `font_size` and `text` in the script.

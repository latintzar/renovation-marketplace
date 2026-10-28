#!/usr/bin/env python3
"""
Convert text to SVG paths using fonttools.
Generates two transparent SVG files for the Leo wordmark:
  - leo-charcoal.svg  (#1C1917 on transparent, use on cream/light backgrounds)
  - leo-cream.svg     (#FAF8F4 on transparent, use on charcoal/dark backgrounds)

The SVG viewBox is tightly cropped to the actual ink of the glyphs.
Font: Playfair Display SemiBold (600 weight).
"""

from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen


def text_to_svg_paths(font_path, text, font_size, color, output_path):
    font = TTFont(font_path)
    glyph_set = font.getGlyphSet()
    hmtx = font['hmtx']
    cmap = font.getBestCmap()
    units_per_em = font['head'].unitsPerEm

    scale = font_size / units_per_em
    print(f"  Font: {font_path}")
    print(f"  UPM: {units_per_em}, scale: {scale:.4f}")

    # Build glyph sequence
    glyphs = []
    for char in text:
        cp = ord(char)
        glyph_name = cmap.get(cp)
        if glyph_name is None:
            print(f"  WARNING: no glyph for '{char}' (U+{cp:04X})")
            continue
        advance_width, lsb = hmtx.metrics[glyph_name]
        glyphs.append((char, glyph_name, advance_width, lsb))

    # --- Pass 1: compute tight bounding box across all glyphs ---
    x_cursor_units = 0
    min_x = min_y = float('inf')
    max_x = max_y = float('-inf')

    for char, glyph_name, advance_width, lsb in glyphs:
        bp = BoundsPen(glyph_set)
        glyph_set[glyph_name].draw(bp)
        if bp.bounds:
            gxmin, gymin, gxmax, gymax = bp.bounds
            min_x = min(min_x, x_cursor_units + gxmin)
            max_x = max(max_x, x_cursor_units + gxmax)
            min_y = min(min_y, gymin)
            max_y = max(max_y, gymax)
        x_cursor_units += advance_width

    print(f"  Tight bounds (font units): x [{min_x:.0f}, {max_x:.0f}] y [{min_y:.0f}, {max_y:.0f}]")

    # Padding in font units
    pad = units_per_em * 0.04
    vb_x = (min_x - pad) * scale
    vb_y = (-max_y - pad) * scale  # flip y
    vb_w = (max_x - min_x + pad * 2) * scale
    vb_h = (max_y - min_y + pad * 2) * scale

    # --- Pass 2: render SVG paths ---
    paths = []
    x_cursor = 0

    for char, glyph_name, advance_width, lsb in glyphs:
        pen = SVGPathPen(glyph_set)
        glyph_set[glyph_name].draw(pen)
        d = pen.getCommands()

        if d:
            # Flip Y: SVG y grows down, font y grows up
            # matrix(scale, 0, 0, -scale, tx, ty) where baseline_y = 0 in font space
            tx = x_cursor * scale
            ty = 0
            paths.append(
                f'<path transform="matrix({scale},0,0,{-scale},{tx:.3f},{ty})" '
                f'd="{d}" fill="{color}"/>'
            )

        x_cursor += advance_width

    svg_content = (
        f'<svg xmlns="http://www.w3.org/2000/svg"'
        f' viewBox="{vb_x:.3f} {vb_y:.3f} {vb_w:.3f} {vb_h:.3f}">\n'
        f'  <title>Leo</title>\n'
        + '\n'.join(f'  {p}' for p in paths)
        + '\n</svg>'
    )

    with open(output_path, 'w') as f:
        f.write(svg_content)

    print(f"  Written: {output_path}")
    print(f"  ViewBox: {vb_x:.2f} {vb_y:.2f} {vb_w:.2f} {vb_h:.2f}")
    return vb_w, vb_h


if __name__ == '__main__':
    font_path = '/tmp/PlayfairDisplay-SemiBold.ttf'
    text = 'Leo'
    font_size = 96

    print("=== Generating Leo wordmark SVGs ===")

    print("\n[1] Charcoal (#1C1917) — use on cream/light backgrounds")
    text_to_svg_paths(font_path, text, font_size, '#1C1917', '/tmp/leo-charcoal.svg')

    print("\n[2] Cream (#FAF8F4) — use on charcoal/dark backgrounds")
    text_to_svg_paths(font_path, text, font_size, '#FAF8F4', '/tmp/leo-cream.svg')

    print("\nDone.")

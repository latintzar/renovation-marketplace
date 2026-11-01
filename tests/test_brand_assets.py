"""The reusable web build carries the real Leo vellum at its mounted base path."""
from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[1]

def test_web_public_brand_asset_is_the_real_stylesheet():
    source=ROOT/'apps/scope/product/public/brand-effects.css'
    bundled=ROOT/'apps/scope/product/web/public/brand-effects.css'
    assert bundled.read_bytes()==source.read_bytes()
    assert '.brand-glass--vellum {' in bundled.read_text()
    assert 'backdrop-filter: blur(7px)' in bundled.read_text()

def test_brand_link_uses_the_configured_vite_base():
    html=(ROOT/'apps/scope/product/web/index.html').read_text()
    assert 'href="%BASE_URL%brand-effects.css"' in html
    assert 'href="/brand-effects.css"' not in html

def test_quote_canvas_labels_are_present_in_both_languages():
    canvas=(ROOT/'packages/ui/src/QuoteCanvas.tsx').read_text()
    keys=set(re.findall(r"t\('([^']+)'",canvas))
    for language in ['en','es']:
        resource=json.loads((ROOT/f'apps/scope/product/web/src/locales/{language}.json').read_text())
        assert keys<=resource.keys(),(language,sorted(keys-resource.keys()))

/**
 * LocationPickerModal — full-screen location picker for the scope builder.
 *
 * Exact port of the homeowner hero location step (homeowners.html):
 *   - Full-screen white modal
 *   - Mapbox GL map fills the space (compresses when keyboard opens)
 *   - Terra pin centred on the map
 *   - Address input with Mapbox forward-geocode autocomplete
 *   - "Use my location" button (reverse geocode)
 *   - "Confirm" CTA with neighbourhood-only privacy note
 *
 * Token: same Mapbox project used by homeowners.html (public pk. token, safe in frontend).
 * Geocoding: Mapbox Geocoding API v5 — place, locality, neighbourhood.
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';
import { Button, Input } from '@scope/ui';

const MB_TOKEN = import.meta.env.VITE_MAPBOX_ACCESS_TOKEN || "";
const LOC_RADIUS_KM = 1.25;
const DEFAULT_CENTER: [number, number] = [-4.4, 36.7]; // Málaga coast
const DEFAULT_ZOOM = 7;

interface LocDraft {
  lng: number;
  lat: number;
  label: string;
}

interface Suggestion {
  id: string;
  place_name: string;
  center: [number, number];
}

interface LocationPickerModalProps {
  lang: 'es' | 'en';
  initialLocation?: string;
  onConfirm: (label: string, coords: { lng: number; lat: number }) => void;
  onClose: () => void;
}

function jitter(coord: number, maxDelta: number): number {
  return coord + (Math.random() - 0.5) * maxDelta;
}

function jitterCenter(lng: number, lat: number): [number, number] {
  const delta = LOC_RADIUS_KM / 111;
  return [jitter(lng, delta), jitter(lat, delta)];
}

async function geocodeForward(q: string): Promise<Suggestion[]> {
  const r = await fetch(
    `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(q)}.json` +
      `?types=place,locality,postcode,district,neighborhood,address&limit=6&country=es,gb,fr,de,pt,it&access_token=${MB_TOKEN}`,
  );
  const d = await r.json();
  return (d.features || []).map((f: { id: string; place_name: string; center: [number, number] }) => ({
    id: f.id,
    place_name: f.place_name,
    center: f.center,
  }));
}

async function geocodeReverse(lng: number, lat: number): Promise<string> {
  const r = await fetch(
    `https://api.mapbox.com/geocoding/v5/mapbox.places/${encodeURIComponent(lng + ',' + lat)}.json` +
      `?types=place,locality,neighborhood,region&limit=1&access_token=${MB_TOKEN}`,
  );
  const d = await r.json();
  const f = d.features?.[0];
  return f ? f.place_name.split(',')[0].trim() : '';
}

export default function LocationPickerModal({
  lang,
  initialLocation,
  onConfirm,
  onClose,
}: LocationPickerModalProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const [draft, setDraft] = useState<LocDraft | null>(null);
  const [searchVal, setSearchVal] = useState(initialLocation ?? '');
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [pinVisible, setPinVisible] = useState(false);
  const [confirmVisible, setConfirmVisible] = useState(false);
  const [geoLoading, setGeoLoading] = useState(false);
  const [searchErr, setSearchErr] = useState('');
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const T = {
    title: lang === 'es' ? '¿Dónde es el trabajo?' : 'Where is the job?',
    subtitle: lang === 'es'
      ? 'Solo aparece el barrio en el presupuesto.'
      : 'Only the neighbourhood appears on the scope.',
    placeholder: lang === 'es' ? 'Ciudad o dirección…' : 'City or address…',
    useLocation: lang === 'es' ? 'Usar mi ubicación' : 'Use my location',
    confirm: lang === 'es' ? 'Confirmar ubicación' : 'Confirm location',
    privacyNote: lang === 'es'
      ? 'Tu dirección exacta no se comparte. Solo el área aproximada.'
      : 'Your exact address is not shared. Approximate area only.',
    notFound: lang === 'es' ? 'No encontrado. Prueba otra búsqueda.' : 'Not found. Try a different search.',
    geoErr: lang === 'es' ? 'No se pudo obtener tu ubicación.' : 'Could not get your location.',
  };

  // Init map
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;
    mapboxgl.accessToken = MB_TOKEN;
    const map = new mapboxgl.Map({
      container: mapContainerRef.current,
      style: 'mapbox://styles/mapbox/light-v11',
      center: DEFAULT_CENTER,
      zoom: DEFAULT_ZOOM,
      attributionControl: false,
    });
    map.addControl(new mapboxgl.NavigationControl({ visualizePitch: false }), 'top-right');
    mapRef.current = map;

    // If initialLocation looks like coordinates, geocode it
    if (initialLocation && initialLocation.trim()) {
      geocodeForward(initialLocation).then((results) => {
        if (results[0]) selectSuggestion(results[0], map);
      }).catch(() => {});
    }

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const flyTo = useCallback((center: [number, number], map?: mapboxgl.Map) => {
    const m = map ?? mapRef.current;
    if (!m) return;
    m.flyTo({ center, zoom: 13, speed: 1.4 });
    setPinVisible(true);
    setConfirmVisible(true);
  }, []);

  const selectSuggestion = useCallback((sug: Suggestion, map?: mapboxgl.Map) => {
    const [lng, lat] = jitterCenter(sug.center[0], sug.center[1]);
    const label = sug.place_name.split(',')[0].trim();
    setDraft({ lng, lat, label });
    setSearchVal(label);
    setSuggestions([]);
    setShowSuggestions(false);
    flyTo([lng, lat], map);
  }, [flyTo]);

  const handleSearchChange = (val: string) => {
    setSearchVal(val);
    setSearchErr('');
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (!val.trim()) { setSuggestions([]); setShowSuggestions(false); return; }
    debounceRef.current = setTimeout(async () => {
      try {
        const results = await geocodeForward(val);
        setSuggestions(results);
        setShowSuggestions(results.length > 0);
        if (results.length === 0) setSearchErr(T.notFound);
      } catch {
        setSearchErr(T.notFound);
      }
    }, 300);
  };

  const handleGeolocate = () => {
    if (!navigator.geolocation) return;
    setGeoLoading(true);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const [lng, lat] = jitterCenter(pos.coords.longitude, pos.coords.latitude);
        setDraft({ lng, lat, label: '' });
        flyTo([lng, lat]);
        // Reverse geocode label in background
        try {
          const label = await geocodeReverse(lng, lat);
          setDraft({ lng, lat, label });
          setSearchVal(label);
        } catch { /* keep empty label */ }
        setGeoLoading(false);
      },
      () => {
        setSearchErr(T.geoErr);
        setGeoLoading(false);
      },
      { timeout: 8000 },
    );
  };

  const handleConfirm = () => {
    if (!draft) return;
    onConfirm(draft.label || searchVal, { lng: draft.lng, lat: draft.lat });
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-white flex flex-col"
      style={{ overscrollBehavior: 'none' }}
    >
      {/* Top header */}
      <div
        className="shrink-0 relative px-5 pb-3.5 bg-white"
        style={{ paddingTop: 'calc(44px + env(safe-area-inset-top, 0px))' }}
      >
        <h2 className="font-display text-[22px] font-semibold text-ink leading-tight mb-1 pr-10">
          {T.title}
        </h2>
        <p className="text-[13px] text-stone">{T.subtitle}</p>
        <Button className="absolute right-4 w-9 h-9 rounded-full bg-black/[.06] text-stone" type="button"
          onClick={onClose}
          aria-label="Close"
          style={{ top: 'calc(40px + env(safe-area-inset-top, 0px))' }}><svg width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <path d="M13 1L1 13M1 1l12 12" />
          </svg></Button>
      </div>

      {/* Map — flex:1 so it compresses when keyboard opens */}
      <div className="flex-1 min-h-[120px] px-3 pb-3 box-border overflow-hidden relative transition-all duration-300">
        <div className="rounded-sm overflow-hidden relative h-full border border-black/[.08]">
          <div ref={mapContainerRef} className="w-full h-full" />
          {/* Terra pin — centred on map */}
          {pinVisible && (
            <div
              className="absolute left-1/2 top-1/2 z-10 pointer-events-none"
              style={{ transform: 'translate(-50%, -100%)' }}
            >
              <svg width="32" height="40" viewBox="0 0 32 40" fill="none">
                <path d="M16 0C7.163 0 0 7.163 0 16c0 10.667 16 24 16 24S32 26.667 32 16C32 7.163 24.837 0 16 0Z" fill="var(--color-terracotta)" />
                <circle cx="16" cy="16" r="6" fill="white" />
              </svg>
            </div>
          )}
        </div>
      </div>

      {/* Bottom panel */}
      <div
        className="shrink-0 bg-white border-t border-border px-5 flex flex-col"
        style={{ paddingBottom: 'calc(24px + env(safe-area-inset-bottom, 0px))', paddingTop: '16px' }}
      >
        {confirmVisible && (
          <p className="text-[12px] text-stone text-center mb-3 leading-[1.45]">{T.privacyNote}</p>
        )}

        {/* Address input */}
        <Input
          type="text"
          value={searchVal}
          onChange={(e) => handleSearchChange(e.target.value)}
          placeholder={T.placeholder}
          className="w-full border border-border rounded-sm px-4 py-3.5 text-[16px] text-ink bg-cream outline-none focus:border-terracotta focus:bg-white transition-colors placeholder-muted"
          style={{ WebkitAppearance: 'none' }}
          autoComplete="off"
        />
        {searchErr && (
          <p className="text-[12px] text-red-500 mt-1">{searchErr}</p>
        )}

        {/* Autocomplete suggestions */}
        {showSuggestions && suggestions.length > 0 && (
          <div className="rounded-sm border border-border bg-white mt-1.5 max-h-[180px] overflow-y-auto shadow-md">
            {suggestions.map((s) => (
              <Button
                key={s.id}
                type="button"
                onClick={() => selectSuggestion(s)}
                className="w-full text-left px-4 py-3 text-[14px] text-ink border-b border-border last:border-0 hover:bg-cream transition-colors"
              >
                {s.place_name}
              </Button>
            ))}
          </div>
        )}

        {/* Use my location */}
        {!confirmVisible && (
          <Button variant="terracotta" fullWidth className="mt-2.5 py-3.5 border-terracotta text-terracotta text-[15px] active:scale-[.98] duration-150" type="button"
            onClick={handleGeolocate}
            disabled={geoLoading}><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="12" r="3" />
              <path d="M12 2v3M12 19v3M2 12h3M19 12h3" />
            </svg>
            {geoLoading ? (lang === 'es' ? 'Buscando…' : 'Finding…') : T.useLocation}</Button>
        )}

        {/* Confirm */}
        {confirmVisible && (
          <Button variant="terracotta" size="lg" fullWidth className="mt-2.5 text-[15px] active:scale-[.98] duration-150" type="button"
            onClick={handleConfirm}><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="20 6 9 17 4 12" />
            </svg>
            {T.confirm}</Button>
        )}
      </div>
    </div>
  );
}

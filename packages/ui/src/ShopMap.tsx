import { useEffect, useRef } from 'react';
import mapboxgl from 'mapbox-gl';
import 'mapbox-gl/dist/mapbox-gl.css';

export interface ShopMapPoint {
  id: string;
  name: string;
  lat: number;
  lon: number;
}

export interface ShopMapProps<T extends ShopMapPoint> {
  accessToken: string;
  points: T[];
  onSelect?: (point: T) => void;
  center?: [number, number];
  height?: string | number;
  className?: string;
  pinClassName?: string;
}

const SOFIA_CENTER: [number, number] = [23.3219, 42.6977];

export function ShopMap<T extends ShopMapPoint>({
  accessToken,
  points,
  onSelect,
  center,
  height = '100%',
  className,
  pinClassName = 'scope-shop-map-pin',
}: ShopMapProps<T>) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const markersRef = useRef<mapboxgl.Marker[]>([]);
  const initialCenter = center ?? (points.length ? [points[0].lon, points[0].lat] : SOFIA_CENTER);

  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;
    mapboxgl.accessToken = accessToken;
    mapRef.current = new mapboxgl.Map({
      container: containerRef.current,
      style: 'mapbox://styles/mapbox/light-v11',
      center: initialCenter,
      zoom: 12,
      attributionControl: false,
    });
    mapRef.current.addControl(new mapboxgl.NavigationControl({ visualizePitch: false }), 'top-right');
    return () => {
      markersRef.current.forEach((marker) => marker.remove());
      markersRef.current = [];
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current = points.map((point) => {
      const el = document.createElement('button');
      el.type = 'button';
      el.className = pinClassName;
      el.setAttribute('aria-label', point.name);
      el.addEventListener('click', () => onSelect?.(point));
      return new mapboxgl.Marker({ element: el, anchor: 'bottom' })
        .setLngLat([point.lon, point.lat])
        .addTo(map);
    });
    if (points.length > 1) {
      const bounds = new mapboxgl.LngLatBounds();
      points.forEach((point) => bounds.extend([point.lon, point.lat]));
      map.fitBounds(bounds, { padding: 46, maxZoom: 14, duration: 600 });
    } else if (points.length === 1) {
      map.flyTo({ center: [points[0].lon, points[0].lat], zoom: 14 });
    }
  }, [onSelect, pinClassName, points]);

  return <div className={className} style={{ height }} ref={containerRef} />;
}

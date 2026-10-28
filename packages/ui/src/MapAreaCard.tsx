import { useTranslation } from 'react-i18next';

interface MapAreaCardProps {
  mapImageSrc: string;
  mapImageAlt?: string;
  areaName: string;
  radiusLabel?: string;
  showApproxRing?: boolean;
  privacyNote?: string;
}

export function MapAreaCard({
  mapImageSrc,
  mapImageAlt = '',
  areaName,
  radiusLabel,
  showApproxRing = true,
  privacyNote,
}: MapAreaCardProps) {
  const { t } = useTranslation();
  const resolvedRadiusLabel = radiusLabel ?? t('map_radius_label');
  const resolvedPrivacyNote = privacyNote ?? t('map_privacy_note');
  return (
    <div className="rounded-[var(--r,8px)] overflow-hidden border border-border">
      {/* Map image with optional approx ring overlay */}
      <div className="relative h-[140px] overflow-hidden">
        <img
          src={mapImageSrc}
          alt={mapImageAlt}
          className="w-full h-full object-cover"
        />
        {showApproxRing && (
          <div
            className="absolute left-1/2 top-1/2 pointer-events-none z-10"
            style={{ transform: 'translate(-50%, -50%)' }}
            aria-hidden="true"
          >
            <div
              style={{
                width: 88,
                height: 88,
                borderRadius: '50%',
                background: 'rgba(218,101,77,0.22)',
                boxShadow: '0 0 0 2px rgba(218,101,77,0.55)',
              }}
            />
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="px-3.5 py-2.5 bg-white border-t border-black/[0.06]">
        <div className="text-[12px] font-semibold text-ink">{areaName}</div>
        {resolvedRadiusLabel && (
          <div className="text-[11px] text-muted mt-0.5">{resolvedRadiusLabel}</div>
        )}
        {resolvedPrivacyNote && (
          <div className="text-[10px] text-muted mt-2 leading-[1.45]">{resolvedPrivacyNote}</div>
        )}
      </div>
    </div>
  );
}

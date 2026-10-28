import type { DrawerState } from '../../lib/api';

export function CustomDrawerBody({ ds }: { ds: DrawerState }) {
  return (
    <div className="space-y-3 text-stone">
      {ds.custom_title ? (
        <h3 className="font-display text-lg font-semibold text-ink">{ds.custom_title}</h3>
      ) : null}
      {ds.custom_body ? (
        <p className="text-sm leading-relaxed whitespace-pre-wrap">{ds.custom_body}</p>
      ) : null}
    </div>
  );
}

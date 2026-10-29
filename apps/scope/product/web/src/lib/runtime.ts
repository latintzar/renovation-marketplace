/** Same product code, with an explicit recipient-owned local service transport. */
export const localMode = import.meta.env.VITE_LOCAL_MODE === '1';
export const appBase = import.meta.env.BASE_URL.replace(/\/$/, '');
export function appPath(path: string): string {
  return `${appBase}/${path.replace(/^\/app\/?/, '').replace(/^\//, '')}`;
}

/**
 * API base for HTTP requests. Empty string = same origin (local dev with Vite proxy).
 * On Vercel, set `VITE_API_ORIGIN` to your JARVIS API origin, e.g. `https://api.example.com`
 * (no trailing slash, no `/api` suffix — paths still use `/api/...`).
 */
export function apiUrl(path: string): string {
  const base = (import.meta.env.VITE_API_ORIGIN as string | undefined)?.replace(/\/$/, "") ?? "";
  const normalized = path.startsWith("/") ? path : `/${path}`;
  if (!base) return normalized;
  return `${base}${normalized}`;
}

/**
 * In Next.js we prefer same-origin calls (`/api/...`) and rely on rewrites
 * in `next.config.mjs` to reach the FastAPI backend.
 */
export function apiUrl(path: string): string {
  return path.startsWith("/") ? path : `/${path}`;
}


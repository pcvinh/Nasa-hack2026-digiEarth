import createClient from 'openapi-fetch';
import { API_BASE, USE_FIXTURES } from '../config';
import { fixtureFetch } from './fixtures/handler';
import type { paths } from './schema';

export const client = createClient<paths>({
  baseUrl: USE_FIXTURES ? 'http://fixture.local/api/v1' : API_BASE,
  ...(USE_FIXTURES ? { fetch: fixtureFetch } : {}),
});

/** Unwraps an openapi-fetch result: returns data or throws a readable error. */
export function unwrap<T>(r: { data?: T; error?: unknown }): T {
  if (r.data !== undefined) return r.data;
  const e = r.error as { error?: string } | undefined;
  throw new Error(e?.error ?? 'Request failed');
}

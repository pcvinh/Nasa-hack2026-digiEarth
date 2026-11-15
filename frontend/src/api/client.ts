import createClient from 'openapi-fetch';
import { API_BASE, USE_FIXTURES } from '../config';
import { fixtureFetch } from './fixtures/handler';
import type { paths } from './schema';

export const client = createClient<paths>({
  baseUrl: USE_FIXTURES ? 'http://fixture.local/api/v1' : API_BASE,
  ...(USE_FIXTURES ? { fetch: fixtureFetch } : {}),
});

/** Error body from the API (contract `Error`): `error` message and `code`. */
export class ApiError extends Error {
  constructor(message: string, readonly code?: string, readonly status?: number) { super(message); }
}

/** Unwraps an openapi-fetch result: returns data or throws an ApiError carrying the API's message. */
export function unwrap<T>(r: { data?: T; error?: unknown; response?: Response }): T {
  if (r.data !== undefined) return r.data;
  const e = r.error as { error?: string; code?: string } | undefined;
  throw new ApiError(e?.error ?? 'Request failed', e?.code, r.response?.status);
}

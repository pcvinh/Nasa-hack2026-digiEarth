import type { GuideRequest, GuideResponse, Session, SessionInput, TrendRequest } from '../types';
import { REGIONS, VARIABLES, buildTrend, lastCompleteYear, scenarioFor, trendMapFor } from './data';

/** Record of every fixture request, so tests can count calls. */
export const fixtureCalls: string[] = [];

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
const err = (status: number, code: string, error: string) => json({ error, code }, status);

const sessions = new Map<string, Session>();
let seq = 0;
const now = () => new Date().toISOString();

const cell = (lon: number, lat: number): [number, number, number, number] => {
  const w = Math.floor(lon / 0.5) * 0.5, s = Math.floor(lat / 0.5) * 0.5;
  return [w, s, w + 0.5, s + 0.5];
};

function analyze(req: TrendRequest): Response {
  const variable = VARIABLES.find((x) => x.id === req.variableId);
  if (!variable) return err(400, 'invalid_input', 'Unknown variable');
  if (variable.status === 'unavailable') return err(400, 'data_unavailable', variable.unavailableReason ?? 'Unavailable');
  const { presetId, point, bbox } = req.region;
  const start = req.startYear ?? 2001, end = req.endYear ?? lastCompleteYear(variable), alpha = req.alpha ?? 0.05;
  if (presetId) {
    const r = REGIONS.find((x) => x.id === presetId);
    if (!r) return err(404, 'not_found', 'Unknown region');
    return json(buildTrend(variable, r.name, r.bbox as [number, number, number, number], false, r.id, start, end, alpha, scenarioFor(`${variable.id}|${r.id}`)));
  }
  if (point) {
    const [lon, lat] = point as [number, number];
    // Fixture stand-in for open ocean (mid-Atlantic box): land-only variables have no data there.
    if (variable.id === 'soil_moisture' && lon > -40 && lon < -20 && lat > -20 && lat < 20) {
      return err(400, 'data_unavailable', 'No data for this point: it is over the ocean and this variable covers land only (SAMPLE message).');
    }
    const b = cell(lon, lat);
    return json(buildTrend(variable, `Cell at ${lon.toFixed(1)}°, ${lat.toFixed(1)}°`, b, true, null, start, end, alpha, scenarioFor(`${variable.id}|${b.join(',')}`)));
  }
  if (bbox) {
    const b = bbox as [number, number, number, number];
    return json(buildTrend(variable, 'Custom box', b, false, null, start, end, alpha, scenarioFor(`${variable.id}|${b.join(',')}`)));
  }
  return err(400, 'invalid_input', 'Provide presetId, bbox or point');
}

function guide(req: GuideRequest): GuideResponse {
  const region = REGIONS.find((r) => r.id === req.regionId);
  const ids = region?.suggestedVariableIds ?? ['precipitation', 'air_temperature'];
  const suggestions = ids.map((variableId) => ({ variableId, reason: '[SAMPLE] Fixture reason for suggesting this variable.' }));
  const first = ids[0]!;
  return {
    reply: `[SAMPLE] Fixture reply. Here are some variables you could investigate${region ? ` for ${region.name}` : ''}.`,
    suggestions,
    actions: [
      { type: 'select_variable', payload: { variableId: first } },
      { type: 'show_trend_map', payload: { variableId: first } },
    ],
    mode: 'rules',
  };
}

export async function fixtureFetch(input: Request | string | URL, init?: RequestInit): Promise<Response> {
  const req = input instanceof Request ? input : new Request(input, init);
  const url = new URL(req.url, 'http://fixture.local');
  const path = url.pathname.replace(/^.*\/api\/v1/, '');
  const method = req.method.toUpperCase();
  fixtureCalls.push(`${method} ${path}`);
  await new Promise((r) => setTimeout(r, 60));
  let m: RegExpMatchArray | null;

  if (method === 'GET' && path === '/health') return json({ status: 'ok', dataVersion: 'sample-fixture.0', variables: VARIABLES.map((v) => ({ id: v.id, status: v.status })) });
  if (method === 'GET' && path === '/variables') {
    const topic = url.searchParams.get('topic');
    return json({ items: VARIABLES.filter((v) => !topic || v.topic === topic) });
  }
  if (method === 'GET' && path === '/regions') {
    const q = (url.searchParams.get('q') ?? '').toLowerCase();
    return json({ items: REGIONS.filter((r) => !q || r.name.toLowerCase().includes(q) || (r.country ?? '').toLowerCase().includes(q)) });
  }
  if (method === 'GET' && (m = path.match(/^\/regions\/([^/]+)$/))) {
    const r = REGIONS.find((x) => x.id === m![1]);
    return r ? json(r) : err(404, 'not_found', 'Unknown region');
  }
  if (method === 'POST' && path === '/trends/analyze') return analyze((await req.json()) as TrendRequest);
  if (method === 'GET' && (m = path.match(/^\/trend-maps\/([^/]+)$/))) {
    return VARIABLES.some((v) => v.id === m![1]) ? json(trendMapFor(m[1]!)) : err(404, 'not_found', 'Unknown variable');
  }
  if (method === 'GET' && path.match(/^\/trend-maps\/[^/]+\/image\.png$/)) return fetch('/fixtures/trend-map-sample.png');
  if (method === 'POST' && path === '/guide/chat') return json(guide((await req.json()) as GuideRequest));
  if (method === 'GET' && path === '/sessions') {
    return json({ items: [...sessions.values()].reverse().map(({ id, title, createdAt, updatedAt }) => ({ id, title, createdAt, updatedAt })) });
  }
  if (method === 'POST' && path === '/sessions') {
    const body = (await req.json()) as SessionInput;
    const s: Session = { id: `sample-${++seq}`, title: body.title, state: body.state, createdAt: now(), updatedAt: now() };
    sessions.set(s.id, s);
    return json(s, 201);
  }
  if ((m = path.match(/^\/sessions\/([^/]+)$/))) {
    const s = sessions.get(m[1]!);
    if (!s) return err(404, 'not_found', 'Unknown session');
    if (method === 'GET') return json(s);
    if (method === 'PUT') {
      const body = (await req.json()) as SessionInput;
      const u = { ...s, title: body.title, state: body.state, updatedAt: now() };
      sessions.set(u.id, u);
      return json(u);
    }
  }
  return err(404, 'not_found', `No fixture for ${method} ${path}`);
}

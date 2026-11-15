// SAMPLE FIXTURES. Every value here is synthetic and exists only to exercise the UI.
// Nothing in this file is NASA data and none of it may be presented as such.
import type { Provenance, Region, TrendMap, TrendResult, Variable } from '../types';

const prov = (id: string, name: string): Provenance => ({
  datasetId: id, datasetVersion: 'sample', missionOrModel: name,
  sourceUrl: 'https://example.invalid/sample', doi: null, accessDate: '2026-01-01',
  processing: 'SAMPLE fixture, no processing', nativeResolution: 'n/a', servedResolution: '0.5°',
  citation: 'SAMPLE fixture. Not a real citation.',
});

const v = (id: string, name: string, topic: Variable['topic'], unit: string, annualUnit: string,
  agg: 'mean' | 'sum', def: string, why: string, unavailable?: string, coverageEnd = '2025-12'): Variable => ({
  id, name, topic, shortDefinition: def, whyItMatters: why, unit, annualUnit, annualAggregation: agg,
  coverage: { start: '2001-01', end: coverageEnd, landOnly: false },
  status: unavailable ? 'unavailable' : 'sample', unavailableReason: unavailable ?? null,
  provenance: prov(id, `${name} (sample)`),
});

export const VARIABLES: Variable[] = [
  v('precipitation', 'Rainfall', 'water', 'mm/month', 'mm/year', 'sum', 'How much rain and snow falls on the ground.', 'Water supply and flooding depend on it.', undefined, '2025-09'),
  v('soil_moisture', 'Topsoil moisture', 'water', 'kg/m²', 'kg/m²', 'mean', 'How wet the top few centimetres of soil are.', 'Plants take their water from here.'),
  v('air_temperature', 'Air temperature', 'heat', '°C', '°C', 'mean', 'Temperature of the air near the ground.', 'Heat affects people, crops and ecosystems.'),
  v('ndvi', 'Vegetation greenness', 'vegetation', 'unitless', 'unitless', 'mean', 'How green and leafy the land looks from space.', 'It shows where plants are growing well or struggling.'),
  v('no2', 'Nitrogen dioxide', 'air_quality', 'unitless', 'unitless', 'mean', 'A gas from traffic and industry.', 'It affects air quality.', 'Not ingested yet (sample reason).'),
];

const box = (w: number, s: number, e: number, n: number) => ({
  type: 'Polygon', coordinates: [[[w, s], [e, s], [e, n], [w, n], [w, s]]],
});
const reg = (id: string, name: string, country: string | null, regionType: Region['regionType'], description: string,
  b: [number, number, number, number], suggested: string[]): Region => ({
  id, name, country, regionType, description,
  center: [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2], bbox: b, geometry: box(...b),
  geometrySource: 'SAMPLE rectangle, not a real boundary', suggestedVariableIds: suggested,
});

// Ids, names, types and bounding boxes mirror the five presets listed in START-HERE.md / backend presets.
// Geometry is a rectangle (sample), not the real boundary.
export const REGIONS: Region[] = [
  reg('mekong-delta', 'Mekong Delta', 'Vietnam', 'river_delta', 'Low, flat river delta in southern Vietnam.',
    [103.838, 8.44, 106.8139, 11.0363], ['precipitation', 'soil_moisture', 'ndvi', 'air_temperature']),
  reg('central-java', 'Central Java', 'Indonesia', 'agricultural', 'Farming region in the middle of Java, Indonesia.',
    [108.612, -8.2118, 111.6772, -5.7257], ['precipitation', 'ndvi', 'soil_moisture', 'air_temperature']),
  reg('johor', 'Johor', 'Malaysia', 'agricultural', 'Farming state at the southern tip of Peninsular Malaysia.',
    [102.4709, 1.2662, 104.541, 2.9199], ['ndvi', 'precipitation', 'air_temperature', 'soil_moisture']),
  reg('amazon-central', 'Central Amazon', 'Brazil', 'rainforest', 'Dense rainforest around the central Amazon basin.',
    [-66.0, -7.0, -56.0, -1.0], ['precipitation', 'ndvi', 'air_temperature', 'soil_moisture']),
  reg('sahel', 'Sahel', null, 'desert_edge', 'Dry belt on the southern edge of the Sahara.',
    [-17.0, 12.0, 35.0, 18.0], ['precipitation', 'ndvi', 'soil_moisture', 'air_temperature']),
];

/** Last year with all 12 months available, from coverage.end ('YYYY-MM'). */
export function lastCompleteYear(v: Variable): number {
  const [y, m] = v.coverage.end.split('-').map(Number) as [number, number];
  return m === 12 ? y : y - 1;
}

export type Scenario = 'significant_up' | 'significant_down' | 'not_significant' | 'insufficient';
const SCENARIOS: Scenario[] = ['significant_up', 'not_significant', 'significant_down', 'insufficient'];

export function scenarioFor(key: string): Scenario {
  const table: Record<string, Scenario> = {
    'precipitation|mekong-delta': 'significant_up',
    'soil_moisture|mekong-delta': 'not_significant',
    'ndvi|amazon-central': 'significant_up',
    'air_temperature|amazon-central': 'significant_up',
    'precipitation|sahel': 'significant_down',
    'ndvi|sahel': 'not_significant',
  };
  const hit = table[key];
  if (hit) return hit;
  let h = 0;
  for (const c of key) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return SCENARIOS[h % SCENARIOS.length]!;
}

const round = (x: number) => Math.round(x * 100) / 100;

export function buildTrend(
  variable: Variable, name: string, bbox: [number, number, number, number], single: boolean,
  presetId: string | null, startYear: number, endYear: number, alpha: number, scenario: Scenario,
): TrendResult {
  const slope = scenario === 'significant_up' ? 1.2 : scenario === 'significant_down' ? -1.1 : 0.2;
  const p = scenario.startsWith('significant') ? 0.012 : 0.41;
  const insufficient = scenario === 'insufficient';
  const base = 100;
  const wobble = (i: number) => Math.sin(i * 1.7) * 3 + Math.cos(i * 0.9) * 2;
  const years: number[] = [];
  for (let y = startYear; y <= endYear; y++) years.push(y);
  const annual = years.map((y, i) => ({
    year: y,
    value: insufficient && i % 2 === 0 ? null : i === 3 ? null : round(base + slope * (i / 10) * 3 + wobble(i)),
  }));
  const monthly = years.flatMap((y, i) => Array.from({ length: 12 }, (_, m) => {
    const miss = m === 5 && i === 3;
    const seasonal = Math.sin((m / 12) * Math.PI * 2) * 10;
    const val = round(base / 12 + seasonal + slope * (i / 10) + wobble(i + m));
    return { time: `${y}-${String(m + 1).padStart(2, '0')}`, value: miss ? null : val, anomaly: miss ? null : round(wobble(i + m)), validCellFraction: single ? 1 : 0.9 };
  }));
  const line = (s: number) => [{ year: startYear, value: round(base + wobble(0)) }, { year: endYear, value: round(base + s * (endYear - startYear) / 10 + wobble(0)) }];
  const dir = slope > 0 ? 'increasing' : 'decreasing';
  const status = insufficient ? 'insufficient_data' : scenario === 'not_significant' ? 'not_significant' : 'significant';
  const na = insufficient;
  return {
    variableId: variable.id,
    region: { presetId, name, bbox, representativeness: single ? 'single_cell' : 'area_mean', cellCount: single ? 1 : 24, cellSize: '0.5°' },
    period: { startYear, endYear },
    unit: variable.unit, annualUnit: variable.annualUnit, dataStatus: 'sample',
    monthly, annual,
    totalChange: { value: na ? null : round(slope * (endYear - startYear) / 10), unit: variable.annualUnit },
    linear: { method: 'SAMPLE: OLS on annual values; two-sided t-test', slopePerDecade: na ? null : slope, ci95: na ? null : [round(slope - 0.9), round(slope + 0.9)], pValue: na ? null : p, rSquared: na ? null : 0.3, n: annual.filter((a) => a.value !== null).length },
    mannKendall: { method: "SAMPLE: Mann-Kendall with Sen's slope on annual values", senSlopePerDecade: na ? null : slope, tau: na ? null : 0.3, pValue: na ? null : p, n: annual.filter((a) => a.value !== null).length },
    trendLines: na ? { sen: [], ols: [] } : { sen: line(slope), ols: line(slope * 0.95) },
    significance: { alpha, status, direction: na ? 'no_change' : dir, agreement: na ? 'neither' : status === 'significant' ? 'both' : 'neither' },
    interpretation: {
      headline: na ? `[SAMPLE] ${variable.name}: not enough data in this fixture`
        : `[SAMPLE] ${variable.name} ${dir === 'increasing' ? 'increased' : 'decreased'}; ${status === 'significant' ? 'significant' : 'not significant'} in this fixture`,
      summary: '[SAMPLE] This sentence is fixture text standing in for the backend interpretation.',
      caveats: ['[SAMPLE] Fixture caveat: linear trend only.', '[SAMPLE] Fixture caveat: trend is not a cause.'],
    },
    provenance: prov(variable.id, `${variable.name} (sample)`),
    dataVersion: 'sample-fixture.0',
  };
}

export const trendMapFor = (variableId: string): TrendMap => ({
  variableId, period: { startYear: 2001, endYear: lastCompleteYear(VARIABLES.find((x) => x.id === variableId) ?? VARIABLES[0]!) },
  imageUrl: '/fixtures/trend-map-sample.png', bounds: [-180, -90, 180, 90], cellSize: '0.5°',
  legend: { min: -10, max: 10, unit: 'SAMPLE units per decade', palette: 'diverging_brown_green', fadedMeaning: 'SAMPLE: faded cells stand for "not significant"' },
  method: 'SAMPLE fixture image, not computed from data', dataStatus: 'sample',
  provenance: prov(variableId, 'Sample trend map'),
});

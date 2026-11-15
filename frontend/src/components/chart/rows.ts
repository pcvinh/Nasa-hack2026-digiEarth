import type { TrendResult } from '../../api/types';
import type { ChartMode } from '../../state/store';

export interface Row { x: string | number; value: number | null; sen?: number | null; ols?: number | null }

/** Builds chart rows. Null stays null so Recharts draws a gap (never 0). */
export function chartRows(r: TrendResult, mode: ChartMode): Row[] {
  if (mode === 'annual') {
    const sen = new Map(r.trendLines.sen.map((p) => [p.year, p.value]));
    const ols = new Map(r.trendLines.ols.map((p) => [p.year, p.value]));
    return r.annual.map((a) => ({ x: a.year, value: a.value, sen: sen.get(a.year) ?? null, ols: ols.get(a.year) ?? null }));
  }
  return r.monthly.map((m) => ({ x: m.time, value: mode === 'anomaly' ? m.anomaly : m.value }));
}

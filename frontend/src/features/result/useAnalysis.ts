import { useMemo } from 'react';
import { useTrend } from '../../api/queries';
import type { TrendRequest } from '../../api/types';
import { useStore } from '../../state/store';

export function useAnalysis() {
  const { variableId, region, startYear, endYear } = useStore();
  const request = useMemo<TrendRequest | null>(
    () => (variableId && region ? { variableId, region, startYear, endYear, alpha: 0.05 } : null),
    [variableId, region, startYear, endYear],
  );
  return { request, query: useTrend(request) };
}

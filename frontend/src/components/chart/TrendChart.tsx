import { CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import type { TrendResult } from '../../api/types';
import type { ChartMode } from '../../state/store';
import { chartRows } from './rows';

export function TrendChart({ result, mode }: { result: TrendResult; mode: ChartMode }) {
  const rows = chartRows(result, mode);
  const unit = mode === 'annual' ? result.annualUnit : result.unit;
  const label = mode === 'anomaly' ? `Anomaly (${result.unit})` : mode === 'annual' ? `Annual value (${unit})` : `Monthly value (${unit})`;
  return (
    <div style={{ width: '100%', height: 240 }} data-testid="trend-chart" role="img" aria-label={label}>
      <ResponsiveContainer>
        <ComposedChart data={rows} margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
          <CartesianGrid stroke="#e1e9f3" />
          <XAxis dataKey="x" tick={{ fontSize: 11 }} minTickGap={24} />
          <YAxis tick={{ fontSize: 11 }} width={44} domain={['auto', 'auto']} />
          <Tooltip />
          <Legend wrapperStyle={{ fontSize: 12 }} />
          <Line name={label} dataKey="value" stroke="#1557bf" strokeWidth={2} dot={mode === 'annual'} connectNulls={false} isAnimationActive={false} />
          {mode === 'annual' && <Line name="Sen's slope" dataKey="sen" stroke="#d97706" strokeWidth={2} strokeDasharray="6 4" dot={false} connectNulls isAnimationActive={false} />}
          {mode === 'annual' && <Line name="OLS line" dataKey="ols" stroke="#0f766e" strokeWidth={2} strokeDasharray="2 3" dot={false} connectNulls isAnimationActive={false} />}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

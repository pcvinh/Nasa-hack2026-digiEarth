import { render, screen } from '@testing-library/react';
import { VARIABLES, buildTrend, type Scenario } from '../../api/fixtures/data';
import { chartRows } from '../../components/chart/rows';
import { fmtP, fmtSig } from '../../components/common/format';
import { Result } from './Result';

vi.mock('../../components/chart/TrendChart', () => ({ TrendChart: () => <div /> }));
const make = (scenario: Scenario) =>
  buildTrend(VARIABLES[0]!, 'Test', [0, 0, 1, 1], false, null, 2001, 2025, 0.05, scenario);

describe('significance badge text', () => {
  it.each([
    ['significant_up', 'Significant'],
    ['not_significant', 'Not significant'],
    ['insufficient', 'Not enough data'],
  ] as const)('%s -> %s', (scenario, text) => {
    render(<Result result={make(scenario)} />);
    expect(screen.getByTestId('significance-badge')).toHaveTextContent(text);
  });
});

describe('nulls', () => {
  it('annual and monthly rows keep null (gap), never 0', () => {
    const r = make('significant_up');
    expect(r.annual.some((a) => a.value === null)).toBe(true);
    expect(chartRows(r, 'annual').filter((x) => x.value === null).length).toBeGreaterThan(0);
    expect(chartRows(r, 'monthly').some((x) => x.value === null)).toBe(true);
    expect(chartRows(r, 'anomaly').some((x) => x.value === null)).toBe(true);
  });
  it('null numbers display as a dash, not 0', () => {
    expect(fmtSig(null)).toBe('—');
    expect(fmtP(undefined)).toBe('—');
  });
});

describe('number display', () => {
  it('rounds to 2 significant figures and formats p-values', () => {
    expect(fmtSig(1.2345)).toBe('1.2');
    expect(fmtP(0.0004)).toBe('p < 0.001');
    expect(fmtP(0.034)).toBe('p = 0.03');
  });
});

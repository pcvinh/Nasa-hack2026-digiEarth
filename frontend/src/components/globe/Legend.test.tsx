import { render, screen } from '@testing-library/react';
import { trendMapFor } from '../../api/fixtures/data';
import { Legend } from './Legend';

const withStops = (colorStops?: string[]) => {
  const m = trendMapFor('precipitation');
  return { ...m, legend: { ...m.legend, ...(colorStops ? { colorStops } : {}) } };
};

describe('legend colours', () => {
  it('uses colorStops from the API when present', () => {
    render(<Legend map={withStops(['#112233', '#ffffff', '#445566'])} />);
    expect(screen.getByTestId('legend-bar').style.background).toContain('linear-gradient');
    expect(screen.getByTestId('legend-bar').style.background).toMatch(/rgb\(17, 34, 51\)|#112233/);
  });
  it('falls back to the palette name when colorStops are absent', () => {
    render(<Legend map={withStops()} />);
    expect(screen.getByTestId('legend-bar').getAttribute('style') ?? '').not.toContain('linear-gradient');
  });
});

describe('legend clamp note', () => {
  it('mentions the clamped west edge in the legend', () => {
    const m = withStops();
    render(<Legend map={{ ...m, bounds: [-180.3125, -90, 179.6875, 90] }} />);
    expect(screen.getByTestId('legend-clamp')).toHaveTextContent('clamped to -180');
  });
});

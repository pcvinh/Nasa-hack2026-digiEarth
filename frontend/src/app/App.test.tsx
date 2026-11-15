import { act, render, screen, waitFor, within } from '@testing-library/react';
import { App } from './App';
import { Providers } from './providers';
import { fixtureCalls } from '../api/fixtures/handler';
import { useStore } from '../state/store';

vi.mock('../config', () => ({ USE_FIXTURES: true, API_BASE: '/api/v1' }));
vi.mock('../components/globe/GlobeView', () => ({ default: () => <div data-testid="globe-stub" /> }));

const mount = () => render(<Providers><App /></Providers>);
const analyzeCount = () => fixtureCalls.filter((c) => c === 'POST /trends/analyze').length;

beforeEach(() => act(() => useStore.getState().reset()));

describe('App shell', () => {
  it('always shows the sample-data banner in fixture mode', () => {
    mount();
    expect(screen.getByTestId('sample-banner')).toHaveTextContent('SAMPLE DATA — not NASA results');
  });
  it('has nav, investigation panel and guide slots', () => {
    mount();
    expect(screen.getByRole('navigation', { name: 'Main' })).toBeInTheDocument();
    expect(screen.getByLabelText('Investigation')).toBeInTheDocument();
    expect(screen.queryByLabelText('Guide')).not.toBeInTheDocument(); // drawer starts closed
    act(() => useStore.getState().setGuideOpen(true));
    expect(screen.getByLabelText('Guide')).toBeInTheDocument();
  });
});

describe('analysis requests', () => {
  it('sends exactly one analyze request per variable or region change', async () => {
    mount();
    const before = analyzeCount();
    act(() => { useStore.getState().setRegion({ presetId: 'mekong-delta' }); });
    expect(analyzeCount()).toBe(before); // no variable yet
    act(() => { useStore.getState().setVariable('precipitation'); });
    await screen.findByTestId('verdict');
    expect(analyzeCount()).toBe(before + 1);
    act(() => { useStore.getState().setVariable('soil_moisture'); });
    await waitFor(() => expect(analyzeCount()).toBe(before + 2));
    await screen.findByTestId('verdict');
    expect(analyzeCount()).toBe(before + 2);
  });

  it('wizard reaches a result in 4 clicks', async () => {
    const { default: userEvent } = await import('@testing-library/user-event');
    const u = userEvent.setup();
    mount();
    await u.click(screen.getByRole('button', { name: 'Start investigation' }));          // 1
    const dlg = await screen.findByRole('dialog');
    await u.click(await within(dlg).findByRole('button', { name: /Central Amazon/ }));     // 2
    await u.click(await within(dlg).findByRole('button', { name: /Vegetation greenness/ })); // 3
    await u.click(within(dlg).getByRole('button', { name: 'Investigate' }));                  // 4
    expect(await screen.findByTestId('verdict')).toBeInTheDocument();
  });
});

describe('default period', () => {
  it('omits endYear from the request and shows the API period (rainfall ends before 2025)', async () => {
    mount();
    act(() => { useStore.getState().setRegion({ presetId: 'sahel' }); useStore.getState().setVariable('precipitation'); });
    expect(useStore.getState().endYear).toBeNull();
    await screen.findByTestId('verdict');
    expect(screen.getByText(/2001–2024/)).toBeInTheDocument();
  });
});

import { act } from '@testing-library/react';
import { fixtureFetch } from '../../api/fixtures/handler';
import { useStore } from '../../state/store';
import { openSession } from './Sessions';

vi.mock('../../config', () => ({ USE_FIXTURES: true, API_BASE: '/api/v1' }));

const post = (body: unknown) => fixtureFetch(new Request('http://x/api/v1/sessions', { method: 'POST', body: JSON.stringify(body), headers: { 'Content-Type': 'application/json' } }));

describe('session restore', () => {
  it('restores variable, region, period, map and chat', async () => {
    act(() => {
      const s = useStore.getState();
      s.reset(); s.setVariable('ndvi'); s.setRegion({ presetId: 'sahel' }); s.setShowTrendMap(true); s.setChartMode('anomaly');
      s.addGuideMessage({ role: 'user', text: 'hello' });
    });
    const saved = await (await post({ title: 't', state: useStore.getState().snapshot() })).json();
    act(() => useStore.getState().reset());
    await act(async () => { await openSession(saved.id); });
    const s = useStore.getState();
    expect([s.variableId, s.region, s.startYear, s.endYear, s.showTrendMap, s.chartMode, s.guideMessages.length])
      .toEqual(['ndvi', { presetId: 'sahel' }, 2001, 2025, true, 'anomaly', 1]);
  });
  it('opens empty with a message when saved state is invalid', async () => {
    const saved = await (await post({ title: 'bad', state: { nonsense: true } })).json();
    await act(async () => { await openSession(saved.id); });
    expect(useStore.getState().variableId).toBeNull();
    expect(useStore.getState().notice).toMatch(/could not be opened/);
  });
});

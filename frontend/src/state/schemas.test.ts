import { DEMOS } from '../demos';
import { parseActions, sessionStateSchema } from './schemas';

describe('action whitelist', () => {
  it('keeps whitelisted actions and drops unknown types', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
    const out = parseActions([
      { type: 'select_variable', payload: { variableId: 'ndvi' } },
      { type: 'delete_everything', payload: {} },
      { type: 'run_analysis', payload: { variableId: 'ndvi' } }, // bad payload
    ]);
    expect(out).toEqual([{ type: 'select_variable', payload: { variableId: 'ndvi' } }]);
    expect(warn).toHaveBeenCalledTimes(2);
    warn.mockRestore();
  });
});

describe('session state', () => {
  const state = {
    version: 1 as const, variableId: 'precipitation', region: { presetId: 'mekong-delta' }, startYear: 2001, endYear: 2025,
    showTrendMap: true, chartMode: 'monthly' as const,
    guideMessages: [{ role: 'user' as const, text: 'hi' }, { role: 'guide' as const, text: 'yo', mode: 'rules' as const }],
  };
  it('round-trips through JSON and Zod', () => {
    expect(sessionStateSchema.parse(JSON.parse(JSON.stringify(state)))).toEqual(state);
  });
  it('rejects invalid state', () => {
    expect(sessionStateSchema.safeParse({ ...state, version: 2 }).success).toBe(false);
    expect(sessionStateSchema.safeParse({ version: 1 }).success).toBe(false);
  });
});

describe('demo walkthrough text', () => {
  it('contains no digits', () => {
    for (const d of DEMOS) for (const s of [{ text: d.blurb, cta: d.title }, ...d.steps]) {
      expect(`${s.text} ${s.cta}`).not.toMatch(/\d/);
    }
  });
  it('every step action is whitelisted', () => {
    for (const d of DEMOS) expect(parseActions(d.steps.map((s) => s.action))).toHaveLength(d.steps.length);
  });
});

import { create } from 'zustand';
import type { GuideMessage, RegionSel, SafeAction, SessionState } from './schemas';

export type ChartMode = 'annual' | 'monthly' | 'anomaly';
export type View = 'explore' | 'demos' | 'saved';

interface State {
  view: View;
  variableId: string | null;
  region: RegionSel | null;
  startYear: number;
  /** null = let the API choose the variable's last complete year */
  endYear: number | null;
  showTrendMap: boolean;
  chartMode: ChartMode;
  guideMessages: GuideMessage[];
  guideOpen: boolean;
  wizardOpen: boolean;
  pickMode: boolean;
  sessionId: string | null;
  notice: string | null;
  demo: { id: string; step: number } | null;
  setView: (v: View) => void;
  setVariable: (id: string | null) => void;
  setRegion: (r: RegionSel | null) => void;
  setShowTrendMap: (b: boolean) => void;
  setChartMode: (m: ChartMode) => void;
  addGuideMessage: (m: GuideMessage) => void;
  setGuideOpen: (b: boolean) => void;
  setWizardOpen: (b: boolean) => void;
  setPickMode: (b: boolean) => void;
  setSessionId: (id: string | null) => void;
  setNotice: (n: string | null) => void;
  setDemo: (d: State['demo']) => void;
  runAction: (a: SafeAction) => void;
  snapshot: () => SessionState;
  restore: (s: SessionState, id: string | null) => void;
  reset: () => void;
}

const initial = {
  view: 'explore' as View, variableId: null, region: null, startYear: 2001, endYear: null as number | null,
  showTrendMap: false, chartMode: 'annual' as ChartMode, guideMessages: [] as GuideMessage[],
  guideOpen: false, wizardOpen: false, pickMode: false, sessionId: null, notice: null, demo: null,
};

export const useStore = create<State>((set, get) => ({
  ...initial,
  setView: (view) => set({ view }),
  setVariable: (variableId) => set({ variableId }),
  setRegion: (region) => set({ region, pickMode: false }),
  setShowTrendMap: (showTrendMap) => set({ showTrendMap }),
  setChartMode: (chartMode) => set({ chartMode }),
  addGuideMessage: (m) => set((s) => ({ guideMessages: [...s.guideMessages, m] })),
  setGuideOpen: (guideOpen) => set({ guideOpen }),
  setWizardOpen: (wizardOpen) => set({ wizardOpen }),
  setPickMode: (pickMode) => set({ pickMode }),
  setSessionId: (sessionId) => set({ sessionId }),
  setNotice: (notice) => set({ notice }),
  setDemo: (demo) => set({ demo }),
  runAction: (a) => {
    switch (a.type) {
      case 'select_variable': set({ variableId: a.payload.variableId }); break;
      case 'select_region': set({ region: a.payload, pickMode: false }); break;
      case 'run_analysis': set({ variableId: a.payload.variableId, region: a.payload.region, pickMode: false }); break;
      case 'show_trend_map': set({ variableId: a.payload.variableId, showTrendMap: true }); break;
    }
  },
  snapshot: () => {
    const s = get();
    return { version: 1, variableId: s.variableId, region: s.region, startYear: s.startYear, endYear: s.endYear,
      showTrendMap: s.showTrendMap, chartMode: s.chartMode, guideMessages: s.guideMessages };
  },
  restore: (st, id) => set({ ...initial, variableId: st.variableId, region: st.region, startYear: st.startYear,
    endYear: st.endYear, showTrendMap: st.showTrendMap, chartMode: st.chartMode, guideMessages: st.guideMessages, guideOpen: st.guideMessages.length > 0, sessionId: id }),
  reset: () => set({ ...initial }),
}));

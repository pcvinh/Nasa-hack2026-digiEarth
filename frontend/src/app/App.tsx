import { lazy, Suspense, useEffect, useMemo } from 'react';
import { useRegion, useTrendMap, useVariables } from '../api/queries';
import { asBBox, type BBox, type LonLat } from '../api/types';
import { Legend } from '../components/globe/Legend';
import { Shell } from '../components/layout/Shell';
import { DemoCard, DemoList } from '../features/demos/Demos';
import { GuideDrawer } from '../features/guide/GuideDrawer';
import { Result } from '../features/result/Result';
import { useAnalysis } from '../features/result/useAnalysis';
import { SaveButton, SavedList, openSession } from '../features/sessions/Sessions';
import { VariableCards } from '../features/wizard/Pickers';
import { TopBar } from '../features/wizard/TopBar';
import { Wizard } from '../features/wizard/Wizard';
import { useStore } from '../state/store';
import styles from '../styles/ui.module.css';

const GlobeView = lazy(() => import('../components/globe/GlobeView'));

function ExplorePanel() {
  const { region, variableId, setVariable } = useStore();
  const variables = useVariables();
  const { query } = useAnalysis();
  const presetId = region && 'presetId' in region ? region.presetId : null;
  const reg = useRegion(presetId);
  if (!region && !variableId) return <p className={styles.sub}>Choose a place and a variable, or click anywhere on the globe, to begin.</p>;
  return (
    <div>
      {region && !variableId && (
        <>
          <h2 className={styles.h2}>What do you want to investigate?</h2>
          <VariableCards variables={variables.data ?? []} selectedId={null} suggestedIds={reg.data?.suggestedVariableIds ?? []} onSelect={(v) => setVariable(v.id)} />
        </>
      )}
      {variableId && !region && <p className={styles.sub}>Now choose a place: search a region, use the wizard, or click the globe.</p>}
      {query.isFetching && <p>Analysing…</p>}
      {query.error && <div className={styles.error}>{query.error.message}</div>}
      {query.data && !query.isFetching && (
        <>
          <div style={{ marginBottom: 8 }}>
            <SaveButton title={`${variables.data?.find((v) => v.id === variableId)?.name ?? variableId} @ ${query.data.region.name}`} />
          </div>
          <Result result={query.data} />
        </>
      )}
    </div>
  );
}

function GlobeContainer() {
  const { region, variableId, showTrendMap, pickMode, setRegion, setNotice } = useStore();
  const presetId = region && 'presetId' in region ? region.presetId : null;
  const reg = useRegion(presetId);
  const { query } = useAnalysis();
  const map = useTrendMap(variableId, showTrendMap);
  const flyTo = useMemo<BBox | null>(() => {
    if (reg.data) return asBBox(reg.data.bbox);
    if (region && 'point' in region) return [region.point[0] - 2, region.point[1] - 2, region.point[0] + 2, region.point[1] + 2];
    return null;
  }, [reg.data, region]);
  const overlay = useMemo(() => (showTrendMap && map.data ? { url: map.data.imageUrl, bounds: asBBox(map.data.bounds) } : null), [showTrendMap, map.data]);
  const onPick = (p: LonLat) => {
    setRegion({ point: p });
    if (!useStore.getState().variableId) setNotice('Point selected. Choose a variable to analyse it.');
    else setNotice(null);
  };
  return (
    <>
      <Suspense fallback={<div style={{ color: '#fff', padding: 16 }}>Loading globe…</div>}>
        <GlobeView outline={reg.data?.geometry ?? null} cell={query.data ? asBBox(query.data.region.bbox) : null}
          flyTo={flyTo} overlay={overlay} pickMode={pickMode} onPick={onPick} />
      </Suspense>
      {showTrendMap && map.data && <Legend map={map.data} />}
      {showTrendMap && map.error && <div className={styles.error} style={{ position: 'absolute', right: 12, bottom: 36 }}>Trend map unavailable.</div>}
      <DemoCard />
    </>
  );
}

export function App() {
  const { view, notice, setNotice, wizardOpen } = useStore();
  useEffect(() => {
    const m = window.location.pathname.match(/^\/s\/([^/]+)$/);
    if (m) void openSession(m[1]!);
  }, []);
  const panel = (
    <>
      {notice && <div className={styles.notice} role="status">{notice} <button className={styles.btnGhost} style={{ padding: '2px 8px' }} onClick={() => setNotice(null)}>Dismiss</button></div>}
      {view === 'explore' && <ExplorePanel />}
      {view === 'demos' && <DemoList />}
      {view === 'saved' && <SavedList />}
    </>
  );
  return (
    <>
      <Shell topBar={<TopBar />} panel={panel} globe={<GlobeContainer />} drawer={<GuideDrawer />} />
      {wizardOpen && <Wizard />}
    </>
  );
}

import { useState } from 'react';
import { useRegions, useVariables } from '../../api/queries';
import { useStore } from '../../state/store';
import styles from '../../styles/ui.module.css';
import { RegionCards, VariableCards } from './Pickers';

export function Wizard() {
  const { region, variableId, setRegion, setVariable, setWizardOpen, setPickMode, setNotice } = useStore();
  const regions = useRegions();
  const variables = useVariables();
  const [step, setStep] = useState(1);
  const presetId = region && 'presetId' in region ? region.presetId : null;
  const suggested = regions.data?.find((r) => r.id === presetId)?.suggestedVariableIds ?? [];
  const close = () => setWizardOpen(false);

  return (
    <div className={styles.overlay} role="dialog" aria-modal="true" aria-label="Start investigation">
      <div className={styles.modal}>
        <div className={styles.row} style={{ justifyContent: 'space-between' }}>
          <h2 className={styles.h2}>Step {step} of 3: {step === 1 ? 'Where?' : step === 2 ? 'What?' : 'Investigate'}</h2>
          <button className={styles.btnGhost} onClick={close}>Close</button>
        </div>
        {step === 1 && (
          <>
            <p className={styles.sub}>Choose a place to investigate.</p>
            {regions.isLoading && <p>Loading regions…</p>}
            {regions.error && <div className={styles.error}>Could not load regions.</div>}
            <RegionCards regions={regions.data ?? []} selectedId={presetId} onSelect={(r) => { setRegion({ presetId: r.id }); setStep(2); }} />
            <p style={{ marginTop: 12 }}>
              <button className={styles.btnGhost} onClick={() => { setPickMode(true); setNotice('Click anywhere on the globe to pick a point.'); close(); }}>Pick a point on the globe</button>
            </p>
          </>
        )}
        {step === 2 && (
          <>
            <p className={styles.sub}>Choose what to investigate.</p>
            {variables.isLoading && <p>Loading variables…</p>}
            {variables.error && <div className={styles.error}>Could not load variables.</div>}
            <VariableCards variables={variables.data ?? []} selectedId={variableId} suggestedIds={suggested} onSelect={(v) => { setVariable(v.id); setStep(3); }} />
          </>
        )}
        {step === 3 && (
          <>
            <p>Ready to look at <strong>{variables.data?.find((v) => v.id === variableId)?.name}</strong> in <strong>{regions.data?.find((r) => r.id === presetId)?.name}</strong>.</p>
            <div className={styles.row}>
              <button className={styles.btnGhost} onClick={() => setStep(2)}>Back</button>
              <button className={styles.btn} onClick={close}>Investigate</button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

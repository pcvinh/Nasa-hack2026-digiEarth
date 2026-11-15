import { useState } from 'react';
import { useRegions, useVariables } from '../../api/queries';
import { useStore } from '../../state/store';
import styles from '../../styles/ui.module.css';

export function TopBar() {
  const { variableId, setVariable, setRegion, setWizardOpen } = useStore();
  const regions = useRegions();
  const variables = useVariables();
  const [q, setQ] = useState('');
  const hits = q.trim()
    ? (regions.data ?? []).filter((r) => `${r.name} ${r.country ?? ''}`.toLowerCase().includes(q.trim().toLowerCase()))
    : [];
  return (
    <div className={styles.row} style={{ flex: 1 }}>
      <strong style={{ marginRight: 8 }}>Trend Detective</strong>
      <div className={styles.topSearch}>
        <input className={styles.input} placeholder="Search regions" aria-label="Search regions" value={q} onChange={(e) => setQ(e.target.value)} />
        {hits.length > 0 && (
          <div className={styles.dropdown}>
            {hits.map((r) => (
              <button key={r.id} onClick={() => { setRegion({ presetId: r.id }); setQ(''); }}>{r.name}{r.country ? `, ${r.country}` : ''}</button>
            ))}
          </div>
        )}
      </div>
      <select className={styles.input} style={{ width: 200 }} aria-label="Variable" value={variableId ?? ''} onChange={(e) => setVariable(e.target.value || null)}>
        <option value="">Choose a variable</option>
        {(variables.data ?? []).map((v) => <option key={v.id} value={v.id} disabled={v.status === 'unavailable'}>{v.name}{v.status === 'unavailable' ? ' (unavailable)' : ''}</option>)}
      </select>
      <button className={styles.btn} onClick={() => setWizardOpen(true)}>Start investigation</button>
    </div>
  );
}

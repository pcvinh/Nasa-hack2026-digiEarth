import type { Region, Variable } from '../../api/types';
import styles from '../../styles/ui.module.css';

const TOPIC: Record<string, string> = { water: 'Water', heat: 'Heat', vegetation: 'Vegetation', air_quality: 'Air quality' };

export function RegionCards({ regions, selectedId, onSelect }: { regions: Region[]; selectedId: string | null; onSelect: (r: Region) => void }) {
  return (
    <div className={styles.cards}>
      {regions.map((r) => (
        <button key={r.id} className={styles.pick} aria-pressed={selectedId === r.id} onClick={() => onSelect(r)}>
          <span className={styles.pickName}>{r.name}</span>
          <span className={styles.pickDesc}>{r.regionType.replace('_', ' ')} · {r.description}</span>
        </button>
      ))}
    </div>
  );
}

export function VariableCards({ variables, selectedId, suggestedIds, onSelect }: {
  variables: Variable[]; selectedId: string | null; suggestedIds: string[]; onSelect: (v: Variable) => void;
}) {
  const topics = [...new Set(variables.map((v) => v.topic))];
  return (
    <div>
      {topics.map((t) => (
        <div key={t}>
          <h3 style={{ fontSize: 13, color: 'var(--muted)', margin: '10px 0 4px' }}>{TOPIC[t] ?? t}</h3>
          <div className={styles.cards}>
            {variables.filter((v) => v.topic === t).map((v) => {
              const off = v.status === 'unavailable';
              return (
                <button key={v.id} className={styles.pick} disabled={off} aria-pressed={selectedId === v.id} onClick={() => onSelect(v)}>
                  <span className={styles.pickName}>
                    {v.name}
                    {suggestedIds.includes(v.id) && !off && <span className={styles.badge} style={{ marginLeft: 8 }}>Suggested for this region</span>}
                  </span>
                  <span className={styles.pickDesc}>{off ? `Unavailable: ${v.unavailableReason ?? 'no reason given'}` : v.shortDefinition}</span>
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}

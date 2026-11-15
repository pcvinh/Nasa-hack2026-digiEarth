import type { TrendMap } from '../../api/types';
import { asBBox } from '../../api/types';
import { fmtSig } from '../common/format';
import { clampNote } from './geo';
import styles from '../../styles/ui.module.css';

export function Legend({ map }: { map: TrendMap }) {
  const { legend, period } = map;
  // Prefer the API's colours (same palette as the PNG); fall back to the palette name when absent.
  const stops = legend.colorStops && legend.colorStops.length >= 2 ? legend.colorStops : null;
  return (
    <div className={styles.legend} data-testid="legend">
      <strong>Trend per decade · {period.startYear}–{period.endYear}</strong>
      <div data-testid="legend-bar" className={stops ? styles.gradBar : legend.palette === 'diverging_brown_green' ? styles.gradBrownGreen : styles.gradBlueRed}
        style={{ marginTop: 6, ...(stops ? { background: `linear-gradient(90deg, ${stops.join(', ')})` } : {}) }} />
      <div className={styles.legendScale}><span>{fmtSig(legend.min)}</span><span>{legend.unit}</span><span>{fmtSig(legend.max)}</span></div>
      <div style={{ marginTop: 4 }}>Faded: {legend.fadedMeaning}</div>
      {clampNote(asBBox(map.bounds)) && <div data-testid="legend-clamp">{clampNote(asBBox(map.bounds))}</div>}
      {map.dataStatus === 'sample' && <div style={{ color: '#b42318', fontWeight: 700 }}>SAMPLE DATA</div>}
    </div>
  );
}

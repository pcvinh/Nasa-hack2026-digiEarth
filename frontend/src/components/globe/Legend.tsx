import type { TrendMap } from '../../api/types';
import { fmtSig } from '../common/format';
import styles from '../../styles/ui.module.css';

export function Legend({ map }: { map: TrendMap }) {
  const { legend, period } = map;
  return (
    <div className={styles.legend} data-testid="legend">
      <strong>Trend per decade · {period.startYear}–{period.endYear}</strong>
      <div className={legend.palette === 'diverging_brown_green' ? styles.gradBrownGreen : styles.gradBlueRed} style={{ marginTop: 6 }} />
      <div className={styles.legendScale}><span>{fmtSig(legend.min)}</span><span>{legend.unit}</span><span>{fmtSig(legend.max)}</span></div>
      <div style={{ marginTop: 4 }}>Faded: {legend.fadedMeaning}</div>
      {map.dataStatus === 'sample' && <div style={{ color: '#b42318', fontWeight: 700 }}>SAMPLE DATA</div>}
    </div>
  );
}

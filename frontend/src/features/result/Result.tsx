import { useState } from 'react';
import type { TrendResult } from '../../api/types';
import { TrendChart } from '../../components/chart/TrendChart';
import { NA, fmtP, fmtSig, fmtSigned } from '../../components/common/format';
import { useStore, type ChartMode } from '../../state/store';
import styles from '../../styles/ui.module.css';

const STATUS_TEXT = { significant: 'Significant', not_significant: 'Not significant', insufficient_data: 'Not enough data' } as const;
const AGREE_TEXT = {
  both: 'Both methods agree: trend found.',
  mann_kendall_only: 'Only Mann-Kendall finds a trend.',
  ols_only: 'Only the t-test (OLS) finds a trend.',
  neither: 'Neither method finds a significant trend.',
} as const;
const DIR_TEXT = { increasing: 'Increasing', decreasing: 'Decreasing', no_change: 'No change' } as const;

export function SignificanceBadge({ status }: { status: keyof typeof STATUS_TEXT }) {
  const mark = status === 'significant' ? '✔' : status === 'not_significant' ? '≈' : '?';
  return <span className={styles.badge} data-testid="significance-badge">{mark} {STATUS_TEXT[status]}</span>;
}

export function representativeness(r: TrendResult['region']): string {
  return r.representativeness === 'single_cell'
    ? `Single ${r.cellSize ?? ''} cell, about 55 km across`.replace('  ', ' ')
    : `Average of ${r.cellCount} cells of ${r.cellSize ?? ''}`.trim();
}

const MODES: [ChartMode, string][] = [['annual', 'Annual'], ['monthly', 'Monthly'], ['anomaly', 'Monthly anomaly']];

export function Result({ result }: { result: TrendResult }) {
  const { chartMode, setChartMode, setShowTrendMap, setGuideOpen } = useStore();
  const [explain, setExplain] = useState(false);
  const s = result.significance;
  const enough = s.status !== 'insufficient_data';
  const p = result.provenance;
  return (
    <div>
      <h2 className={styles.h2}>{result.region.name}</h2>
      <p className={styles.sub}>
        {result.period.startYear}–{result.period.endYear} · {representativeness(result.region)}
      </p>
      <div className={styles.row} style={{ marginBottom: 8 }}>
        <span className={result.dataStatus === 'source_backed' ? styles.badge : styles.badgeSample} data-testid="data-status">
          {result.dataStatus === 'source_backed' ? 'Source-backed NASA data' : result.dataStatus === 'sample' ? 'SAMPLE DATA' : 'Unavailable'}
        </span>
      </div>

      <div className={styles.card} data-testid="verdict">
        <strong>{result.interpretation.headline}</strong>
        <p style={{ margin: '6px 0' }}>{result.interpretation.summary}</p>
        <div className={styles.row}><SignificanceBadge status={s.status} /><span>{DIR_TEXT[s.direction]}</span></div>
        <div className={styles.stats}>
          <div className={styles.stat}><small>Change per decade (Sen)</small><span className={styles.big}>{fmtSigned(result.mannKendall.senSlopePerDecade)}</span><small>{result.annualUnit} per decade</small></div>
          <div className={styles.stat}><small>Total change</small><span className={styles.big}>{fmtSigned(result.totalChange.value)}</span><small>{result.totalChange.unit}</small></div>
          <div className={styles.stat}><small>Mann-Kendall</small><span className={styles.big}>{fmtP(result.mannKendall.pValue).replace('p ', 'p ')}</span><small>α = {s.alpha}</small></div>
        </div>
        <small>{AGREE_TEXT[s.agreement]}</small>
      </div>

      <div className={styles.tabs} role="group" aria-label="Chart view">
        {MODES.map(([m, label]) => (
          <button key={m} className={styles.tab} aria-pressed={chartMode === m} onClick={() => setChartMode(m)}>{label}</button>
        ))}
      </div>
      <TrendChart result={result} mode={chartMode} />

      <button className={styles.btnGhost} onClick={() => setExplain((e) => !e)} aria-expanded={explain} style={{ margin: '8px 0' }}>
        What does “significant” mean?
      </button>
      {explain && (
        <div className={styles.card}>
          <p style={{ marginTop: 0 }}>The p-value is the chance of seeing a trend at least this strong if nothing was really changing. If p is below the threshold α (here {s.alpha}), we call the trend statistically significant.</p>
          <p style={{ marginBottom: 0 }}>A trend can be real but not yet significant: with few years of data or lots of year-to-year noise, the test may not be able to tell the trend from chance.</p>
        </div>
      )}

      {enough && (
        <div className={styles.card} data-testid="details">
          <strong>Details</strong>
          <ul className={styles.list}>
            <li>OLS slope: {fmtSigned(result.linear.slopePerDecade)} {result.annualUnit} per decade{result.linear.ci95 ? `, 95% CI ${fmtSig(result.linear.ci95[0])} to ${fmtSig(result.linear.ci95[1])}` : ''}</li>
            <li>t-test: {fmtP(result.linear.pValue)}</li>
            <li>Mann-Kendall τ: {fmtSig(result.mannKendall.tau)}</li>
            <li>Years used (n): {result.mannKendall.n}</li>
          </ul>
        </div>
      )}
      {!enough && <div className={styles.notice}>{NA} Not enough valid years to test a trend here.</div>}

      <div className={styles.card}>
        <strong>Source</strong>
        <p className={styles.sourceTxt}>{p.missionOrModel} · {p.datasetId} v{p.datasetVersion} · accessed {p.accessDate}<br />{p.processing}<br />{p.citation}<br /><a href={p.sourceUrl} target="_blank" rel="noreferrer">Source link</a></p>
        <strong>Caveats</strong>
        <ul className={styles.list}>{result.interpretation.caveats.map((c) => <li key={c}>{c}</li>)}</ul>
      </div>

      <div className={styles.row}>
        <button className={styles.btn} onClick={() => setShowTrendMap(true)}>Show trend map</button>
        <button className={styles.btnGhost} onClick={() => setGuideOpen(true)}>Ask the Guide</button>
      </div>
    </div>
  );
}

import { useState, type ReactNode } from 'react';
import { useStore, type View } from '../../state/store';
import { USE_FIXTURES } from '../../config';
import { SampleBanner } from './SampleBanner';
import styles from './Shell.module.css';

const NAV: [View, string][] = [['explore', 'Explore'], ['demos', 'Demos'], ['saved', 'Saved sessions']];

interface ShellProps {
  topBar?: ReactNode;
  panel?: ReactNode;
  globe?: ReactNode;
  drawer?: ReactNode;
}

export function Shell({ topBar, panel, globe, drawer }: ShellProps) {
  const [collapsed, setCollapsed] = useState(false);
  const { view, setView, guideOpen, setGuideOpen } = useStore();
  return (
    <div className={styles.root}>
      {USE_FIXTURES && <SampleBanner />}
      <div className={styles.body}>
        <nav className={styles.nav} data-collapsed={collapsed} aria-label="Main">
          <button className={styles.toggle} onClick={() => setCollapsed((c) => !c)} aria-label="Collapse navigation">
            ☰
          </button>
          {NAV.map(([id, label]) => (
            <button key={id} className={styles.navItem} aria-current={view === id} onClick={() => setView(id)}>{collapsed ? label[0] : label}</button>
          ))}
        </nav>
        <div className={styles.main}>
          <header className={styles.top}>
            {topBar ?? <strong>Trend Detective</strong>}
            <button onClick={() => setGuideOpen(!guideOpen)} aria-expanded={guideOpen}>Guide</button>
          </header>
          <div className={styles.work}>
            <section className={styles.panel} aria-label="Investigation">{panel}</section>
            <section className={styles.globe} aria-label="Globe">{globe}</section>
          </div>
        </div>
        {guideOpen && <aside className={styles.drawer} aria-label="Guide">{drawer}</aside>}
      </div>
    </div>
  );
}

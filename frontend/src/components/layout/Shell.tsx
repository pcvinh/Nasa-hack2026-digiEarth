import { useState, type ReactNode } from 'react';
import { USE_FIXTURES } from '../../config';
import { SampleBanner } from './SampleBanner';
import styles from './Shell.module.css';

const NAV = ['Explore', 'Demos', 'Saved sessions'] as const;

interface ShellProps {
  topBar?: ReactNode;
  panel?: ReactNode;
  globe?: ReactNode;
  drawer?: ReactNode;
}

export function Shell({ topBar, panel, globe, drawer }: ShellProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(true);
  return (
    <div className={styles.root}>
      {USE_FIXTURES && <SampleBanner />}
      <div className={styles.body}>
        <nav className={styles.nav} data-collapsed={collapsed} aria-label="Main">
          <button className={styles.toggle} onClick={() => setCollapsed((c) => !c)} aria-label="Collapse navigation">
            ☰
          </button>
          {NAV.map((n) => (
            <button key={n} className={styles.navItem}>{collapsed ? n[0] : n}</button>
          ))}
        </nav>
        <div className={styles.main}>
          <header className={styles.top}>
            {topBar ?? <strong>Trend Detective</strong>}
            <button onClick={() => setDrawerOpen((o) => !o)} aria-expanded={drawerOpen}>Guide</button>
          </header>
          <div className={styles.work}>
            <section className={styles.panel} aria-label="Investigation">{panel}</section>
            <section className={styles.globe} aria-label="Globe">{globe}</section>
          </div>
        </div>
        {drawerOpen && <aside className={styles.drawer} aria-label="Guide">{drawer}</aside>}
      </div>
    </div>
  );
}

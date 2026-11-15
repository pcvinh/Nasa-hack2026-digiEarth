import { useState } from 'react';
import { DEMOS } from '../../demos';
import { useStore } from '../../state/store';
import styles from '../../styles/ui.module.css';

export function DemoList() {
  const { setDemo, setView } = useStore();
  return (
    <div>
      <h2 className={styles.h2}>Demo walkthroughs</h2>
      <p className={styles.sub}>Guided investigations. The numbers always come from the live analysis.</p>
      <div className={styles.cards}>
        {DEMOS.map((d) => (
          <button key={d.id} className={styles.pick} onClick={() => { setDemo({ id: d.id, step: 0 }); setView('explore'); }}>
            <span className={styles.pickName}>{d.title}</span><span className={styles.pickDesc}>{d.blurb}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

export function DemoCard() {
  const { demo, setDemo, runAction } = useStore();
  const [done, setDone] = useState<string | null>(null);
  if (!demo) return null;
  const d = DEMOS.find((x) => x.id === demo.id);
  const step = d?.steps[demo.step];
  if (!d || !step) return null;
  const key = `${d.id}:${demo.step}`;
  const last = demo.step === d.steps.length - 1;
  return (
    <div className={styles.demoCard} role="region" aria-label="Demo walkthrough">
      <small>{d.title} · step {demo.step + 1} of {d.steps.length}</small>
      <p style={{ margin: '6px 0 10px' }}>{step.text}</p>
      <div className={styles.row}>
        <button className={styles.btn} onClick={() => { runAction(step.action); setDone(key); }}>{step.cta}</button>
        <button className={styles.btnGhost} disabled={done !== key} onClick={() => (last ? setDemo(null) : setDemo({ id: d.id, step: demo.step + 1 }))}>{last ? 'Finish' : 'Next step'}</button>
        <button className={styles.btnGhost} onClick={() => setDemo(null)}>Exit</button>
      </div>
    </div>
  );
}

import { useState, type FormEvent } from 'react';
import { useGuideChat, useVariables } from '../../api/queries';
import { parseActions, type SafeAction } from '../../state/schemas';
import { useStore } from '../../state/store';
import styles from '../../styles/ui.module.css';

const LABEL: Record<SafeAction['type'], string> = {
  select_variable: 'Select variable', select_region: 'Select region', run_analysis: 'Run analysis', show_trend_map: 'Show trend map',
};

export function GuideDrawer() {
  const { guideMessages, addGuideMessage, region, variableId, runAction } = useStore();
  const chat = useGuideChat();
  const variables = useVariables();
  const [text, setText] = useState('');
  const name = (id: string) => variables.data?.find((v) => v.id === id)?.name ?? id;

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const message = text.trim();
    if (!message) return;
    setText('');
    addGuideMessage({ role: 'user', text: message });
    chat.mutate(
      { message, regionId: region && 'presetId' in region ? region.presetId : null, variableId },
      { onSuccess: (r) => addGuideMessage({ role: 'guide', text: r.reply, mode: r.mode, suggestions: r.suggestions, actions: parseActions(r.actions) }) },
    );
  };

  const last = [...guideMessages].reverse().find((m) => m.role === 'guide');
  return (
    <div>
      <h2 className={styles.h2}>Detective Guide</h2>
      {last?.mode === 'rules' && <span className={styles.badge}>Rules-based guide</span>}
      {last?.mode === 'llm' && <span className={styles.badge}>AI-worded guide</span>}
      <p className={styles.sub}>Ask which variables could help you investigate a place.</p>
      <div className={styles.chat} aria-live="polite">
        {guideMessages.map((m, i) => (
          <div key={i} className={m.role === 'user' ? styles.msgUser : styles.msgGuide}>
            <div>{m.text}</div>
            {m.suggestions?.map((s) => (
              <div key={s.variableId}>
                <button className={styles.chip} onClick={() => runAction({ type: 'select_variable', payload: { variableId: s.variableId } })}>{name(s.variableId)}</button>
                <small> {s.reason}</small>
              </div>
            ))}
            {m.actions?.map((a, j) => <button key={j} className={styles.chip} onClick={() => runAction(a)}>{LABEL[a.type]}</button>)}
          </div>
        ))}
        {chat.isPending && <div className={styles.msgGuide}>Thinking…</div>}
        {chat.isError && <div className={styles.error}>The Guide could not answer. Try again.</div>}
      </div>
      <form onSubmit={submit} className={styles.row}>
        <input className={styles.input} style={{ flex: 1 }} aria-label="Message the Guide" placeholder="e.g. What should I look at in a delta?" value={text} onChange={(e) => setText(e.target.value)} maxLength={1000} />
        <button className={styles.btn} type="submit" disabled={chat.isPending}>Send</button>
      </form>
    </div>
  );
}

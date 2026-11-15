import { getSession, useSaveSession, useSessions } from '../../api/queries';
import { sessionStateSchema } from '../../state/schemas';
import { useStore } from '../../state/store';
import styles from '../../styles/ui.module.css';

export async function openSession(id: string) {
  const { restore, reset, setNotice, setView } = useStore.getState();
  try {
    const s = await getSession(id);
    const parsed = sessionStateSchema.safeParse(s.state);
    if (!parsed.success) throw new Error('invalid');
    restore(parsed.data, s.id);
    window.history.pushState(null, '', `/s/${s.id}`);
    setView('explore');
  } catch {
    reset();
    window.history.replaceState(null, '', '/');
    setNotice('That saved session could not be opened, so the app started empty.');
  }
}

export function SaveButton({ title }: { title: string }) {
  const save = useSaveSession();
  const { sessionId, snapshot, setSessionId, setNotice } = useStore();
  return (
    <button className={styles.btnGhost} disabled={save.isPending} onClick={() =>
      save.mutate({ id: sessionId, body: { title, state: snapshot() } }, {
        onSuccess: (s) => { setSessionId(s.id); window.history.pushState(null, '', `/s/${s.id}`); setNotice('Session saved.'); },
        onError: () => setNotice('Could not save the session.'),
      })}>
      Save session
    </button>
  );
}

export function SavedList() {
  const q = useSessions();
  return (
    <div>
      <h2 className={styles.h2}>Saved sessions</h2>
      {q.isLoading && <p>Loading…</p>}
      {q.error && <div className={styles.error}>Could not load saved sessions.</div>}
      {q.data?.length === 0 && <p className={styles.sub}>Nothing saved yet. Run an investigation, then choose Save session.</p>}
      <div className={styles.cards}>
        {q.data?.map((s) => (
          <button key={s.id} className={styles.pick} onClick={() => void openSession(s.id)}>
            <span className={styles.pickName}>{s.title}</span>
            <span className={styles.pickDesc}>Updated {new Date(s.updatedAt).toLocaleString('en-SG', { hour12: false })}</span>
          </button>
        ))}
      </div>
    </div>
  );
}

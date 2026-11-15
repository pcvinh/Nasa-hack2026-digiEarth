import styles from './Shell.module.css';

export function SampleBanner() {
  return (
    <div className={styles.banner} role="alert" data-testid="sample-banner">
      SAMPLE DATA — not NASA results
    </div>
  );
}

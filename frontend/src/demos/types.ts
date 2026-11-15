import type { SafeAction } from '../state/schemas';

/** Demo copy asks questions only. No numbers or claimed outcomes: results come from the live API. */
export interface DemoStep { text: string; cta: string; action: SafeAction }
export interface Demo { id: string; title: string; blurb: string; steps: DemoStep[] }

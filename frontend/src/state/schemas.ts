import { z } from 'zod';

/** Whitelist of Guide / demo actions. Anything else is dropped. */
const lonLat = z.tuple([z.number().min(-180).max(180), z.number().min(-90).max(90)]);
const bbox = z.tuple([z.number(), z.number(), z.number(), z.number()]);
export const regionInputSchema = z.union([
  z.object({ presetId: z.string() }),
  z.object({ point: lonLat }),
  z.object({ bbox }),
]);
export type RegionSel = z.infer<typeof regionInputSchema>;

export const actionSchema = z.discriminatedUnion('type', [
  z.object({ type: z.literal('select_variable'), payload: z.object({ variableId: z.string() }) }),
  z.object({ type: z.literal('select_region'), payload: regionInputSchema }),
  z.object({ type: z.literal('run_analysis'), payload: z.object({ variableId: z.string(), region: regionInputSchema }) }),
  z.object({ type: z.literal('show_trend_map'), payload: z.object({ variableId: z.string() }) }),
]);
export type SafeAction = z.infer<typeof actionSchema>;

/** Keeps valid actions; logs and drops unknown types or bad payloads. */
export function parseActions(raw: unknown[]): SafeAction[] {
  const out: SafeAction[] = [];
  for (const a of raw) {
    const r = actionSchema.safeParse(a);
    if (r.success) out.push(r.data);
    else console.warn('Dropped unsupported Guide action', a);
  }
  return out;
}

export const guideMessageSchema = z.object({
  role: z.enum(['user', 'guide']),
  text: z.string(),
  mode: z.enum(['rules', 'llm']).optional(),
  suggestions: z.array(z.object({ variableId: z.string(), reason: z.string() })).optional(),
  actions: z.array(actionSchema).optional(),
});
export type GuideMessage = z.infer<typeof guideMessageSchema>;

export const sessionStateSchema = z.object({
  version: z.literal(1),
  variableId: z.string().nullable(),
  region: regionInputSchema.nullable(),
  startYear: z.number().int(),
  endYear: z.number().int().nullable(),
  showTrendMap: z.boolean(),
  chartMode: z.enum(['annual', 'monthly', 'anomaly']),
  camera: z.object({ lon: z.number(), lat: z.number(), height: z.number() }).optional(),
  guideMessages: z.array(guideMessageSchema),
});
export type SessionState = z.infer<typeof sessionStateSchema>;

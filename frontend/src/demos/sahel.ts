import type { Demo } from './types';

export const sahel: Demo = {
  id: 'sahel', title: 'Sahel: rain and plants',
  blurb: 'The Sahel sits between desert and savanna. Are rain and vegetation moving together?',
  steps: [
    { text: 'Has rainfall changed in the Sahel? Let’s check.', cta: 'Investigate rainfall', action: { type: 'run_analysis', payload: { variableId: 'precipitation', region: { presetId: 'sahel' } } } },
    { text: 'Do plants tell the same story? Check vegetation greenness.', cta: 'Investigate greenness', action: { type: 'run_analysis', payload: { variableId: 'ndvi', region: { presetId: 'sahel' } } } },
    { text: 'Now zoom out. Do other parts of the world show the same pattern for rainfall, or different ones?', cta: 'Show global rainfall trend map', action: { type: 'show_trend_map', payload: { variableId: 'precipitation' } } },
  ],
};

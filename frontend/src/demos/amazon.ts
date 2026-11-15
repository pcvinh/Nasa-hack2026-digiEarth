import type { Demo } from './types';

export const amazon: Demo = {
  id: 'amazon', title: 'Amazon: forest and heat',
  blurb: 'Is the rainforest looking different from space, and is the air warming?',
  steps: [
    { text: 'Is the central Amazon greener or less green than before? Let’s look.', cta: 'Investigate greenness', action: { type: 'run_analysis', payload: { variableId: 'ndvi', region: { presetId: 'amazon-central' } } } },
    { text: 'What has happened to the air temperature in the same place?', cta: 'Investigate temperature', action: { type: 'run_analysis', payload: { variableId: 'air_temperature', region: { presetId: 'amazon-central' } } } },
  ],
};

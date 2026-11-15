import type { Demo } from './types';

export const mekong: Demo = {
  id: 'mekong', title: 'Mekong Delta: farming and water',
  blurb: 'Farmers in the delta depend on rain and wet soil. Has either one changed?',
  steps: [
    { text: 'Has rainfall changed in the Mekong Delta? Let’s check.', cta: 'Investigate rainfall', action: { type: 'run_analysis', payload: { variableId: 'precipitation', region: { presetId: 'mekong-delta' } } } },
    { text: 'Rain is only part of the story. What about the water held in the topsoil, where crop roots are?', cta: 'Investigate topsoil moisture', action: { type: 'run_analysis', payload: { variableId: 'soil_moisture', region: { presetId: 'mekong-delta' } } } },
  ],
};

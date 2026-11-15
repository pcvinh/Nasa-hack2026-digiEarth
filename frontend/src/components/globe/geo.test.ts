import { REGIONS } from '../../api/fixtures/data';
import { asBBox } from '../../api/types';
import { bboxCenter, bboxToGeoJson, radiansToLonLat } from './geo';

describe('[lon, lat] handling', () => {
  it('converts Cesium radians to [lon, lat] degrees', () => {
    const [lon, lat] = radiansToLonLat((105.8 * Math.PI) / 180, (10 * Math.PI) / 180);
    expect(lon).toBeCloseTo(105.8);
    expect(lat).toBeCloseTo(10);
  });
  it('Mekong Delta centre is about 105.8 E, 10 N (lon first)', () => {
    const mekong = REGIONS.find((r) => r.id === 'mekong-delta')!;
    const [lon, lat] = bboxCenter(asBBox(mekong.bbox));
    expect(lon).toBeGreaterThan(104); expect(lon).toBeLessThan(107);
    expect(lat).toBeGreaterThan(8); expect(lat).toBeLessThan(12);
  });
  it('outline ring is [lon, lat] and closed', () => {
    const g = bboxToGeoJson([100, 5, 110, 15]);
    expect(g.coordinates[0]![0]).toEqual([100, 5]);
    expect(g.coordinates[0]![2]).toEqual([110, 15]);
    expect(g.coordinates[0]![4]).toEqual(g.coordinates[0]![0]);
  });
});

import { clampBounds, clampNote } from './geo';
describe('overlay clamping', () => {
  it('clamps the MERRA-2 west edge to -180', () => {
    expect(clampBounds([-180.3125, -90, 179.6875, 90])).toEqual([-180, -90, 179.6875, 90]);
    expect(clampNote([-180.3125, -90, 179.6875, 90])).toMatch(/west edge clamped to -180/);
  });
  it('leaves in-range bounds alone', () => {
    expect(clampBounds([-180, -90, 180, 90])).toEqual([-180, -90, 180, 90]);
    expect(clampNote([-180, -90, 180, 90])).toBeNull();
  });
});

import type { BBox, LonLat } from '../../api/types';

/** Cesium cartographic positions are radians; the API and GeoJSON use [lon, lat] degrees. */
export const radiansToLonLat = (lonRad: number, latRad: number): LonLat => [(lonRad * 180) / Math.PI, (latRad * 180) / Math.PI];

/** [west, south, east, north] -> Rectangle.fromDegrees argument order is the same. */
export const bboxToDegrees = (b: BBox) => ({ west: b[0], south: b[1], east: b[2], north: b[3] });

export const bboxCenter = (b: BBox): LonLat => [(b[0] + b[2]) / 2, (b[1] + b[3]) / 2];

/** Closed outline ring [lon, lat] for a bbox. */
export const bboxToGeoJson = (b: BBox) => ({
  type: 'Polygon',
  coordinates: [[[b[0], b[1]], [b[2], b[1]], [b[2], b[3]], [b[0], b[3]], [b[0], b[1]]]],
});

/** Cesium rectangles must stay within the globe. Clamp to [-180, 180] x [-90, 90]. */
export const clampBounds = (b: BBox): BBox => [Math.max(-180, b[0]), Math.max(-90, b[1]), Math.min(180, b[2]), Math.min(90, b[3])];

/** Note for the legend when the overlay had to be clamped (e.g. MERRA-2 grid edge at -180.3125). */
export function clampNote(b: BBox): string | null {
  const c = clampBounds(b);
  if (c.every((v, i) => v === b[i])) return null;
  const edge = c[0] !== b[0] ? `west edge clamped to ${c[0]}° (data grid starts at ${b[0]}°)` : 'edges clamped to the globe limits';
  return `Overlay ${edge}.`;
}

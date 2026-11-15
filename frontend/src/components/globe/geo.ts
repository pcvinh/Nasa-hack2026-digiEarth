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

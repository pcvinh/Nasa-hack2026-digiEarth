import { useEffect, useRef } from 'react';
import * as Cesium from 'cesium';
import type { BBox, LonLat } from '../../api/types';
import { bboxToDegrees, radiansToLonLat } from './geo';
import styles from './GlobeView.module.css';

export interface GlobeProps {
  outline: object | null;        // GeoJSON geometry (preset region)
  cell: BBox | null;             // bbox of the analysed cell/region (result)
  flyTo: BBox | null;
  overlay: { url: string; bounds: BBox } | null;
  pickMode: boolean;
  onPick: (lonLat: LonLat) => void;
}

// NASA GIBS WMTS, EPSG:4326, no token needed. Layer and matrix set checked against GetCapabilities.
const GIBS =
  'https://gibs.earthdata.nasa.gov/wmts/epsg4326/best/BlueMarble_ShadedRelief_Bathymetry/default/{TileMatrixSet}/{TileMatrix}/{TileRow}/{TileCol}.jpeg';

/**
 * GIBS EPSG:4326 matrix set "500m": level 0 is 2x1 tiles of 512 px at 0.5625 deg/px, i.e. each
 * level-0 tile spans 288 deg, anchored at the top-left (-180, 90); the tile size halves each level
 * (matrix widths 2, 3, 5, 10, 20 ...; checked in GetCapabilities). That is not Cesium's default
 * 180-degree geographic scheme, so describe the real grid: 2x1 level-0 tiles of 288 deg.
 */
const gibsTilingScheme = () =>
  new Cesium.GeographicTilingScheme({
    rectangle: Cesium.Rectangle.fromDegrees(-180, 90 - 288, -180 + 2 * 288, 90),
    numberOfLevelZeroTilesX: 2, numberOfLevelZeroTilesY: 1,
  });

export default function GlobeView(props: GlobeProps) {
  const host = useRef<HTMLDivElement>(null);
  const viewer = useRef<Cesium.Viewer | null>(null);
  const pickCb = useRef(props.onPick);
  useEffect(() => { pickCb.current = props.onPick; });
  const outlineDs = useRef<Cesium.CustomDataSource | null>(null);

  useEffect(() => {
    Cesium.Ion.defaultAccessToken = '';
    const gibs = new Cesium.WebMapTileServiceImageryProvider({
      url: GIBS, layer: 'BlueMarble_ShadedRelief_Bathymetry', style: 'default', format: 'image/jpeg',
      tileMatrixSetID: '500m', tileMatrixLabels: Array.from({ length: 8 }, (_, i) => String(i)),
      maximumLevel: 7, tilingScheme: gibsTilingScheme(), rectangle: Cesium.Rectangle.fromDegrees(-180, -90, 180, 90),
      tileWidth: 512, tileHeight: 512, credit: new Cesium.Credit('Imagery: NASA GIBS', true), // showOnScreen: always visible
    });
    const v = new Cesium.Viewer(host.current!, {
      baseLayer: new Cesium.ImageryLayer(gibs), baseLayerPicker: false, geocoder: false, timeline: false,
      animation: false, homeButton: false, sceneModePicker: false, navigationHelpButton: false,
      fullscreenButton: false, infoBox: false, selectionIndicator: false, terrainProvider: new Cesium.EllipsoidTerrainProvider(),
    });
    v.scene.globe.enableLighting = false;
    viewer.current = v;
    // Dev-only hook so the screenshot script can position the camera. Not present in production builds.
    if (import.meta.env.DEV) (window as unknown as { __cesiumViewer?: Cesium.Viewer }).__cesiumViewer = v;
    const ds = new Cesium.CustomDataSource('outline');
    outlineDs.current = ds;
    void v.dataSources.add(ds);
    const handler = new Cesium.ScreenSpaceEventHandler(v.scene.canvas);
    handler.setInputAction((e: { position: Cesium.Cartesian2 }) => {
      const c = v.camera.pickEllipsoid(e.position, v.scene.globe.ellipsoid);
      if (!c) return;
      const g = Cesium.Cartographic.fromCartesian(c);
      pickCb.current(radiansToLonLat(g.longitude, g.latitude));
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);
    return () => {
      handler.destroy();
      if (!v.isDestroyed()) v.destroy();
      viewer.current = null;
    };
  }, []);

  // Region outline (geometry) and result cell outline
  useEffect(() => {
    const ds = outlineDs.current;
    if (!ds) return;
    ds.entities.removeAll();
    const ring = (b: BBox) => Cesium.Rectangle.fromDegrees(...(Object.values(bboxToDegrees(b)) as [number, number, number, number]));
    if (props.outline) {
      const geom = props.outline as { type: string; coordinates: number[][][] | number[][][][] };
      const polys = geom.type === 'MultiPolygon' ? (geom.coordinates as number[][][][]) : [geom.coordinates as number[][][]];
      for (const p of polys) {
        const outer = p[0] ?? [];
        ds.entities.add({ polygon: { hierarchy: Cesium.Cartesian3.fromDegreesArray(outer.flatMap((c) => [c[0]!, c[1]!])),
          material: Cesium.Color.fromCssColorString('#1557bf').withAlpha(0.15), outline: true, outlineColor: Cesium.Color.WHITE, height: 0 } });
        ds.entities.add({ polyline: { positions: Cesium.Cartesian3.fromDegreesArray(outer.flatMap((c) => [c[0]!, c[1]!])),
          width: 3, clampToGround: false, material: Cesium.Color.WHITE } });
      }
    }
    if (props.cell) {
      ds.entities.add({ rectangle: { coordinates: ring(props.cell), material: Cesium.Color.YELLOW.withAlpha(0.15),
        outline: true, outlineColor: Cesium.Color.YELLOW, height: 0 } });
    }
  }, [props.outline, props.cell]);

  useEffect(() => {
    const v = viewer.current;
    if (!v || !props.flyTo) return;
    const [w, s, e, n] = props.flyTo;
    const padX = (e - w) * 0.6 + 2, padY = (n - s) * 0.6 + 2;
    void v.camera.flyTo({ destination: Cesium.Rectangle.fromDegrees(w - padX, s - padY, e + padX, n + padY), duration: 1.5 });
  }, [props.flyTo]);

  // Trend map overlay, nearest-neighbour so 0.5 degree cells stay visible as cells.
  useEffect(() => {
    const v = viewer.current;
    if (!v || !props.overlay) return;
    let layer: Cesium.ImageryLayer | null = null;
    let cancelled = false;
    void Cesium.SingleTileImageryProvider.fromUrl(props.overlay.url, {
      rectangle: Cesium.Rectangle.fromDegrees(...(props.overlay.bounds as [number, number, number, number])),
    }).then((p) => {
      if (cancelled || v.isDestroyed()) return;
      layer = new Cesium.ImageryLayer(p, { alpha: 0.8, minificationFilter: Cesium.TextureMinificationFilter.NEAREST, magnificationFilter: Cesium.TextureMagnificationFilter.NEAREST });
      v.imageryLayers.add(layer);
    });
    return () => {
      cancelled = true;
      if (layer && !v.isDestroyed()) v.imageryLayers.remove(layer, true);
    };
  }, [props.overlay]);

  return <div ref={host} className={styles.host} data-pick={props.pickMode} data-testid="globe" />;
}

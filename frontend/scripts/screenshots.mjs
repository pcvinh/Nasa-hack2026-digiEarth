// Drives headless Chrome over the DevTools protocol and saves screenshots to docs/screenshots/.
// Usage: node scripts/screenshots.mjs <real-url> <fixture-url>
//   real-url:    dev server with VITE_USE_FIXTURES=false and the backend on :8000
//   fixture-url: dev server with VITE_USE_FIXTURES=true (only used for the "insufficient data" state)
import { spawn } from 'node:child_process';
import { mkdirSync, writeFileSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const [REAL, FIX] = process.argv.slice(2);
const OUT = new URL('../docs/screenshots/', import.meta.url).pathname;
mkdirSync(OUT, { recursive: true });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9333;

const chrome = spawn(CHROME, ['--headless=new', `--remote-debugging-port=${PORT}`, `--user-data-dir=${mkdtempSync(join(tmpdir(), 'td-'))}`,
  '--window-size=1440,900', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--hide-scrollbars', 'about:blank'], { stdio: 'ignore' });
let target;
for (let i = 0; i < 40 && !target; i++) {
  await sleep(500);
  try { target = (await (await fetch(`http://localhost:${PORT}/json`)).json()).find((t) => t.type === 'page'); } catch { /* not up yet */ }
}
if (!target) { chrome.kill(); throw new Error('Chrome did not start'); }
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));
let id = 0; const pending = new Map();
ws.onmessage = (m) => { const d = JSON.parse(m.data); if (d.id && pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); } };
const send = (method, params = {}) => new Promise((res) => { const i = ++id; pending.set(i, res); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expr) => { const r = await send('Runtime.evaluate', { expression: expr, awaitPromise: true, returnByValue: true }); if (r.result?.exceptionDetails) throw new Error(JSON.stringify(r.result.exceptionDetails).slice(0, 300)); return r.result?.result?.value; };
const shot = async (name) => { const r = await send('Page.captureScreenshot', { format: 'png' }); writeFileSync(OUT + name + '.png', Buffer.from(r.result.data, 'base64')); console.log('saved', name); };
await send('Page.enable'); await send('Runtime.enable');
await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: 1, mobile: false });
const go = async (url) => { await send('Page.navigate', { url }); await sleep(4000); };

const btn = (text) => ev(`(() => { const b=[...document.querySelectorAll('button')].filter(x=>x.textContent.trim().startsWith(${JSON.stringify(text)})&&!x.disabled); const w=b.at(-1); if(!w) return false; w.click(); return true; })()`);
const setInput = (label, val) => ev(`(() => { const i=document.querySelector('[aria-label=${JSON.stringify(label)}]'); const proto=i.tagName==='SELECT'?HTMLSelectElement.prototype:HTMLInputElement.prototype; Object.getOwnPropertyDescriptor(proto,'value').set.call(i, ${JSON.stringify(val)}); i.dispatchEvent(new Event(i.tagName==='SELECT'?'change':'input',{bubbles:true})); return true; })()`);
const clickAt = async (x, y) => { for (const t of ['mousePressed', 'mouseReleased']) await send('Input.dispatchMouseEvent', { type: t, x, y, button: 'left', clickCount: 1 }); };
const pickRegion = async (q, name) => { await setInput('Search regions', q); await sleep(400); await btn(name); };
const waitResult = async () => { for (let i = 0; i < 40; i++) { await sleep(500); if (await ev(`!!document.querySelector('[data-testid=verdict]')`)) return; } throw new Error('no result'); };
const setCamera = (lon, lat, h) => ev(`(async () => { const C = await import('/node_modules/.vite/deps/cesium.js'); window.__cesiumViewer.camera.setView({ destination: C.Cartesian3.fromDegrees(${lon}, ${lat}, ${h}) }); return true; })()`);
// Software-rendered WebGL loads tiles slowly: wait until Cesium reports the globe and overlays loaded.
const waitTiles = async (max = 60000) => { const t0 = Date.now(); await sleep(1500); while (Date.now() - t0 < max) { if (await ev(`(() => { const v = window.__cesiumViewer; return !!v && v.scene.globe.tilesLoaded && !v.camera._flight; })()`)) { await sleep(1500); return; } await sleep(700); } console.log('warning: tiles not fully loaded'); };
const globeCenter = () => ev(`(() => { const r=document.querySelector('[data-testid=globe]').getBoundingClientRect(); return [r.x + r.width/2, r.y + r.height/2]; })()`);

// ---- real backend ----
await go(REAL);
await ev(`localStorage.clear()`);
// 1. globe with region outline (flying to Mekong)
await pickRegion('mekong', 'Mekong Delta');
await sleep(2000); await waitTiles();
await shot('01-globe-outline');
// 2. significant result (rainfall, Mekong)
await setInput('Variable', 'precipitation'); await waitResult(); await sleep(1500);
await shot('02-result-significant');
// 3. not significant (topsoil moisture, Mekong)
await setInput('Variable', 'soil_moisture'); await sleep(800); await waitResult(); await sleep(1200);
await shot('03-result-not-significant');
// 4. trend map zoomed to Mekong, land-only variable (soil moisture): cells should hug the coast
await btn('Show trend map'); await sleep(2000); await waitTiles();
await setCamera(105.3, 9.8, 700000); await waitTiles();
await shot('04-trend-map-coastlines-mekong');
await setCamera(60, 10, 22000000); await waitTiles();
await shot('05-trend-map-global');
// 5. click-to-analyse: click the middle of the globe
const [cx, cy] = await globeCenter();
await setCamera(105.3, 10.5, 1500000); await waitTiles();
await clickAt(cx, cy); await sleep(3500); await waitTiles();
await shot('06-click-to-analyse-cell');
// 6. data_unavailable: click open ocean with a land-only variable
await setCamera(-30, 0, 9000000); await waitTiles();
await clickAt(cx, cy); await sleep(3000);
await shot('07-data-unavailable-ocean');
// 7. opposite trends: air temperature in the Sahel vs central Amazon
await go(REAL);
await setInput('Variable', 'air_temperature');
await pickRegion('sahel', 'Sahel'); await waitResult(); await waitTiles();
await shot('08-opposite-sahel-air-temperature');
await pickRegion('amazon', 'Central Amazon'); await sleep(800); await waitResult(); await waitTiles();
await shot('09-opposite-amazon-air-temperature');
await btn('Show trend map'); await sleep(2000); await waitTiles();
await setCamera(-10, 5, 16000000); await waitTiles();
await shot('10-trend-map-air-temperature-merra2');
// 8. wizard
await go(REAL);
await btn('Start investigation'); await sleep(600);
await btn('Central Amazon'); await sleep(800);
await shot('11-wizard-step-what');
// 9. Guide
await go(REAL);
await btn('Guide'); await sleep(500);
await setInput('Message the Guide', 'What should I look at in a desert?');
await btn('Send'); await sleep(2500);
await shot('12-guide');
// ---- fixtures: insufficient-data state (cannot be produced from real data) ----
await go(FIX);
await pickRegion('sahel', 'Sahel');
await setInput('Variable', 'soil_moisture');
// fixture scenarios are deterministic; find a region/variable pair that is insufficient
let found = false;
for (const [q, name, v] of [['johor', 'Johor', 'ndvi'], ['central', 'Central Java', 'ndvi'], ['johor', 'Johor', 'air_temperature'], ['central', 'Central Java', 'soil_moisture'], ['johor', 'Johor', 'precipitation']]) {
  await pickRegion(q, name); await setInput('Variable', v); await sleep(1500);
  if (await ev(`document.querySelector('[data-testid=significance-badge]')?.textContent.includes('Not enough data')`)) { found = true; break; }
}
console.log('insufficient state found:', found);
await sleep(1500);
await shot('13-result-insufficient-data-FIXTURE-SAMPLE');

ws.close(); chrome.kill();

// Writes a SYNTHETIC 720x360 equirectangular PNG (1 px = 0.5 deg) for fixture mode only.
// The pattern is a smooth made-up field, not data and not related to real coastlines.
import { deflateSync } from 'node:zlib';
import { writeFileSync } from 'node:fs';

const W = 720, H = 360;
const raw = Buffer.alloc((W * 4 + 1) * H);
for (let y = 0; y < H; y++) {
  raw[y * (W * 4 + 1)] = 0;
  for (let x = 0; x < W; x++) {
    const v = Math.sin(x / 37) * Math.cos(y / 23); // -1..1
    const faded = Math.sin(x / 11 + y / 7) < 0.2;
    const o = y * (W * 4 + 1) + 1 + x * 4;
    const t = (v + 1) / 2;
    raw[o] = Math.round(140 - 100 * t); raw[o + 1] = Math.round(80 + 120 * t); raw[o + 2] = Math.round(40 + 20 * t);
    raw[o + 3] = Math.abs(y - H / 2) > 150 ? 0 : faded ? 70 : 255;
  }
}
const crcTable = Array.from({ length: 256 }, (_, n) => { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; return c >>> 0; });
const crc = (b) => { let c = 0xffffffff; for (const x of b) c = crcTable[(c ^ x) & 255] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; };
const chunk = (type, data) => { const len = Buffer.alloc(4); len.writeUInt32BE(data.length); const td = Buffer.concat([Buffer.from(type), data]); const c = Buffer.alloc(4); c.writeUInt32BE(crc(td)); return Buffer.concat([len, td, c]); };
const ihdr = Buffer.alloc(13); ihdr.writeUInt32BE(W, 0); ihdr.writeUInt32BE(H, 4); ihdr[8] = 8; ihdr[9] = 6;
writeFileSync('public/fixtures/trend-map-sample.png', Buffer.concat([Buffer.from([137,80,78,71,13,10,26,10]), chunk('IHDR', ihdr), chunk('IDAT', deflateSync(raw)), chunk('IEND', Buffer.alloc(0))]));

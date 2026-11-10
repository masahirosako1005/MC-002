// Pure encoder/decoder compatibility check; no live code or API is used.
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { createOmikujiQr } from "../../frontend/src/omikuji-qr.ts";
const require = createRequire(new URL("../../frontend/package.json", import.meta.url));
const jsQR = require("jsqr");
let verified = 0;
for (const code of ["000000", "012345", "999999"]) {
  const marker = createOmikujiQr(code);
  const scale = 8;
  const size = marker.size * scale;
  const pixels = new Uint8ClampedArray(size * size * 4).fill(255);
  const modules = [...marker.path.matchAll(/M(\d+) (\d+)h1v1h-1z/g)];
  assert.ok(modules.length > 0);
  for (const module of modules) {
    const x = Number(module[1]); const y = Number(module[2]);
    assert.ok(x >= 4 && y >= 4 && x < marker.size - 4 && y < marker.size - 4);
    for (let yy = y * scale; yy < (y + 1) * scale; yy += 1) {
      for (let xx = x * scale; xx < (x + 1) * scale; xx += 1) {
        const offset = (yy * size + xx) * 4;
        pixels[offset] = 0; pixels[offset + 1] = 0; pixels[offset + 2] = 0;
      }
    }
  }
  const decoded = jsQR(pixels, size, size, { inversionAttempts: "dontInvert" });
  assert.equal(decoded?.data, `KOU-OMIKUJI:${code}`);
  verified += 1;
}
for (const invalid of ["12345", "1234567", "<script>", "KOU-OMIKUJI:123456"]) {
  assert.throws(() => createOmikujiQr(invalid));
}
process.stdout.write(JSON.stringify({ status: "passed", roundtrip_fixtures: verified, invalid_inputs: 4, quiet_zone_modules: 4, live_code_used: false }) + "\n");

// Encode original generated artwork for local delivery; do not alter composition.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const sharp = require('../presentation/node_modules/sharp');
const root = path.resolve(__dirname, '..');
const publicDir = path.join(root, 'frontend/public/art');
const originals = path.join(root, 'artifacts/image-originals');
const names = ['scene-gate-spring-v2', 'scene-gate-summer-v2', 'scene-gate-autumn-v2', 'scene-gate-winter-v2', 'scene-shrine-v2', 'scene-coast-v2', 'scene-conference-v2', 'city-overview-v2'];
async function main() {
  fs.mkdirSync(originals, { recursive: true });
  const assets = [];
  for (const name of names) {
    const candidate = path.join(publicDir, `${name}.png`);
    const source = path.join(originals, `${name}.png`);
    for (const target of [candidate, source]) {
      if (!path.resolve(target).startsWith(root + path.sep)) throw new Error('Asset path is outside project');
    }
    if (fs.existsSync(candidate)) {
      if (fs.existsSync(source)) throw new Error('Original already exists: ' + name);
      fs.renameSync(candidate, source);
    }
    const metadata = await sharp(source).metadata();
    const files = [];
    for (const width of [640, 1280]) {
      const target = path.join(publicDir, `${name}${width === 640 ? '-small' : ''}.webp`);
      await sharp(source).resize({ width, withoutEnlargement: true }).webp({ quality: 82, effort: 5 }).toFile(target);
      const buffer = fs.readFileSync(target);
      files.push({ path: path.relative(root, target).replaceAll('\\', '/'), bytes: buffer.length, sha256: crypto.createHash('sha256').update(buffer).digest('hex') });
    }
    assets.push({ name, original: path.relative(root, source).replaceAll('\\', '/'), original_bytes: fs.statSync(source).size, width: metadata.width, height: metadata.height, files });
  }
  fs.writeFileSync(path.join(root, 'artifacts/art-manifest.json'), JSON.stringify({ generated_by: 'built-in image_gen', encoding: 'WebP quality 82, widths 640 and 1280', assets }, null, 2) + '\n');
  console.log(JSON.stringify({ assets: assets.length, originalBytes: assets.reduce((s, a) => s + a.original_bytes, 0), deliveredBytes: assets.reduce((s, a) => s + a.files.reduce((n, f) => n + f.bytes, 0), 0) }));
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });

import createQrCode from "qrcode-generator";

/** Local marker payload. The server validates expiry, budget and one-time use. */
export function createOmikujiQr(code: string) {
  if (!/^[0-9]{6}$/.test(code)) throw new Error("現地確認コードを確認してください。");
  const payload = `KOU-OMIKUJI:${code}`;
  const qr = createQrCode(0, "M");
  qr.addData(payload, "Byte");
  qr.make();
  const count = qr.getModuleCount();
  const quiet = 4;
  let path = "";
  for (let row = 0; row < count; row += 1) {
    for (let column = 0; column < count; column += 1) {
      if (qr.isDark(row, column)) path += `M${column + quiet} ${row + quiet}h1v1h-1z`;
    }
  }
  const size = count + quiet * 2;
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${size} ${size}" shape-rendering="crispEdges"><rect width="${size}" height="${size}" fill="#fff"/><path d="${path}" fill="#000"/></svg>`;
  return { payload, size, path, imageUrl: `data:image/svg+xml,${encodeURIComponent(svg)}` };
}

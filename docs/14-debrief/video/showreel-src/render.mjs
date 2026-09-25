import { chromium } from 'playwright-core';
import { spawn } from 'node:child_process';
import http from 'node:http';
import fs from 'node:fs';
import path from 'node:path';
const dir = path.dirname(new URL(import.meta.url).pathname);
const FF = process.env.FFMPEG || 'ffmpeg';
const types = { '.html': 'text/html', '.woff2': 'font/woff2' };
const fonts = path.resolve(dir, '../../../../frontend/public/fonts');
const srv = http.createServer((q, r) => { const u = decodeURIComponent(q.url.split('?')[0]); const f = u.endsWith('.woff2') ? path.join(fonts, path.basename(u)) : path.join(dir, u); if (!fs.existsSync(f)) { r.writeHead(404); return r.end(); } r.writeHead(200, { 'content-type': types[path.extname(f)] || 'application/octet-stream' }); fs.createReadStream(f).pipe(r); });
await new Promise(r => srv.listen(8765, r));
const browser = await chromium.launch({ executablePath: process.env.CHROME_PATH || undefined, args: ['--disable-gpu-vsync', '--font-render-hinting=none', '--force-color-profile=srgb'] });
async function newPage() {
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  await page.goto('http://localhost:8765/reel.html');
  await page.evaluate(() => window.fontsReady);
  return page;
}
const mode = process.argv[2];
if (mode === 'stills') {
  const times = process.argv[3].split(',').map(Number);
  const out = process.argv[4] || 'stills';
  fs.mkdirSync(path.join(dir, out), { recursive: true });
  const page = await newPage();
  for (const t of times) {
    await page.evaluate(t => window.seek(t, Math.round(t * 60)), t);
    await page.screenshot({ path: path.join(dir, out, `t${t.toFixed(2)}.png`) });
  }
} else if (mode === 'full') {
  const FPS = Number(process.argv[3] || 120), DUR = 20, N = FPS * DUR, W = Number(process.argv[4] || 4);
  const per = Math.ceil(N / W);
  await Promise.all(Array.from({ length: W }, async (_, w) => {
    const page = await newPage();
    const a = w * per, b = Math.min(N, a + per);
    const ff = spawn(FF, ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '10', '-pix_fmt', 'yuv444p', path.join(dir, `chunk${w}.mp4`)], { stdio: ['pipe', 'inherit', 'inherit'] });
    for (let i = a; i < b; i++) {
      await page.evaluate(([t, f]) => window.seek(t, f), [i / FPS, Math.floor(i * 60 / FPS)]);
      const buf = await page.screenshot({ type: 'jpeg', quality: 96 });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if ((i - a) % 200 === 0) console.log(`worker ${w}: ${i - a}/${b - a}`);
    }
    ff.stdin.end();
    await new Promise(r => ff.on('close', r));
  }));
}
await browser.close(); srv.close();

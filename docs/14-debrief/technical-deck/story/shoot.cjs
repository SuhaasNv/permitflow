// Renders a story slide to PNG at 3840 x 2160.
// Usage: node shoot.cjs <html> <out.png> "<KICKER>" "<NN / TT>" ["<head>"] ["<foot>"] [light]
const path = require('path');
const { chromium } = require(require.resolve('@playwright/test', { paths: [path.resolve(__dirname, '../../../../frontend')] }));
(async () => {
  const [html, out, kicker, page, head, foot, light] = process.argv.slice(2);
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 2 });
  await p.goto('file://' + path.resolve(html));
  await p.evaluate(([k, n, h, f, l]) => {
    document.querySelector('.kicker').textContent = k;
    document.querySelector('.page').textContent = n;
    if (h) document.querySelector('.head').textContent = h;
    if (f) document.querySelector('.foot').innerHTML = f;
    if (l === 'light') document.body.classList.add('light');
  }, [kicker, page, head || '', foot || '', light || '']);
  await p.evaluate(() => document.fonts.ready);
  await p.screenshot({ path: out });
  await b.close();
})();

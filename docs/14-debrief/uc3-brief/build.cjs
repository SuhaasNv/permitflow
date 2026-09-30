// Renders src/*.html to PNG at 3840 x 2160, then build.py assembles the deck.
// Usage (from the repository root): node docs/14-debrief/uc3-brief/build.cjs && python3 docs/14-debrief/uc3-brief/build.py
const path = require('path');
const fs = require('fs');
const { chromium } = require(require.resolve('@playwright/test', { paths: [path.resolve(__dirname, '../../../frontend')] }));
(async () => {
  const src = path.join(__dirname, 'src');
  const out = path.join(__dirname, 'slides');
  fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 2 });
  for (const f of fs.readdirSync(src).filter((n) => n.endsWith('.html')).sort()) {
    await p.goto('file://' + path.join(src, f));
    await p.evaluate(() => document.fonts.ready);
    await p.screenshot({ path: path.join(out, f.replace('.html', '.png')) });
  }
  await b.close();
})();

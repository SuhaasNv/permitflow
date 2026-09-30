/* Renders the four flowcharts to ../*.png at 3840 x 2160. Run: node docs/14-debrief/technical-deck/flows/src/shoot.cjs */
const { chromium } = require(require('path').resolve(__dirname, '../../../../../frontend/node_modules/playwright'));
const path = require('path');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 2 });
  const names = { signin: '1-sign-in', application: '2-creating-an-application', upload: '3-document-upload', ai: '4-ai-verification', submit: '5-submit', officer: '6-officer-queue-and-case' };
  for (const [d, file] of Object.entries(names)) {
    await page.goto('file://' + path.resolve(__dirname, 'flow.html') + '?d=' + d);
    await page.evaluate(() => document.fonts.ready);
    const problems = await page.evaluate(() => {
      const out = [];
      for (const el of document.querySelectorAll('.node, .banner .f')) {
        if (el.scrollHeight > el.clientHeight + 1) out.push(`${el.dataset.id || el.textContent.slice(0, 30)} overflows by ${el.scrollHeight - el.clientHeight}px`);
      }
      const fontsOk = document.fonts.check('16px "Public Sans"');
      if (!fontsOk) out.push('Public Sans not loaded');
      return out;
    });
    console.log(d, problems.length ? problems : 'ok');
    await page.screenshot({ path: path.resolve(__dirname, '..', file + '.png') });
  }
  await browser.close();
})();

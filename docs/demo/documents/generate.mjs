// Regenerates the PermitFlow demo PDFs from the HTML templates in ./src.
//
// Run from the frontend folder so that @playwright/test resolves:
//   cd frontend && node ../docs/demo/documents/generate.mjs
//
// For each set (clean, with_issues) the script fills the {{PLACEHOLDERS}} in
// every template, writes the filled HTML next to the PDF (so the exact source of
// each PDF is inspectable) and renders the PDF with Playwright's Chromium.

import { createRequire } from 'node:module';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));
const srcDir = path.join(here, 'src');

// Resolve Playwright from the current working directory (frontend/), not from
// this file's location, because docs/ has no node_modules.
const requireFromCwd = createRequire(path.join(process.cwd(), 'package.json'));
let chromium;
try {
  ({ chromium } = requireFromCwd('@playwright/test'));
} catch {
  console.error('Cannot resolve @playwright/test from', process.cwd());
  console.error('Run this script from the frontend folder: cd frontend && node ../docs/demo/documents/generate.mjs');
  process.exit(1);
}

const DOCS = [
  { name: 'business_profile', label: 'Business Profile Extract', landscape: false },
  { name: 'floor_plan', label: 'Layout Plan LOD-2025-114', landscape: false },
  { name: 'tenancy_agreement', label: 'Tenancy Agreement TA/BH/2025/0142', landscape: false },
  { name: 'food_hygiene_certificate', label: 'Certificate FH-2026-018842', landscape: true },
];

// Values that differ between the two sets. Everything else is fixed in the templates.
const SETS = {
  clean: {
    UEN: '202355555E',
    TENANCY_UNIT: '#01-12',
    FH_ASSESSED: '31 January 2026',
    FH_ISSUED: '2 February 2026',
    FH_VALID_TO: '1 February 2029',
  },
  with_issues: {
    UEN: '202355555F', // one character off from the application's 202355555E
    TENANCY_UNIT: '#01-21', // application says #01-12
    FH_ASSESSED: '3 January 2022',
    FH_ISSUED: '4 January 2022',
    FH_VALID_TO: '3 January 2025', // expired
  },
  // A second, unrelated business with a clean set: the production example application, so the
  // demonstration record is not the same restaurant as every test fixture (19 Sep 2026).
  second_business: {
    UEN: '202411223K',
    TENANCY_UNIT: '#01-05',
    FH_ASSESSED: '12 March 2026',
    FH_ISSUED: '14 March 2026',
    FH_VALID_TO: '13 March 2029',
    replace: [
      ['Kopi &amp; Kaya Toast House Pte. Ltd.', 'Serangoon Spice House Pte. Ltd.'],
      ['KOPI &amp; KAYA TOAST HOUSE PTE. LTD.', 'SERANGOON SPICE HOUSE PTE. LTD.'],
      ['KOPI &amp; TEH BREWING', 'TANDOOR &amp; GRILL'],
      ['Tan Wei Ling', 'Priya Raghavan'],
      ['TAN WEI LING', 'PRIYA RAGHAVAN'],
      ['weiling.tan@kopikaya.sg', 'priya@serangoonspice.sg'],
      ['S****512A', 'S****804C'],
      ['10 Jalan Besar', '52 Serangoon Garden Way'],
      ['Jalan Besar frontage', 'Serangoon Garden Way frontage'],
      ['208787', '555949'],
      ['10 JALAN BESAR', '52 SERANGOON GARDEN WAY'],
      ['#01-12', '#01-05'],
      ['+65 9123 4567', '+65 9876 5432'],
      ['202355555E', '202411223K'],
      ['<td class="mono">56122</td>', '<td class="mono">56111</td>'],
      ['Cafes and coffee houses.', 'Restaurants.'],
      ['14 March 2023', '8 May 2024'],
      ['21 March 2023', '15 May 2024'],
      ['Sale of kaya toast, soft-boiled eggs, kopi and teh', 'Sale of South Indian meals, tandoor dishes and teh tarik'],
    ],
  },
};

const FOOTER_DISCLAIMER = 'Fictional document produced for a software demonstration. Not issued by any authority.';

function fill(template, values) {
  return template.replace(/\{\{([A-Z_]+)\}\}/g, (match, key) => {
    if (!(key in values)) throw new Error(`No value for placeholder ${match}`);
    return values[key];
  });
}

function footerTemplate(label) {
  return `<div style="width:100%;font-family:Helvetica,Arial,sans-serif;font-size:7px;color:#666;padding:0 14mm;display:flex;justify-content:space-between;">
    <span>${FOOTER_DISCLAIMER}</span>
    <span>${label} &middot; Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>
  </div>`;
}

async function main() {
  const baseCss = await readFile(path.join(srcDir, 'base.css'), 'utf8');
  const browser = await chromium.launch();
  try {
    for (const [setName, setValues] of Object.entries(SETS)) {
      const outDir = path.join(here, setName);
      await mkdir(outDir, { recursive: true });
      const { replace = [], ...placeholders } = setValues;
      const values = { ...placeholders, BASE_CSS: baseCss };

      for (const doc of DOCS) {
        const template = await readFile(path.join(srcDir, `${doc.name}.html`), 'utf8');
        let html = fill(template, values);
        for (const [from, to] of replace) html = html.split(from).join(to);
        const htmlPath = path.join(outDir, `${doc.name}.html`);
        const pdfPath = path.join(outDir, `${doc.name}.pdf`);
        await writeFile(htmlPath, html, 'utf8');

        const page = await browser.newPage();
        await page.setContent(html, { waitUntil: 'load' });
        await page.emulateMedia({ media: 'print' });
        await page.pdf({
          path: pdfPath,
          format: 'A4',
          landscape: doc.landscape,
          printBackground: true,
          displayHeaderFooter: true,
          headerTemplate: '<span></span>',
          footerTemplate: footerTemplate(doc.label),
          margin: doc.landscape
            ? { top: '10mm', right: '12mm', bottom: '13mm', left: '12mm' }
            : { top: '14mm', right: '14mm', bottom: '16mm', left: '14mm' },
        });
        await page.close();
        console.log(`${setName}/${doc.name}.pdf`);
      }
    }
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});

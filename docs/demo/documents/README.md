# Demo documents

Fictional, text-based PDFs for demonstrating PermitFlow uploads and the AI verification step. They match the seeded demo application for **Kopi & Kaya Toast House Pte. Ltd.** (UEN 202355555E, 10 Jalan Besar #01-12, Singapore 208787), so the AI check can cross-reference every field.

All four are real PDFs with selectable text (rendered from HTML by Chromium, not scanned images), A4, each under 250 KB.

## The four documents

| File | What it is | Pages | Key values |
|------|------------|-------|------------|
| `business_profile.pdf` | Company extract from a fictional registrar, "Registry of Business Entities" (ACRA-style layout: entity information, principal activities, capital, officers, shareholders, contact particulars) | 2 | UEN, company name, incorporation 14 March 2023, registered office, contact person Tan Wei Ling, email, phone |
| `floor_plan.pdf` | Layout plan by a fictional design practice: 1:50 plan drawn as SVG (walls, kitchen, dish-washing, toilet, dry store, counter, 6 tables of 4, entrance, scale bar, north arrow), plus area schedule, seating schedule, legend and notes | 2 | Address, 48 sqm, 24 seats, hours 7am to 9pm, 4 food handlers, menu |
| `tenancy_agreement.pdf` | Tenancy agreement between the fictional landlord Besar Holdings Pte. Ltd. and the tenant: cover, parties, 17 clauses, particulars schedule, handover inventory, execution page signed by both parties with witnesses | 5 | Premises, 48 sqm, term 1 November 2025 to 31 October 2027, rent S$4,800 per month, deposit S$9,600 |
| `food_hygiene_certificate.pdf` | Certificate of attainment from a fictional training institute (landscape) | 1 | Holder Tan Wei Ling, "Basic Food Hygiene (Level 1)", certificate FH-2026-018842, issued 2 February 2026, valid until 1 February 2029 |

## Which set to upload

| Folder | Use it for | Result the AI check should give |
|--------|-----------|---------------------------------|
| `clean/` | The "happy path" demo: submit, AI verifies, officer approves | All four documents consistent with the application |
| `with_issues/` | The "feedback round" demo: AI flags problems, officer requests changes, operator resubmits with the clean versions | Three findings: wrong UEN in the business profile, wrong unit number in the tenancy agreement, expired food hygiene certificate. The floor plan is fine. See `with_issues/NOTES.md` for the exact planted values and where they appear |

A typical demo: upload `with_issues/` first, walk through the findings, then replace the three flagged files with their `clean/` counterparts and show the application passing.

## Layout of this folder

```
docs/demo/documents/
  README.md                 this file
  generate.mjs              regenerates every PDF from the templates
  src/                      templates with {{PLACEHOLDERS}} and the shared base.css
  clean/                    rendered .html (exact source of each PDF) and .pdf
  with_issues/              same, plus NOTES.md listing the planted issues
```

The `.html` files next to each PDF are the filled templates, written by the generator, so you can open one in a browser to see exactly what was printed.

## Regenerating

The generator uses Playwright's bundled Chromium from the frontend workspace. Run it from `frontend/` so the `@playwright/test` import resolves:

```bash
cd frontend
node ../docs/demo/documents/generate.mjs
```

If Chromium is not installed yet: `cd frontend && npx playwright install chromium`.

To change a value, edit the template in `src/` (shared content) or the `SETS` object in `generate.mjs` (values that differ between the two sets), then rerun. Quick checks after regenerating:

```bash
pdfinfo docs/demo/documents/clean/tenancy_agreement.pdf | grep Pages
pdftotext docs/demo/documents/with_issues/business_profile.pdf - | grep 202355555
```

## Disclaimer

Every document is fictional and says so in its footer and body: "Fictional document produced for a software demonstration. Not issued by any authority." The registrar, the design studio, the landlord, the training institute, all persons, identification numbers, reference numbers and signatures are invented. No real company, UEN, logo or government crest is used. Do not present these files as genuine records.

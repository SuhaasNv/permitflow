# Demo documents

Fictional, text-based PDFs for demonstrating PermitFlow uploads and the AI verification step. They match the demo business used in the walkthroughs and the evaluation set, **Kopi & Kaya Toast House Pte. Ltd.** (the seed creates the two accounts only; type the form values from the table below) (UEN 202355555E, 10 Jalan Besar #01-12, Singapore 208787), so the AI check can cross-reference every field.

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
| `second_business/` | The production example: a second, unrelated restaurant (Serangoon Spice House Pte. Ltd., UEN 202411223K, 52 Serangoon Garden Way #01-05, contact Priya Raghavan), clean set, so the record left on https://permitflow.space is not the same business as every test fixture | All four documents consistent with that application; the form values to enter are in the table below |
| `with_issues/` | The "feedback round" demo: AI flags problems, officer requests changes, operator resubmits with the clean versions | Three findings: wrong UEN in the business profile, wrong unit number in the tenancy agreement, expired food hygiene certificate. The floor plan is fine. See `with_issues/NOTES.md` for the exact planted values and where they appear |

A typical demo: upload `with_issues/` first, walk through the findings, then replace the three flagged files with their `clean/` counterparts and show the application passing.

## Layout of this folder

```
docs/12-demo/documents/
  README.md                 this file
  clean/                    the four PDFs that agree with the Kopi & Kaya form values
  with_issues/              the four PDFs with planted defects, plus NOTES.md listing them
  second_business/          the four PDFs for Serangoon Spice House (the production example)
```

## How they were made

Each PDF was rendered by Chromium (Playwright) from an HTML template with the values filled in, so the text is selectable and the AI check can read it. The templates and the generator are working files and are not part of the repository; the PDFs are the fixtures the tests, the evaluation set (`backend/evals/cases.json`) and the walkthroughs use. To change a value, edit the PDF's source in the workshop and re-render; then check:

```bash
pdfinfo docs/12-demo/documents/clean/tenancy_agreement.pdf | grep Pages
pdftotext docs/12-demo/documents/with_issues/business_profile.pdf - | grep 202355555
```

## Disclaimer

Every document is fictional and says so in its footer and body: "Fictional document produced for a software demonstration. Not issued by any authority." The registrar, the design studio, the landlord, the training institute, all persons, identification numbers, reference numbers and signatures are invented. No real company, UEN, logo or government crest is used. Do not present these files as genuine records.

## Verified against the live check (19 Sep 2026, gpt-4.1-mini)

| Set | business_profile | floor_plan | tenancy_agreement | food_hygiene_certificate |
|-----|------------------|------------|-------------------|--------------------------|
| clean | Verified | Verified | Verified | Verified |
| with_issues | Issues found (UEN mismatch) | Verified | Issues found (address mismatch) | Issues found (expired) |

Quirk worth knowing before a demo: on the expired certificate the model also reported the "fictional document" disclaimer as possible prompt injection text. It is a false positive of the model, not of the platform's own injection heuristic, and it shows the "advisory only" stance well: the officer decides.

## Kopi & Kaya (clean and with_issues sets): form values

The values the `clean/` documents agree with, and that `backend/evals/cases.json` uses; the `with_issues/` set plants a different UEN, a different unit number and an expired certificate against these same values.

| Section | Field | Value |
|---|---|---|
| Business | Business name | Kopi & Kaya Toast House Pte. Ltd. |
| Business | UEN | 202355555E |
| Business | Entity type | Private limited |
| Business | Contact | Tan Wei Ling, weiling.tan@kopikaya.sg, +65 9123 4567 |
| Premises | Address | 10 Jalan Besar #01-12, Singapore 208787 |
| Premises | Floor area, type | 48 sqm, shophouse |
| Premises | Tenancy expiry | 2027-10-31 |
| Operations | Cuisine | Kaya toast, soft-boiled eggs, kopi and teh. |
| Operations | Seating, hours, handlers | 24, Mon-Sun 7am-9pm, 4 |
| Declarations | Both boxes | ticked |

## Second business: form values

| Section | Field | Value |
|---|---|---|
| Business | Business name | Serangoon Spice House Pte. Ltd. |
| Business | UEN | 202411223K |
| Business | Contact | Priya Raghavan, priya@serangoonspice.sg, +65 9876 5432 |
| Premises | Address | 52 Serangoon Garden Way #01-05, Singapore 555949 |
| Premises | Floor area, type | 48 sqm, shophouse |
| Premises | Tenancy expiry | 2027-10-31 |
| Operations | Cuisine | South Indian meals, tandoor dishes and teh tarik |
| Operations | Seating, hours, handlers | 24, Mon-Sun 7am-9pm, 4 |


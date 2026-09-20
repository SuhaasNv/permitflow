# 12 Demo

Material for demonstrating the product: the fictional documents that the walkthroughs, the acceptance scenarios and the evaluation set upload. Everything is invented (Kopi & Kaya Toast House Pte. Ltd., Jalan Besar); no real business, person or agency.

| Folder | What it holds |
|--------|---------------|
| `documents/` | Twelve PDFs in three sets: `clean/` (a complete application that passes every check), `with_issues/` (the same business with planted defects that the check should find; the planted values are in `with_issues/NOTES.md`), `second_business/` (a different business for a second application). `documents/README.md` gives the form values each set agrees with and how the PDFs were made |

Demo accounts are seeded by the backend (`README.md` at the root, "Demo accounts"); the seed creates the accounts only, the application data is typed in during the demo. Local quotas: the operator account has 60 automatic checks a day, so repeated demo runs on one account can hit the limit (the root README says how to raise it).

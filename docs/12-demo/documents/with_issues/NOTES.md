# Planted issues in this set

These four PDFs are the "feedback round" versions of the demo documents. Three of them contain one deliberate inconsistency each against the seeded application for Kopi & Kaya Toast House Pte. Ltd. (UEN 202355555E, 10 Jalan Besar #01-12, Singapore 208787). The AI verification step is expected to flag each one; the officer can then request a resubmission.

| File | Planted issue | Where it appears | Expected value |
|------|---------------|------------------|----------------|
| `business_profile.pdf` | UEN is one character off: `202355555F` | Reference line under the title, and row "Unique Entity Number (UEN)" in section 1 | `202355555E` |
| `tenancy_agreement.pdf` | Unit number transposed: `#01-21` | Cover page, Parties (2), Recital A, Schedule 1 "Premises" and "Tenant" rows | `#01-12` |
| `food_hygiene_certificate.pdf` | Certificate expired: valid until `3 January 2025` (assessed 3 January 2022, issued 4 January 2022) | "Valid until" and "Date of issue" boxes, "Issued at Singapore on" line | Issued 2 February 2026, valid until 1 February 2029 |
| `floor_plan.pdf` | None. Identical to the clean set | | |

Everything else (business name, incorporation date, contact person, email, phone, postal code, floor area, rent, term, landlord, seating, hours, staff count, certificate holder, course name, certificate number) matches the application in both sets.

The values are set in the `with_issues` block of `../generate.mjs`; the rendered HTML next to each PDF shows exactly what was printed.

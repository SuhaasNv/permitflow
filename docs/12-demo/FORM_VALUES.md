# Form values to copy and paste

Every field of a new Food Establishment Licence application, in the order the form asks for it, with the value that matches the demo documents. Each value sits in its own code block so it can be copied in one click. Field names and rules come from `backend/app/domain/form_schema.py`, the single source of truth for the server and the client.

Two businesses are available. Use **Kopi & Kaya** with `documents/clean/` and `documents/with_issues/`; use **Serangoon Spice House** with `documents/second_business/`. Everything is fictional.

---

## Kopi & Kaya Toast House (clean and with_issues documents)

### 1. Business details

Business name
```
Kopi & Kaya Toast House Pte. Ltd.
```

UEN
```
202355555E
```

Entity type: choose **Private limited company**

Contact person
```
Tan Wei Ling
```

Contact email
```
weiling.tan@kopikaya.sg
```

Contact phone
```
+65 9123 4567
```

### 2. Premises

Premises address
```
10 Jalan Besar #01-12
```

Postal code
```
208787
```

Premises type: choose **Shophouse**

Floor area (sqm)
```
48
```

Tenancy expiry date: pick **31 October 2027** in the date picker (stored as `2027-10-31`)

### 3. Operations

Description of food and cuisine
```
Kaya toast, soft-boiled eggs, kopi and teh.
```

Seating capacity
```
24
```

Operating hours
```
Mon-Sun 7am-9pm
```

Number of food handlers
```
4
```

### 4. Declarations

Tick both boxes:
- I confirm that the information provided is accurate and complete to the best of my knowledge.
- I consent to an inspection of the premises by a licensing officer at a mutually arranged time.

### 5. Documents

| Slot | Feedback-round demo (`documents/with_issues/`) | Clean run (`documents/clean/`) |
|---|---|---|
| Business profile (ACRA) | `business_profile.pdf` (UEN off by one character) | `business_profile.pdf` |
| Floor plan | `floor_plan.pdf` (matches) | `floor_plan.pdf` |
| Tenancy agreement | `tenancy_agreement.pdf` (unit `#01-21`) | `tenancy_agreement.pdf` |
| Food hygiene certificate | `food_hygiene_certificate.pdf` (expired) | `food_hygiene_certificate.pdf` |

Edge cases, on a separate draft: `documents/edge_cases/` (hidden and visible prompt injection, an empty PDF, a fake PDF); expected results in its README.

---

## Serangoon Spice House (second_business documents)

### 1. Business details

Business name
```
Serangoon Spice House Pte. Ltd.
```

UEN
```
202411223K
```

Entity type: choose **Private limited company**

Contact person
```
Priya Raghavan
```

Contact email
```
priya@serangoonspice.sg
```

Contact phone
```
+65 9876 5432
```

### 2. Premises

Premises address
```
52 Serangoon Garden Way #01-05
```

Postal code
```
555949
```

Premises type: choose **Shophouse**

Floor area (sqm)
```
48
```

Tenancy expiry date: pick **31 October 2027** (stored as `2027-10-31`)

### 3. Operations

Description of food and cuisine
```
South Indian meals, tandoor dishes and teh tarik
```

Seating capacity
```
24
```

Operating hours
```
Mon-Sun 7am-9pm
```

Number of food handlers
```
4
```

### 4. Declarations

Tick both boxes.

### 5. Documents

The four files in `documents/second_business/`, one per slot with the same names.

---

## Wrong values for showing validation

Type one of these, move to the next field to see the message, then replace it with the correct value above.

| Field | Wrong value | Message (server wording; the form may phrase number errors slightly differently) |
|---|---|---|
| UEN | `12345` | Enter a valid UEN, for example 202312345K. |
| Contact email | `weiling.tan` | Enter a valid email address. |
| Contact phone | `123` | Enter 8 to 15 digits. |
| Postal code | `2087` | Enter the 6-digit postal code, for example 208787. |
| Floor area (sqm) | `0` | Must be at least 1. |
| Seating capacity | `2.5` | Must be a whole number. |

The same rules run on the server, so a request that skips the form gets the same messages back as a 422.

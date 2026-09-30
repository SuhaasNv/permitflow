/* The four flows. Text is short on purpose: the slide shows the path, the speaker adds the detail. */

// Left-to-right chain within a row; `yes` labels leave a check.
function chain(ids, nodes, dir = 'ltr') {
  const byId = Object.fromEntries(nodes.map((n) => [n.id, n]))
  const out = []
  for (let i = 0; i < ids.length - 1; i++) {
    const from = byId[ids[i]]
    out.push({
      from: ids[i],
      to: ids[i + 1],
      fs: dir === 'ltr' ? 'r' : 'l',
      ts: dir === 'ltr' ? 'l' : 'r',
      label: from.check ? from.yes || 'yes' : '',
    })
  }
  return out
}

const SPECS = {}

/* 1. Sign-in ------------------------------------------------------------------------------------- */
{
  const nodes = [
    { id: 'a1', row: 'A', col: 0, step: '1', actor: 'browser', title: 'Enter email and password', detail: 'Login page with a show-password toggle', file: 'features/auth/LoginPage.tsx' },
    { id: 'a2', row: 'A', col: 1, step: '2', actor: 'api', check: true, title: 'Under the rate limit?', detail: '20 sign-in attempts a minute per client, and 10 failed ones', file: 'core/rate_limit.py',
      pill: { code: '429', text: 'Too many requests. Try again in a moment.' } },
    { id: 'a3', row: 'A', col: 2, step: '3', actor: 'api', title: 'Find the user by email', detail: 'One lookup in the users table', file: 'services/auth.py',
      pill: { kind: 'store', text: 'users: email, Argon2 hash, role, active', label: 'read' } },
    { id: 'a4', row: 'A', col: 3, step: '4', actor: 'api', check: true, title: 'Active and password correct?', detail: 'Argon2 verify; unknown email checks a dummy hash, so timing is the same', file: 'core/security.py',
      pill: { code: '401', text: 'Email or password is incorrect. (Same answer for both.)' } },
    { id: 'a5', row: 'A', col: 4, step: '5', actor: 'api', title: 'Sign a token (JWT)', detail: 'HS256 with JWT_SECRET: user id and role, valid for 8 hours', file: 'core/security.py' },
    { id: 'a6', row: 'A', col: 5, step: '6', actor: 'browser', title: 'Keep the token', detail: 'In sessionStorage (this tab only), then open the home page for the role', file: 'features/auth/AuthContext.tsx' },

    { id: 'b1', row: 'B', col: 0, step: '7', actor: 'browser', title: 'Send the token', detail: 'Authorization: Bearer <token> on every API call', file: 'api/client.ts' },
    { id: 'b2', row: 'B', col: 1, step: '8', actor: 'api', check: true, title: 'Signature valid and not expired?', detail: 'Checked with the same secret', file: 'api/deps.py',
      pill: { code: '401', text: 'Your session has expired. Sign in again.' } },
    { id: 'b3', row: 'B', col: 2, step: '9', actor: 'api', check: true, title: 'User still active?', detail: 'User re-read from the database on every request; the role comes from the row', file: 'services/auth.py',
      pill: { code: '401', text: 'Invalid or missing credentials.' } },
    { id: 'b4', row: 'B', col: 3, step: '10', actor: 'api', check: true, title: 'Role allowed on this route?', detail: 'Operator and officer routes; the admin role is reserved', file: 'api/deps.py  require_role',
      pill: { code: '403', text: 'Not available for your role.' } },
    { id: 'b5', row: 'B', col: 4, step: '11', actor: 'api', check: true, title: 'Allowed to see this record?', detail: 'Loaded by id, then the owner is checked. Operators see only their own.', file: 'repositories/applications.py',
      pill: { code: '404', text: 'Application not found. (No hint that it exists.)' } },
    { id: 'b6', row: 'B', col: 5, step: '12', actor: 'api', done: true, tagLabel: 'API', title: 'Run the request', detail: 'The service does its work in one database transaction' },
  ]
  SPECS.signin = {
    part: 'Flow 1 · Sign-in',
    title: 'sign-in',
    sub: 'From the login form to a token, and the checks every later request passes',
    actors: ['browser', 'api', 'db'],
    phases: {
      A: { n: 1, t: 'Sign in', s: 'POST /api/v1/auth/login' },
      B: { n: 2, t: 'Every request after', s: 'api/deps.py runs before each protected route' },
    },
    nodes,
    edges: [...chain(['a1', 'a2', 'a3', 'a4', 'a5', 'a6'], nodes), ...chain(['b1', 'b2', 'b3', 'b4', 'b5', 'b6'], nodes)],
    banner: [
      { k: 'No fallback secret', v: 'The app refuses to start without a real JWT_SECRET, in every environment, tests included.' },
      { k: 'Nothing leaks', v: 'Wrong email and wrong password get the same message and take the same time.' },
      { k: 'Honest gap', v: 'Token in sessionStorage. Production: httpOnly cookie with CSRF, short tokens, Singpass or Corppass, MFA.' },
    ],
  }
}

/* 2. Creating an application --------------------------------------------------------------------- */
{
  const nodes = [
    { id: 'a1', row: 'A', col: 0, step: '1', actor: 'browser', title: 'Click New application', detail: 'From the operator dashboard' },
    { id: 'a2', row: 'A', col: 1, step: '2', actor: 'api', check: true, title: 'Fewer than 20 open drafts?', detail: 'Stops a script filling the database with drafts', file: 'services/quotas.py',
      pill: { code: '409', text: 'draft_limit: submit or delete a draft first.' } },
    { id: 'a3', row: 'A', col: 2, step: '3', actor: 'db', title: 'Take a reference number', detail: 'From a database sequence: PF-2026-001234. Never repeats.', file: 'repositories/applications.py' },
    { id: 'a4', row: 'A', col: 3, step: '4', actor: 'db', title: 'Save in one transaction', detail: 'Application row (status draft, empty working copy) and audit: application.created', file: 'services/applications.py' },
    { id: 'a5', row: 'A', col: 4, step: '5', actor: 'api', title: 'Serve the form schema', detail: 'Four sections; every field rule written once, in Python', file: 'domain/form_schema.py' },
    { id: 'a6', row: 'A', col: 5, step: '6', actor: 'browser', title: 'Build the form', detail: 'Zod validators made from that schema; each field checked when you leave it', file: 'lib/zodFromSchema.ts' },

    { id: 'b1', row: 'B', col: 0, step: '7', actor: 'browser', title: 'Save and continue', detail: 'Or Save and exit. Leaving with unsaved edits asks first.', file: 'operator/SectionForm.tsx' },
    { id: 'b2', row: 'B', col: 1, step: '8', actor: 'api', check: true, title: 'Your application?', detail: 'Row locked for this save; loaded by id, then the owner is checked', file: 'services/applications.py',
      pill: { code: '404', text: 'Application not found.' } },
    { id: 'b3', row: 'B', col: 2, step: '9', actor: 'api', check: true, title: 'Section open for changes?', detail: 'Draft: every section.\nResubmission: only what the officer flagged.', file: 'domain/editability.py',
      pill: { code: '403', text: 'The licensing officer did not ask for changes to this section.' } },
    { id: 'b4', row: 'B', col: 3, step: '10', actor: 'api', check: true, title: 'Valid on the server?', detail: 'Same rules as the browser. A draft may leave fields blank, never wrong.', file: 'domain/form_schema.py',
      pill: { code: '422', text: 'A message per field, e.g. Enter a valid UEN.' } },
    { id: 'b5', row: 'B', col: 4, step: '11', actor: 'db', title: 'Save the working copy', detail: 'draft_data (JSON), version + 1, audit: section.updated with field names, not values' },
    { id: 'b6', row: 'B', col: 5, step: '12', actor: 'browser', done: true, tagLabel: 'Browser', title: 'Update the progress card', detail: '4 sections + 4 documents. The same check guards Submit.', file: 'domain/completeness.py' },
  ]
  SPECS.application = {
    part: 'Flow 2 · Creating an application',
    title: 'creating an application',
    sub: 'Start a draft, then save the form one section at a time',
    actors: ['browser', 'api', 'db'],
    phases: {
      A: { n: 1, t: 'Start a draft', s: 'POST /api/v1/applications' },
      B: { n: 2, t: 'Save a section', s: 'PATCH /applications/{id}/sections/{key}' },
    },
    nodes,
    edges: [...chain(['a1', 'a2', 'a3', 'a4', 'a5', 'a6'], nodes), ...chain(['b1', 'b2', 'b3', 'b4', 'b5', 'b6'], nodes)],
    banner: [
      { k: 'One source of rules', v: 'form_schema.py feeds both the server checks and the browser validators, so they cannot disagree.' },
      { k: 'Two copies of the form', v: 'draft_data is the working copy. Submit freezes it into a revision that never changes.' },
      { k: 'Honest gap', v: 'No autosave here: saved per section. Two tabs: the last save wins, with a warning.' },
    ],
  }
}

/* 3. Document upload ----------------------------------------------------------------------------- */
{
  const nodes = [
    { id: 'a1', row: 'A', col: 0, step: '1', actor: 'browser', title: 'Choose a file', detail: 'Drag and drop or the picker, for one of the four document types', file: 'documents/DropZone.tsx' },
    { id: 'a2', row: 'A', col: 1, step: '2', actor: 'browser', check: true, title: 'Passes the quick check?', detail: 'Type, 10 MB, not empty. For speed only; the server checks again.', file: 'api/documents.ts',
      pill: { kind: 'info', text: 'A message is shown. Nothing is sent.' } },
    { id: 'a3', row: 'A', col: 2, step: '3', actor: 'browser', title: 'Upload with progress', detail: 'Multipart POST through XHR, so the card shows a real progress bar', file: 'api/documents.ts' },
    { id: 'a4', row: 'A', col: 3, step: '4', actor: 'api', check: true, title: 'Declared size under 10 MB?', detail: 'Content-Length checked before the body is read', file: 'main.py',
      pill: { code: '400', text: 'The file is larger than 10 MB.' } },
    { id: 'a5', row: 'A', col: 4, step: '5', actor: 'api', check: true, title: 'Allowed type?', detail: 'pdf, png, jpg, jpeg, txt: extension and MIME type', file: 'domain/uploads.py',
      pill: { code: '400', text: 'Only PDF, PNG, JPG or TXT files are accepted.' } },
    { id: 'a6', row: 'A', col: 5, step: '6', actor: 'api', check: true, title: 'Yours, and open for changes?', detail: 'Row locked. Draft: all four. Resubmission: flagged ones only.', file: 'services/documents.py',
      pill: { code: '404 / 403', text: 'Not found, or not open for changes.' } },

    { id: 'b1', row: 'B', col: 0, step: '7', actor: 'api', check: true, title: 'Content matches the type?', detail: 'Streamed in 64 KB chunks: magic bytes, 10 MB cap, sha256 as it goes', file: 'services/documents.py',
      pill: { code: '400', text: 'The file content does not match its type.' } },
    { id: 'b2', row: 'B', col: 1, step: '8', actor: 'storage', title: 'Write the file', detail: 'Server-made name: <application id>/<random>.pdf. Written as .part, then renamed.', file: 'infra/storage.py' },
    { id: 'b3', row: 'B', col: 2, step: '9', actor: 'db', check: true, title: 'Different from the current file?', detail: 'sha256 compared with this document type', file: 'services/documents.py',
      pill: { kind: 'info', label: 'no, same', text: 'No change: the copy is deleted, no new AI check.' } },
    { id: 'b4', row: 'B', col: 3, step: '10', actor: 'db', title: 'Save in one transaction', detail: 'New document (old one kept as superseded), a pending AI run, an audit row' },
    { id: 'b5', row: 'B', col: 4, step: '11', actor: 'api', title: 'Start the AI check', detail: 'Background task, only after the commit', file: 'api/v1/applications.py' },
    { id: 'b6', row: 'B', col: 5, step: '12', actor: 'browser', done: true, tagLabel: 'Browser', title: 'Card shows Checking', detail: '201 back at once. Polls every 2 s while the tab is visible.', file: 'documents/DocumentSlot.tsx' },
  ]
  SPECS.upload = {
    part: 'Flow 3 · Document upload',
    title: 'document upload',
    sub: 'From the file picker to a stored document and a queued AI check',
    actors: ['browser', 'api', 'storage', 'db'],
    phases: {
      A: { n: 1, t: 'Gates before anything is stored', s: 'POST /applications/{id}/documents' },
      B: { n: 2, t: 'Stream, deduplicate, record', s: 'continues from step 6' },
    },
    nodes,
    edges: [
      ...chain(['a1', 'a2', 'a3', 'a4', 'a5', 'a6'], nodes),
      { from: 'a6', to: 'b1', fs: 'r', ts: 'l', label: '', via: RETURN },
      ...chain(['b1', 'b2', 'b3', 'b4', 'b5', 'b6'], nodes),
    ],
    banner: [
      { k: 'Allowlist, not blocklist', v: 'Only five types get in, and the content is checked, not just the file name.' },
      { k: 'Nothing half-saved', v: 'A rejected upload deletes its partial file; the database commit comes last.' },
      { k: 'Honest gap', v: 'No virus scan, no OCR. Production: scanning with quarantine, object storage, backups.' },
    ],
  }
}

/* 4. AI verification ----------------------------------------------------------------------------- */
{
  const nodes = [
    { id: 'a1', row: 'A', col: 0, step: '1', actor: 'db', check: true, title: 'Within the daily quota?', detail: 'Checked at upload: 60 checks per applicant and 1,000 for the platform, per day', file: 'services/quotas.py',
      pill: { kind: 'status', text: 'Stored as unavailable: daily limit reached. No call.' } },
    { id: 'a2', row: 'A', col: 1, step: '2', actor: 'task', title: 'Claim the run', detail: 'pending to running in one atomic update; frees its DB connection before the slow part', file: 'services/verification.py' },
    { id: 'a3', row: 'A', col: 2, step: '3', actor: 'task', check: true, title: 'Text found?', detail: 'pypdf: up to 30 pages, 20,000 characters, 10 s. No OCR for images.', file: 'infra/extraction.py',
      pill: { kind: 'status', text: 'Stored as unreadable. No call.' } },
    { id: 'a4', row: 'A', col: 3, step: '4', actor: 'task', check: true, title: 'Provider set up?', detail: 'Mock in tests and CI. OpenAI when a key is set.', file: 'infra/ai/factory.py',
      pill: { kind: 'status', text: 'Stored as unavailable: provider not configured.' } },
    { id: 'a5', row: 'A', col: 4, step: '5', actor: 'rules', title: 'Scan for injection', detail: '8 English phrases, such as "ignore previous instructions". Used again at step 9.', file: 'domain/verification_rules.py' },
    { id: 'a6', row: 'A', col: 5, step: '6', actor: 'task', title: 'Build the request', detail: 'Document type, only the matching form section, the text in <document> tags, today in Singapore' },

    { id: 'b1', row: 'B', col: 0, step: '7', actor: 'openai', title: 'Call gpt-4.1-mini', detail: 'Temperature 0 · 30 s timeout · 1 retry · strict JSON schema · prompt 2026-09-19.3', file: 'infra/ai/openai_provider.py' },
    { id: 'b2', row: 'B', col: 1, step: '8', actor: 'rules', check: true, title: 'Answer on time and valid?', detail: 'Wire schema, then our model: confidence 0 to 1, status agrees with issues',
      pill: { kind: 'status', text: 'Timeout: unavailable. Bad answer: failed.' } },
    { id: 'b3', row: 'B', col: 2, step: '9', actor: 'rules', title: 'Decide the status', detail: 'Injection: needs review\nModel unreadable: unreadable\nIssues: issues found\nVerified under 0.6: needs review\nOtherwise: verified' },
    { id: 'b4', row: 'B', col: 3, step: '10', actor: 'db', title: 'Save the result', detail: 'Status, issues with evidence, model, latency; the audit row records the prompt version' },
    { id: 'b5', row: 'B', col: 4, step: '11', actor: 'browser', title: 'Show it by role', detail: 'Operator: a plain label and what to fix. Officer: adds confidence, evidence, model.' },
    { id: 'b6', row: 'B', col: 5, step: '12', actor: 'officer', done: true, tagLabel: 'Officer', title: 'A person decides', detail: 'The check never changes status, feedback or what can be edited' },
  ]
  SPECS.ai = {
    part: 'Flow 4 · AI verification',
    title: 'AI verification',
    sub: 'After the upload commits: the model gives advice, our code sets the status, an officer decides',
    actors: ['task', 'rules', 'openai', 'db', 'browser'],
    phases: {
      A: { n: 1, t: 'Prepare without spending a call', s: 'services/verification.py  run_verification' },
      B: { n: 2, t: 'Ask the model, then decide', s: 'continues from step 6' },
    },
    nodes,
    edges: [
      ...chain(['a1', 'a2', 'a3', 'a4', 'a5', 'a6'], nodes),
      { from: 'a6', to: 'b1', fs: 'r', ts: 'l', label: '', via: RETURN },
      ...chain(['b1', 'b2', 'b3', 'b4', 'b5', 'b6'], nodes),
    ],
    banner: [
      { k: 'Advisory only', v: 'The AI never changes status, feedback or what can be edited. A person decides.' },
      { k: 'Never crashes the app', v: 'Every failure is stored as a status. After a restart, stuck runs become failed with a Re-run.' },
      { k: 'Honest gaps', v: 'English-only injection check, no OCR, confidence not calibrated, text sent to a US provider.' },
    ],
  }
}

/* 5. Submit -------------------------------------------------------------------------------------- */
{
  const nodes = [
    { id: 'a1', row: 'A', col: 0, step: '1', actor: 'browser', title: 'Press Submit', detail: 'Review page. AI checks may still be running: they never block a submit.', file: 'operator/ReviewPage.tsx' },
    { id: 'a2', row: 'A', col: 1, step: '2', actor: 'browser', check: true, title: 'Not already sending?', detail: 'A second click while the first request is on its way is ignored',
      pill: { kind: 'info', text: 'Nothing is sent twice.' } },
    { id: 'a3', row: 'A', col: 2, step: '3', actor: 'api', check: true, title: 'Your application?', detail: 'Row locked (FOR UPDATE); loaded by id, then the owner is checked', file: 'services/submission.py',
      pill: { code: '404', text: 'Application not found.' } },
    { id: 'a4', row: 'A', col: 3, step: '4', actor: 'api', check: true, title: 'Complete?', detail: 'Same check as the progress card: 4 sections valid, 4 documents present', file: 'domain/completeness.py',
      pill: { code: '422', text: 'What is missing, e.g. Section: Premises' } },
    { id: 'a5', row: 'A', col: 4, step: '5', actor: 'api', check: true, title: 'Still a draft?', detail: 'State machine: draft to Application Received, operator only', file: 'domain/workflow.py',
      pill: { code: '409', text: 'This application is Submitted. Only a draft can be submitted.' } },
    { id: 'a6', row: 'A', col: 5, step: '6', actor: 'db', title: 'Freeze Revision 1', detail: 'A full copy of the form plus the 4 document ids. Never updated again.', file: 'models/application.py' },

    { id: 'b1', row: 'B', col: 0, step: '7', actor: 'db', title: 'Update the application', detail: 'Status Application Received, current revision set, version + 1' },
    { id: 'b2', row: 'B', col: 1, step: '8', actor: 'db', title: 'Write two audit rows', detail: 'revision.submitted and status.changed, in the same transaction', file: 'repositories/audit.py' },
    { id: 'b3', row: 'B', col: 2, step: '9', actor: 'db', title: 'Notify every officer', detail: 'One in-app notification per active officer', file: 'services/notifications.py' },
    { id: 'b4', row: 'B', col: 3, step: '10', actor: 'db', title: 'Commit once', detail: 'Revision, status, audit and notifications: all saved, or none' },
    { id: 'b5', row: 'B', col: 4, step: '11', actor: 'api', title: 'Then send messages', detail: 'Only after the commit, so nobody hears about a failed save. Email is mocked.' },
    { id: 'b6', row: 'B', col: 5, step: '12', actor: 'browser', done: true, tagLabel: 'Browser', title: 'Submitted page', detail: 'Redirect with replace, so Back does not reopen the form. The form is locked.' },
  ]
  SPECS.submit = {
    part: 'Flow 5 · Submit',
    title: 'submit',
    sub: 'The moment a draft becomes an application: checked, frozen and recorded in one transaction',
    actors: ['browser', 'api', 'db'],
    phases: {
      A: { n: 1, t: 'Check, then freeze', s: 'POST /api/v1/applications/{id}/submit' },
      B: { n: 2, t: 'One transaction, then tell people', s: 'continues from step 6' },
    },
    nodes,
    edges: [
      ...chain(['a1', 'a2', 'a3', 'a4', 'a5', 'a6'], nodes),
      { from: 'a6', to: 'b1', fs: 'r', ts: 'l', label: '', via: RETURN },
      ...chain(['b1', 'b2', 'b3', 'b4', 'b5', 'b6'], nodes),
    ],
    banner: [
      { k: 'Double click, four stops', v: 'The button, the row lock, the state check and a unique revision number: always one revision.' },
      { k: 'AI never blocks', v: 'Submit works while checks run or when OpenAI is down; the officer sees results when they finish.' },
      { k: 'Honest gap', v: 'Email is mocked and every officer is notified: there is no case assignment yet.' },
    ],
  }
}

/* 6. Officer queue and case ---------------------------------------------------------------------- */
{
  const nodes = [
    { id: 'a1', row: 'A', col: 0, step: '1', actor: 'browser', title: 'Open the review queue', detail: 'Tabs: My turn, Waiting on operator, Decided, All. Search. Refreshes every 30 s.', file: 'officer/QueuePage.tsx' },
    { id: 'a2', row: 'A', col: 1, step: '2', actor: 'api', check: true, title: 'Officer role?', detail: 'The officer guard runs on every officer route', file: 'api/deps.py',
      pill: { code: '403', text: 'Not available for your role.' } },
    { id: 'a3', row: 'A', col: 2, step: '3', actor: 'db', title: 'Every submitted application', detail: 'Drafts are left out; the applicant comes with each row', file: 'repositories/applications.py' },
    { id: 'a4', row: 'A', col: 3, step: '4', actor: 'db', title: 'Counts in a batch', detail: 'Revisions, open feedback, checks needing attention: a few queries, not one per row', file: 'services/officer_queue.py' },
    { id: 'a5', row: 'A', col: 4, step: '5', actor: 'api', title: "Work out whose turn", detail: 'A table maps each status to a next action: Start review, Waiting on operator, Decide', file: 'domain/officer_actions.py' },
    { id: 'a6', row: 'A', col: 5, step: '6', actor: 'browser', title: 'Rows in officer words', detail: 'Officer label and colour, next action, revision count, checks to look at' },

    { id: 'b1', row: 'B', col: 0, step: '7', actor: 'browser', title: 'Open a case', detail: 'Refetched on focus, and every 2 s while a check is still running', file: 'officer/queries.ts' },
    { id: 'b2', row: 'B', col: 1, step: '8', actor: 'api', check: true, title: 'Submitted?', detail: 'A draft is invisible to officers', file: 'services/officer_view.py',
      pill: { code: '404', text: 'Application not found.' } },
    { id: 'b3', row: 'B', col: 2, step: '9', actor: 'db', title: 'Read the latest revision', detail: 'Sections come from the frozen snapshot, not the working copy' },
    { id: 'b4', row: 'B', col: 3, step: '10', actor: 'db', title: 'Documents and checks', detail: 'Current documents with the full check: confidence, evidence, model' },
    { id: 'b5', row: 'B', col: 4, step: '11', actor: 'api', title: 'Allowed actions', detail: 'From the state machine, with the reason a button is disabled', file: 'domain/workflow.py' },
    { id: 'b6', row: 'B', col: 5, step: '12', actor: 'browser', done: true, tagLabel: 'Browser', title: 'The case page', detail: 'Sections, documents, feedback, revisions, what changed, and a version for 409s' },
  ]
  SPECS.officer = {
    part: 'Flow 6 · Officer queue and case',
    title: 'officer queue and case',
    sub: 'What the licensing officer sees first, and everything a case page is built from',
    actors: ['browser', 'api', 'db'],
    phases: {
      A: { n: 1, t: 'The queue', s: 'GET /api/v1/officer/applications' },
      B: { n: 2, t: 'One case', s: 'GET /api/v1/officer/applications/{id}' },
    },
    nodes,
    edges: [
      ...chain(['a1', 'a2', 'a3', 'a4', 'a5', 'a6'], nodes),
      { from: 'a6', to: 'b1', fs: 'r', ts: 'l', label: '', via: RETURN },
      ...chain(['b1', 'b2', 'b3', 'b4', 'b5', 'b6'], nodes),
    ],
    banner: [
      { k: 'One table, one truth', v: 'Buttons come from the state machine, so the page cannot offer a move the server refuses.' },
      { k: 'Reads what was sent', v: 'The case shows the submitted snapshot; the operator’s later edits stay in their own copy.' },
      { k: 'Honest gap', v: 'On main the queue row reads name and address from the working copy (fixed on dev); no case assignment.' },
    ],
  }
}

from lib import *

def login():
    body = f'''
<div style="display:flex;height:100%">
  <section style="width:520px;background:var(--surface);border-right:1px solid var(--line);padding:56px 64px;display:flex;flex-direction:column">
    <a class="brand" href="Landing.dc.html" style="margin-bottom:56px">{LOGO_MARK}<span class="brand-name">PermitFlow</span><span class="brand-sub">Licensing Services</span></a>
    <h1 class="h1" style="margin-bottom:6px">Sign in</h1>
    <p class="muted" style="margin-bottom:28px">Use your registered email address and password.</p>
    <form class="stack" style="gap:18px" action="OperatorDashboard.dc.html">
      {field('Email address','weiling.tan@kopikaya.sg','email',placeholder='name@company.sg')}
      {field('Password','••••••••••••','password')}
      <div class="row-b"><label class="check"><input type="checkbox" checked><span>Keep me signed in on this device</span></label><a href="Main.dc.html" class="small">Forgot password?</a></div>
      <a class="btn primary" href="OperatorDashboard.dc.html" style="height:44px">Sign in</a>
    </form>
    <div class="meta" style="margin-top:auto;line-height:18px;display:flex;flex-direction:column;gap:6px"><span>{ic('lock',12)} Sign-in is paused for a minute after 10 failed attempts.</span><span>Licensing officers and administrators: <a href="OfficerQueue.dc.html" style="font-weight:600">staff sign-in</a> · <a href="Landing.dc.html">About PermitFlow</a></span></div>
  </section>
  <section style="flex:1;padding:72px 80px;display:flex;flex-direction:column;justify-content:center;gap:28px;background:var(--bg)">
    <div><div class="meta" style="letter-spacing:.08em;text-transform:uppercase;font-weight:600;color:var(--primary);margin-bottom:12px">Food Establishment Licence</div>
    <h2 class="h1" style="font-size:32px;line-height:40px;max-width:520px">Apply, respond to officer feedback and track your licence in one place.</h2></div>
    <p class="muted" style="max-width:480px;font-size:16px;line-height:26px">Uploads are checked automatically so you can fix problems before you submit. Every decision is made by a licensing officer.</p>
    <div class="card" style="max-width:520px;padding:16px 20px;margin-top:8px">
      <div class="label" style="margin-bottom:10px">Before you start, have these ready</div>
      <div class="stack-s small">
        <div class="row" style="gap:10px"><span style="color:var(--success)">{ic('check',15)}</span><span>ACRA business profile (PDF, issued within 6 months)</span></div>
        <div class="row" style="gap:10px"><span style="color:var(--success)">{ic('check',15)}</span><span>Floor plan showing the food preparation area</span></div>
        <div class="row" style="gap:10px"><span style="color:var(--success)">{ic('check',15)}</span><span>Signed tenancy agreement covering the licence period</span></div>
        <div class="row" style="gap:10px"><span style="color:var(--success)">{ic('check',15)}</span><span>Food hygiene certificate</span></div>
      </div>
      <div class="meta" style="margin-top:12px">Takes about 20 minutes. Save a draft and return any time.</div>
    </div>

  </section>
</div>'''
    return page(body, 1280, 900, 'Sign in')

def op_dashboard():
    content = f'''
<a class="card" href="OperatorApplication.dc.html" style="display:flex;align-items:center;gap:20px;padding:18px 24px;margin-bottom:12px;border-color:var(--warning-line);color:inherit;text-decoration:none">
  <span style="width:40px;height:40px;border-radius:50%;background:var(--warning-soft);color:var(--warning);display:flex;align-items:center;justify-content:center;flex-shrink:0">{ic('flag',18)}</span>
  <div style="flex:1;min-width:0"><div class="eyebrow" style="color:var(--warning);margin-bottom:2px">Needs your action</div><div class="h3">PF-2026-000214 · the licensing office has asked for 3 changes</div><div class="small muted">Requested 16 Sep, 15:42 · reply within 14 days to keep the application moving</div></div>
  <span class="btn primary">Respond {ic('arrowr',16)}</span>
</a>
<p class="small muted" style="margin:0 2px 24px">Also: <b>2</b> with the licensing office · <b>1</b> draft not yet submitted</p>
<div class="stack" style="gap:24px">
  <div class="card">
    <div class="card-h"><h2 class="h3">My applications</h2><span class="meta">4 applications · sorted by last update</span></div>
    <table class="table">
      <colgroup><col style="width:190px"><col><col style="width:260px"><col style="width:140px"><col style="width:120px"></colgroup><thead><tr><th>Reference</th><th>Business</th><th>Status</th><th>Updated</th><th></th></tr></thead>
      <tbody>
        <tr class="rowlink"><td><a class="ref" href="OperatorApplication.dc.html">PF-2026-000214</a><div class="meta">Revision 1</div></td><td>Kopi &amp; Kaya Toast House<div class="meta">10 Jalan Besar #01-12</div></td><td>{status_badge('pending_pre_site_resubmission')}<div class="meta" style="margin-top:4px">3 items to address</div></td><td class="num">16 Sep, 15:42</td><td class="r"><a class="btn secondary sm" href="OperatorApplication.dc.html">Respond</a></td></tr>
        <tr class="rowlink"><td><a class="ref" href="OperatorApplication.dc.html">PF-2026-000203</a><div class="meta">Revision 2</div></td><td>Kopi &amp; Kaya Toast House, Tampines<div class="meta">3 Tampines Central 1 #02-08</div></td><td>{status_badge('under_review')}</td><td class="num">14 Sep, 09:10</td><td class="r"><a class="btn ghost sm" href="OperatorApplication.dc.html">View</a></td></tr>
        <tr class="rowlink"><td><a class="ref" href="OperatorApplication.dc.html">PF-2026-000198</a><div class="meta">Revision 1</div></td><td>Kopi &amp; Kaya Toast House, Bedok<div class="meta">208 New Upper Changi Rd #01-651</div></td><td>{status_badge('site_visit_scheduled')}</td><td class="num">11 Sep, 17:05</td><td class="r"><a class="btn ghost sm" href="OperatorApplication.dc.html">View</a></td></tr>
        <tr class="rowlink"><td><a class="ref" href="ApplicationForm.dc.html">PF-2026-000231</a><div class="meta">Draft</div></td><td>Kopi &amp; Kaya Toast House, Clementi<div class="meta">Premises not entered yet</div></td><td>{status_badge('draft')}<div class="meta" style="margin-top:4px">35% complete</div></td><td class="num">Today, 08:51</td><td class="r"><a class="btn secondary sm" href="ApplicationForm.dc.html">Continue</a></td></tr>
      </tbody>
    </table>
  </div>
  <div class="split" style="grid-template-columns:minmax(0,1fr) minmax(0,1fr)">
    <div class="card">
      <div class="card-h"><h2 class="h3">Recent activity</h2><a class="small" href="OperatorHistory.dc.html">View all</a></div>
      <div class="card-b" style="padding-bottom:4px">{timeline([
        ('w','Changes requested','PF-2026-000214 · 3 items flagged by the licensing office','16 Sep 2026, 15:42'),
        ('i','Under review','PF-2026-000203 · an officer has started reviewing','14 Sep 2026, 09:10'),
        ('','Site visit pending','PF-2026-000198 · you will be contacted to arrange a date','11 Sep 2026, 17:05'),
        ('s','Application submitted','PF-2026-000214 · Revision 1 received','10 Sep 2026, 11:23'),
      ])}</div>
    </div>
    <div class="card card-b" style="padding:16px 20px">
      <div class="row" style="gap:10px;margin-bottom:6px">{ic('help',18)}<span class="h3">Before you submit</span></div>
      <p class="small muted">You will need your ACRA business profile, a floor plan, the signed tenancy agreement and a food hygiene certificate. Upload PDFs where you can: they are checked automatically, scanned images are stored but cannot be read by the checker.</p>
    </div>
  </div>
</div>'''
    body = shell('operator','Dashboard',content,title='Good morning, Wei Ling',sub='Here is what needs your attention today.',actions=f'<a class="btn primary" href="ApplicationForm.dc.html">{ic("plus",16)}New application</a>',notif=2)
    return page(body, 1280, 940, 'Operator dashboard')

def app_form():
    content = f'''
<div class="statusbar has-steps">
  {status_badge('draft',lg=True)}
  <span class="expl">Not yet submitted. You can save and return any time.</span>
  <span class="meta num" style="margin-left:auto;white-space:nowrap">Step 2 of 6</span>
</div>
<div class="steps">{stepper(['Business','Premises','Operations','Declarations','Documents','Review'],1)}</div>
<div class="split-l">
  <aside class="stack">
    <nav class="secnav" aria-label="Form sections">
      <a href="#business">{ic('check',14)}<span>Business details</span><span class="st ok">{ic('check',11)}</span></a>
      <a class="active" href="#premises">{ic('home',14)}<span>Premises</span><span class="st err">{ic('x',11)}</span></a>
      <a href="#operations">{ic('activity',14)}<span>Operations</span><span class="st todo"></span></a>
      <a href="#declarations">{ic('shield',14)}<span>Declarations</span><span class="st todo"></span></a>
      <div class="divider" style="margin:6px 4px"></div>
      <a href="Documents.dc.html">{ic('file',14)}<span>Documents</span><span class="st todo"></span></a>
      <a href="ReviewSubmit.dc.html">{ic('check',14)}<span>Review</span><span class="st todo"></span></a>
    </nav>
    <div class="meta" style="padding:0 4px;line-height:18px">{ic('check',12)} Draft saved 2 minutes ago · 1 of 6 steps complete</div>
  </aside>
  <div class="stack" style="gap:20px">
    <div class="alert error">{ic('alert',18)}<div><b>2 fields need attention before this section can be saved.</b><div class="small" style="margin-top:2px"><a href="#postal" style="color:inherit;font-weight:600">Postal code</a> · <a href="#area" style="color:inherit;font-weight:600">Floor area</a></div></div></div>
    <section class="fsec" id="premises">
      <div class="fsec-h"><h2 class="h3">Premises</h2><span class="meta">Where the food will be prepared and sold</span></div>
      <div class="fsec-b fgrid">
        {field('Premises address','Blk 321 Clementi Avenue 3 #01-08',help='Include the unit number as shown on the tenancy agreement.',wide=True)}
        {field('Postal code','12032',error='Enter the 6-digit postal code, for example 120321.',attrs='id="postal" inputmode="numeric"')}
        {field('Premises type','Shophouse','select')}
        {field('Floor area (sqm)','',kind='number',help='Total area under the tenancy, including kitchen and seating.',error='Floor area is required.',attrs='id="area"')}
        {field('Tenancy expiry date','2027-10-31','date',help='Must be after the licence start date.')}
      </div>
      <div class="card-f"><a class="btn ghost" href="ApplicationForm.dc.html">Discard changes</a><a class="btn secondary" href="ApplicationForm.dc.html">Save section</a><a class="btn primary" href="ApplicationForm.dc.html">Save and continue {ic('arrowr',16)}</a></div>
    </section>
    <section class="fsec" id="business">
      <div class="fsec-h"><h2 class="h3">Business details</h2>{badge('success','Complete')}<a class="btn ghost sm" href="ApplicationForm.dc.html" style="margin-left:auto">{ic('edit',14)}Edit</a></div>
      <div class="fsec-b"><dl class="kv">
        <dt>Business name</dt><dd>Kopi &amp; Kaya Toast House Pte. Ltd.</dd>
        <dt>UEN</dt><dd class="mono">202312345K</dd>
        <dt>Entity type</dt><dd>Private limited company</dd>
        <dt>Contact person</dt><dd>Tan Wei Ling</dd>
        <dt>Contact email</dt><dd>weiling.tan@kopikaya.sg</dd>
        <dt>Contact phone</dt><dd>+65 9123 4567</dd>
      </dl></div>
    </section>
    <section class="fsec" id="operations">
      <div class="fsec-h"><h2 class="h3">Operations</h2><span class="meta">Not started</span></div>
      <div class="fsec-b fgrid">
        {field('Description of food and cuisine','', 'textarea',placeholder='e.g. Traditional kaya toast, soft-boiled eggs, kopi and teh',wide=True,help='Up to 1000 characters.')}
        {field('Seating capacity','', 'number',placeholder='0')}
        {field('Operating hours','',placeholder='e.g. Mon–Sun, 7.00am–9.00pm')}
        {field('Number of food handlers','', 'number',placeholder='0',help='Each handler must hold a valid food hygiene certificate.')}
      </div>
    </section>
  </div>
</div>'''
    body = shell('operator','My applications',content,crumbs=[('My applications','OperatorDashboard.dc.html'),('PF-2026-000231',None)],title='PF-2026-000231 · Food Establishment Licence',sub='Kopi &amp; Kaya Toast House, Clementi',actions=f'<a class="btn secondary" href="OperatorDashboard.dc.html">Save and exit</a><a class="btn primary" href="Documents.dc.html">Continue to documents {ic("arrowr",16)}</a>',notif=2)
    return page(body, 1280, 1420, 'Application form')

def documents():
    running = ver_block('running','Checking document…','Reading the file and comparing it with your Premises section. Usually takes under a minute.','<div class="vprog"><i></i></div>')
    verified = ver_block('verified','Verified','Business name and UEN match your Business details. Profile issued 3 Aug 2026.')
    issues = ver_block('issues','2 issues found','This appears to be a tenancy agreement, but some details do not match your form.',
        '<div class="stack-s" style="margin-top:10px">'+issue('high','Tenancy expiry in the document is 30 Sep 2027; your form says 30 Sep 2028.','Term: 1 Oct 2025 to 30 Sep 2027')+issue('medium','Floor area in the document (58 sqm) differs from your Premises section (55 sqm).','approximately 58 square metres')+'</div><div class="small" style="margin-top:10px;color:var(--text-2)"><b>What to do:</b> check which value is correct and update the form or replace the document. You can still submit; an officer will review this.</div>')
    unreadable = ver_block('unreadable','Could not read this document','Images cannot be read by the checker. The file is attached and will be reviewed by an officer as normal.','<div class="small" style="margin-top:8px;color:var(--text-2)"><b>Tip:</b> upload a PDF copy if you have one so it can be checked automatically.</div>')
    content = f'''
<div class="statusbar has-steps">
  {status_badge('draft',lg=True)}
  <span class="expl">4 documents required · 3 uploaded · 1 check in progress</span>
  <span class="meta num" style="margin-left:auto;white-space:nowrap">Step 5 of 6</span>
</div>
<div class="steps">{stepper(['Business','Premises','Operations','Declarations','Documents','Review'],4)}</div>
<div class="alert info" style="margin-bottom:20px">{ic('sparkle',18)}<div><b>Uploads are checked automatically.</b> The checker reads each document and compares it with your form to warn you about likely problems. It does not approve or reject anything: a licensing officer reviews every application.</div></div>
<div class="split">
  <div class="stack" style="gap:16px">
    {doc_card('ACRA_BizProfile_KopiKaya_Aug2026.pdf','Business profile (ACRA)','412 KB','today 09:02',verified,f'<a class="btn ghost sm" href="Documents.dc.html">{ic("download",14)}Download</a><a class="btn ghost sm" href="Documents.dc.html">{ic("refresh",14)}Re-run check</a><a class="btn ghost sm" href="Documents.dc.html" style="margin-left:auto">Remove</a>')}
    {doc_card('FloorPlan_Clementi_01-08_rev2.pdf','Floor plan','2.1 MB','today 09:04',running,f'<a class="btn ghost sm" href="Documents.dc.html">{ic("download",14)}Download</a><span class="meta" style="margin-left:auto">Check started 09:04:31</span>')}
    {doc_card('Tenancy_Agreement_Clementi_signed.pdf','Tenancy agreement','1.4 MB','today 09:05',issues,f'<a class="btn ghost sm" href="Documents.dc.html">{ic("download",14)}Download</a><a class="btn secondary sm" href="Documents.dc.html">{ic("upload",14)}Replace file</a>')}
    <div class="doc">
      <div class="doc-h"><span class="doc-ic">{ic('shield',18)}</span><div class="doc-t"><div class="name">Food hygiene certificate</div><div class="meta">Required · not uploaded yet</div></div>{badge('neutral','Missing')}</div>
      <div style="padding:16px">
        <div class="alert error" style="margin-bottom:12px;padding:10px 12px">{ic('x',16)}<div><b>FoodHygiene_Cert_TanWL.docx was not accepted.</b> Word documents are not supported. Save it as PDF and try again.</div></div>
        <div class="drop over" tabindex="0" role="button" aria-label="Upload food hygiene certificate">
          <div class="di">{ic('upload',20)}</div>
          <div style="font-weight:600;color:var(--primary)">Drop to upload FoodHygiene_Cert_TanWL.jpg</div>
          <div class="small muted" style="margin-top:2px">PDF, PNG, JPG or TXT · up to 10 MB</div>
        </div>
      </div>
    </div>
  </div>
  <div class="stack">
    <div class="card">
      <div class="card-h"><h2 class="h3">Required documents</h2><span class="meta num">3 / 4</span></div>
      <div class="card-b" style="padding:4px 20px">
        <div class="chk"><span class="st ok">{ic('check',11)}</span><span>Business profile (ACRA)</span><span class="meta" style="margin-left:auto">Verified</span></div>
        <div class="chk"><span class="st" style="border:1.5px solid var(--info-line)"><span class="spin" style="width:10px;height:10px;border-width:1.5px"></span></span><span>Floor plan</span><span class="meta" style="margin-left:auto">Checking…</span></div>
        <div class="chk"><span class="st warn">{ic('alert',11)}</span><span>Tenancy agreement</span><span class="meta" style="margin-left:auto">2 issues</span></div>
        <div class="chk"><span class="st todo"></span><span>Food hygiene certificate</span><span class="meta" style="margin-left:auto">Missing</span></div>
      </div>
    </div>
    <div class="card card-b" style="padding:16px 20px">
      <div class="h3" style="margin-bottom:6px">Accepted files</div>
      <p class="small muted">PDF, PNG, JPG or TXT, up to 10 MB each. PDF is recommended: it is the only format the automatic check can read. Re-uploading an identical file is detected and does not count as a change.</p>
    </div>
  </div>
</div>'''
    body = shell('operator','My applications',content,crumbs=[('My applications','OperatorDashboard.dc.html'),('PF-2026-000231','ApplicationForm.dc.html'),('Documents',None)],title='Documents',sub='PF-2026-000231 · Kopi &amp; Kaya Toast House, Clementi',actions=f'<a class="btn secondary" href="ApplicationForm.dc.html">{ic("arrowl",16)}Back to form</a><a class="btn primary" href="ReviewSubmit.dc.html">Review and submit {ic("arrowr",16)}</a>',notif=2)
    return page(body, 1280, 1400, 'Documents and verification')

def review_submit():
    content = f'''
<div class="statusbar has-steps">
  {status_badge('draft',lg=True)}
  <span class="expl">Everything required is in place. Check the details below, then submit.</span>
  <span class="meta num" style="margin-left:auto;white-space:nowrap">Step 6 of 6</span>
</div>
<div class="steps">{stepper(['Business','Premises','Operations','Declarations','Documents','Review'],5)}</div>
<div class="split">
  <div class="stack" style="gap:20px">
    <div class="alert warning">{ic('alert',18)}<div><b>1 document has unresolved check results.</b> The tenancy agreement shows 2 possible mismatches. You can still submit; the licensing officer will see the same findings and may ask you to clarify. <a href="Documents.dc.html" style="color:inherit;font-weight:600">Review documents</a></div></div>
    <section class="fsec"><div class="fsec-h"><h2 class="h3">Business details</h2>{badge('success','Complete')}<a class="btn ghost sm" href="ApplicationForm.dc.html" style="margin-left:auto">{ic('edit',14)}Edit</a></div>
      <div class="fsec-b"><dl class="kv"><dt>Business name</dt><dd>Kopi &amp; Kaya Toast House Pte. Ltd.</dd><dt>UEN</dt><dd class="mono">202312345K</dd><dt>Entity type</dt><dd>Private limited company</dd><dt>Contact</dt><dd>Tan Wei Ling · weiling.tan@kopikaya.sg · +65 9123 4567</dd></dl></div></section>
    <section class="fsec"><div class="fsec-h"><h2 class="h3">Premises</h2>{badge('success','Complete')}<a class="btn ghost sm" href="ApplicationForm.dc.html" style="margin-left:auto">{ic('edit',14)}Edit</a></div>
      <div class="fsec-b"><dl class="kv"><dt>Address</dt><dd>Blk 321 Clementi Avenue 3 #01-08, Singapore 120321</dd><dt>Premises type</dt><dd>Mall unit</dd><dt>Floor area</dt><dd>55 sqm</dd><dt>Tenancy expiry</dt><dd>30 Sep 2028</dd></dl></div></section>
    <section class="fsec"><div class="fsec-h"><h2 class="h3">Operations</h2>{badge('success','Complete')}<a class="btn ghost sm" href="ApplicationForm.dc.html" style="margin-left:auto">{ic('edit',14)}Edit</a></div>
      <div class="fsec-b"><dl class="kv"><dt>Cuisine</dt><dd>Traditional kaya toast, soft-boiled eggs, kopi and teh; light local breakfast and lunch sets.</dd><dt>Seating capacity</dt><dd>24</dd><dt>Operating hours</dt><dd>Mon–Sun, 7.00am–9.00pm</dd><dt>Food handlers</dt><dd>4</dd></dl></div></section>
    <section class="fsec"><div class="fsec-h"><h2 class="h3">Documents</h2>{badge('success','4 of 4 uploaded')}<a class="btn ghost sm" href="Documents.dc.html" style="margin-left:auto">{ic('edit',14)}Manage</a></div>
      <div class="fsec-b" style="padding:4px 20px">
        <div class="chk"><span class="st ok">{ic('check',11)}</span><span>Business profile (ACRA): ACRA_BizProfile_KopiKaya_Aug2026.pdf</span>{badge('success','Verified')}</div>
        <div class="chk"><span class="st ok">{ic('check',11)}</span><span>Floor plan: FloorPlan_Clementi_01-08_rev2.pdf</span>{badge('success','Verified')}</div>
        <div class="chk"><span class="st warn">{ic('alert',11)}</span><span>Tenancy agreement: Tenancy_Agreement_Clementi_signed.pdf</span>{badge('error','2 issues found')}</div>
        <div class="chk"><span class="st ok">{ic('check',11)}</span><span>Food hygiene certificate: FoodHygiene_Cert_TanWL.jpg</span>{badge('neutral','Could not be read')}</div>
      </div></section>
    <section class="fsec"><div class="fsec-h"><h2 class="h3">Declarations</h2></div>
      <div class="fsec-b stack" style="gap:12px">
        <label class="check"><input type="checkbox" checked><span>I confirm that the information provided is accurate and complete to the best of my knowledge.</span></label>
        <label class="check"><input type="checkbox" checked><span>I consent to an inspection of the premises by a licensing officer at a mutually arranged time.</span></label>
      </div></section>
  </div>
  <div class="stack">
    <div class="card">
      <div class="card-h"><h2 class="h3">Ready to submit</h2></div>
      <div class="card-b" style="padding-top:16px">
        <div class="row-b small" style="margin-bottom:8px"><span style="font-weight:600">Completion</span><span class="num" style="color:var(--success);font-weight:600">100%</span></div>
        <div class="progress"><i style="width:100%"></i></div>
        <p class="small muted" style="margin:14px 0 0">After you submit, your application becomes <b>Revision 1</b> and is locked for editing. If the licensing office needs changes, you will be notified and only the flagged parts will reopen.</p>
      </div>
      <div class="card-f" style="flex-direction:column;align-items:stretch"><a class="btn primary" href="Submitted.dc.html" style="height:44px">Submit application</a><a class="btn ghost" href="OperatorDashboard.dc.html">Save draft and exit</a></div>
    </div>
    <div class="card card-b" style="padding:16px 20px"><div class="h3" style="margin-bottom:6px">What happens next</div><ol class="small muted" style="margin:0;padding-left:18px;line-height:20px"><li>You receive a reference confirmation immediately.</li><li>An officer reviews the application, typically within 10 working days.</li><li>You are notified of any request for changes or a site visit.</li></ol></div>
  </div>
</div>'''
    body = shell('operator','My applications',content,crumbs=[('My applications','OperatorDashboard.dc.html'),('PF-2026-000231','ApplicationForm.dc.html'),('Review &amp; submit',None)],title='Review and submit',sub='PF-2026-000231 · Kopi &amp; Kaya Toast House, Clementi',notif=2)
    return page(body, 1280, 1400, 'Review and submit')

def submitted():
    content = f'''
<div style="max-width:720px;margin:24px auto 0" class="fade">
  <div class="card" style="text-align:center;padding:40px 40px 32px">
    <span style="width:56px;height:56px;border-radius:50%;background:var(--success-soft);color:var(--success);display:inline-flex;align-items:center;justify-content:center;margin-bottom:16px;border:1px solid var(--success-line)">{ic('check',26,2.5)}</span>
    <h1 class="h1" style="margin-bottom:6px">Application submitted</h1>
    <p class="muted">Your Food Establishment Licence application has been received by the licensing office.</p>
    <div style="display:inline-flex;align-items:center;gap:14px;margin:24px auto 0;padding:12px 20px;border:1px solid var(--line);border-radius:var(--radius-lg);background:var(--surface-2)">
      <div style="text-align:left"><div class="meta">Reference number</div><div class="mono" style="font-size:18px;font-weight:600">PF-2026-000231</div></div>
      <div class="divider" style="width:1px;height:36px"></div>
      <div style="text-align:left"><div class="meta">Status</div>{status_badge('application_received')}</div>
      <div class="divider" style="width:1px;height:36px"></div>
      <div style="text-align:left"><div class="meta">Submitted</div><div style="font-weight:600" class="num">17 Sep 2026, 09:41</div></div>
    </div>
    <div class="row" style="justify-content:center;gap:8px;margin-top:28px"><a class="btn primary" href="OperatorApplication.dc.html">View application</a><a class="btn secondary" href="OperatorDashboard.dc.html">Back to dashboard</a></div>
  </div>
  <div class="card card-b" style="margin-top:20px">
    <h2 class="h3" style="margin-bottom:12px">What happens next</h2>
    {timeline([('s','Submitted: Revision 1 recorded','A copy of everything you entered and uploaded is kept as Revision 1. It cannot be changed.','17 Sep 2026, 09:41'),('','Officer review','A licensing officer reviews your form and documents. You will be notified if changes are needed.','Typically within 10 working days'),('','Site visit','If the review is satisfactory, an officer will contact you to arrange a visit to the premises.','After review'),('','Outcome','You will be notified of the final decision here and by email.','After the site visit')])}
  </div>
  <p class="meta" style="text-align:center;margin-top:16px">A confirmation has been sent to weiling.tan@kopikaya.sg</p>
</div>'''
    body = shell('operator','My applications',content,crumbs=[('My applications','OperatorDashboard.dc.html'),('PF-2026-000231',None)],notif=2)
    return page(body, 1280, 900, 'Application submitted')

def op_application():
    fb1 = fb_item(1,'open','section','Premises','The floor area stated (48 sqm) does not match the tenancy agreement (approximately 62 sqm). Please confirm the correct floor area and amend the Premises section or the document.','<span>Raised by Licensing Officer · Round 1 · 16 Sep 2026, 15:40</span>',f'<div style="margin-top:8px"><a class="anchor" href="#premises">Go to Premises {ic("arrowr",14)}</a></div>')
    fb2 = fb_item(2,'open','document','Tenancy agreement','The tenancy expires on 31 Oct 2026, which is before the licence period. Please upload a renewed or extended tenancy agreement.','<span>Raised by Licensing Officer · Round 1 · 16 Sep 2026, 15:41</span>',f'<div style="margin-top:8px"><a class="anchor" href="#doc-tenancy">Go to Tenancy agreement {ic("arrowr",14)}</a></div>')
    fb3 = fb_item(3,'open','document','Food hygiene certificate','The uploaded image is too low in resolution to read the certificate number. Please upload a clearer scan or a PDF copy.','<span>Raised by Licensing Officer · Round 1 · 16 Sep 2026, 15:42</span>',f'<div style="margin-top:8px"><a class="anchor" href="#doc-cert">Go to Food hygiene certificate {ic("arrowr",14)}</a></div>')
    content = f'''
<div class="statusbar" style="margin-bottom:20px">
  {status_badge('pending_pre_site_resubmission',lg=True)}
  <span class="expl">The licensing office has asked for changes. Update the 3 flagged items below and resubmit. Everything else stays as you submitted it.</span>
  <span class="meta num" style="margin-left:auto;white-space:nowrap">Revision 1 · submitted 10 Sep 2026</span>
</div>
<div class="tabs"><a class="tab active" href="OperatorApplication.dc.html">Application</a><a class="tab" href="OperatorHistory.dc.html">History<span class="cnt num">1 revision</span></a></div>
<div class="split-l">
  <aside class="stack">
    <nav class="secnav" aria-label="Sections">
      <a href="#business">{ic('lock',14)}<span>Business details</span><span class="st" title="Read-only" aria-label="Read-only" style="color:var(--text-3)">{ic('lock',13)}</span></a>
      <a class="active" href="#premises">{ic('edit',14)}<span>Premises</span><span class="st warn">{ic('flag',10)}</span></a>
      <a href="#operations">{ic('lock',14)}<span>Operations</span><span class="st" title="Read-only" aria-label="Read-only" style="color:var(--text-3)">{ic('lock',13)}</span></a>
      <a href="#declarations">{ic('lock',14)}<span>Declarations</span><span class="st" title="Read-only" aria-label="Read-only" style="color:var(--text-3)">{ic('lock',13)}</span></a>
      <div class="divider" style="margin:6px 4px"></div>
      <a href="#documents">{ic('file',14)}<span>Documents</span><span class="st warn">{ic('flag',10)}</span></a>
    </nav>
    <div class="card card-b" style="padding:16px">
      <div class="row-b small" style="margin-bottom:8px"><span style="font-weight:600">Flagged items changed</span><span class="num muted">1 of 3</span></div>
      <div class="progress"><i style="width:33%"></i></div>
      <div class="meta" style="margin-top:10px;line-height:18px">Items are marked Addressed when you resubmit. Resubmit is available once at least one flagged item has changed.</div>
    </div>
  </aside>
  <div class="stack" style="gap:20px">
    <div class="fb" id="feedback">
      <div class="fb-h">{ic('msg',18)}<h2 class="h3">Feedback from the licensing office</h2><span class="tag" style="margin-left:auto">Round 1 · 3 open items</span></div>
      {fb1}{fb2}{fb3}
    </div>
    <section class="fsec flagged hl" id="premises">
      <div class="fsec-h"><h2 class="h3">Premises</h2><span class="tag editable">{ic('edit',12)} Open for changes</span><span class="meta" style="margin-left:auto">Feedback item 1</span></div>
      <div class="fsec-b">
        <div class="inline-fb" style="padding:8px 12px">{ic('msg',16)}<div><b>Feedback item 1:</b> floor area does not match the tenancy agreement. <a href="#feedback" style="color:inherit;font-weight:600">Read the full comment</a></div></div>
        <div class="fgrid">
          {field('Premises address','10 Jalan Besar #01-12',wide=True)}
          {field('Postal code','208787')}
          {field('Premises type','Shophouse','select')}
          {field('Floor area (sqm)','62','number',help='Previously 48 sqm in Revision 1.',attrs='style="border-color:var(--info)"')}
          {field('Tenancy expiry date','2027-10-31','date')}
        </div>
      </div>
      <div class="card-f"><span class="meta" style="margin-right:auto;align-self:center">{ic('check',12)} Changes saved · floor area updated from 48 to 62</span><a class="btn secondary" href="OperatorApplication.dc.html">Save section</a></div>
    </section>
    <section class="fsec locked" id="business">
      <div class="fsec-h"><h2 class="h3">Business details</h2><span class="tag readonly">{ic('lock',12)} Read-only</span><span class="meta" style="margin-left:auto">Not flagged, carried forward unchanged</span></div>
      <div class="fsec-b"><dl class="kv"><dt>Business name</dt><dd>Kopi &amp; Kaya Toast House Pte. Ltd.</dd><dt>UEN</dt><dd class="mono">202312345K</dd><dt>Entity type</dt><dd>Private limited company</dd><dt>Contact</dt><dd>Tan Wei Ling · weiling.tan@kopikaya.sg · +65 9123 4567</dd></dl></div>
    </section>
    <section class="fsec" id="documents">
      <div class="fsec-h"><h2 class="h3">Documents</h2><span class="meta">Only flagged document types can be replaced</span></div>
      <div class="fsec-b stack" style="gap:12px">
        <div class="doc" style="opacity:.85"><div class="doc-h"><span class="doc-ic">{ic('file',18)}</span><div class="doc-t"><div class="name">ACRA_BizProfile_KopiKaya_Aug2026.pdf</div><div class="meta">Business profile (ACRA) · 412 KB · Revision 1</div></div>{badge('success','Verified')}<span class="tag readonly">{ic('lock',12)} Read-only</span></div></div>
        <div class="doc" style="opacity:.85"><div class="doc-h"><span class="doc-ic">{ic('file',18)}</span><div class="doc-t"><div class="name">FloorPlan_JalanBesar_01-12_rev3.pdf</div><div class="meta">Floor plan · 2.1 MB · Revision 1</div></div>{badge('success','Verified')}<span class="tag readonly">{ic('lock',12)} Read-only</span></div></div>
        <div class="doc fsec flagged" id="doc-tenancy" style="border-radius:var(--radius-lg)">
          <div class="doc-h"><span class="doc-ic">{ic('file',18)}</span><div class="doc-t"><div class="name">Tenancy_Agreement_10JalanBesar_signed.pdf</div><div class="meta">Tenancy agreement · 1.4 MB · Revision 1</div></div>{badge('error','2 issues found')}<span class="tag editable">{ic('edit',12)} Replace requested</span></div>
          <div style="padding:0 16px 16px"><div class="inline-fb" style="margin-bottom:12px;padding:8px 12px">{ic('msg',16)}<div><b>Feedback item 2:</b> tenancy expires before the licence period. <a href="#feedback" style="color:inherit;font-weight:600">Read the full comment</a></div></div>
          <div class="drop" tabindex="0" role="button" aria-label="Replace tenancy agreement"><div class="di">{ic('upload',20)}</div><div style="font-weight:600">Drop the renewed agreement here, or <span style="color:var(--primary)">browse</span></div><div class="small muted" style="margin-top:2px">PDF, PNG, JPG or TXT · up to 10 MB · the previous file stays in Revision 1</div></div></div>
        </div>
        <div class="doc fsec flagged" id="doc-cert" style="border-radius:var(--radius-lg)">
          <div class="doc-h"><span class="doc-ic">{ic('file',18)}</span><div class="doc-t"><div class="name">FoodHygiene_Cert_TanWL_scan.pdf</div><div class="meta">Food hygiene certificate · 640 KB · uploaded today 10:12 · replaces FoodHygiene_Cert_TanWL.jpg</div></div>{badge('info','Checking…')}<span class="tag changed">Changed</span></div>
          {ver_block('running','Checking document…','Reading the certificate and comparing the holder name with your Business details.','<div class="vprog"><i></i></div>')}
        </div>
      </div>
    </section>
  </div>
</div>'''
    actions = f'<a class="btn secondary" href="OperatorHistory.dc.html">{ic("history",16)}History</a><a class="btn primary" href="OfficerQueue.dc.html">Resubmit application</a>'
    body = shell('operator','My applications',content,crumbs=[('My applications','OperatorDashboard.dc.html'),('PF-2026-000214',None)],title='PF-2026-000214 · Food Establishment Licence',sub='Kopi &amp; Kaya Toast House · 10 Jalan Besar #01-12',actions=actions,notif=2)
    return page(body, 1280, 1780, 'Operator application — respond to feedback')

def op_history():
    content = f'''
<div class="statusbar" style="margin-bottom:20px">
  {status_badge('pre_site_resubmitted',lg=True)}
  <span class="expl">Your changes were sent to the licensing office on 17 Sep 2026. You will be notified when the review continues.</span>
  <span class="meta num" style="margin-left:auto;white-space:nowrap">Revision 2 · resubmitted 17 Sep 2026</span>
</div>
<div class="tabs"><a class="tab" href="OperatorApplication.dc.html">Application</a><a class="tab active" href="OperatorHistory.dc.html">History<span class="cnt num">2 revisions</span></a></div>
<div class="split">
  <div class="stack" style="gap:20px">
    <div class="card">
      <div class="card-h"><h2 class="h3">Revisions</h2><span class="meta">Each revision is a complete, unchangeable copy of your application at the time you submitted it.</span></div>
      <div class="card-b stack-s">
        <div class="rev current"><span class="rn">Revision 2</span><span class="rmid"><span class="small num">Resubmitted 17 Sep, 10:31</span><span class="tag changed">3 items changed</span></span><span class="racts"><a class="btn ghost sm" href="OperatorHistory.dc.html">View</a><a class="btn secondary sm" href="OfficerCompare.dc.html">{ic('compare',14)}Compare with Rev 1</a></span></div>
        <div class="rev"><span class="rn">Revision 1</span><span class="rmid"><span class="small num">Submitted 10 Sep, 11:23</span></span><span class="racts"><a class="btn ghost sm" href="OperatorHistory.dc.html">View</a></span></div>
      </div>
    </div>
    <div class="fb">
      <div class="fb-h">{ic('msg',18)}<h2 class="h3">Feedback and what changed</h2><span class="tag" style="margin-left:auto">Round 1 · 3 items</span></div>
      {fb_item(1,'addressed','section','Premises','The floor area stated (48 sqm) does not match the tenancy agreement (approximately 62 sqm). Please confirm the correct floor area.','<span>Round 1 · 16 Sep 2026</span><span>You changed: floor area 48 → 62 sqm (Revision 2)</span>')}
      {fb_item(2,'addressed','document','Tenancy agreement','The tenancy expires on 31 Oct 2026, which is before the licence period. Please upload a renewed or extended tenancy agreement.','<span>Round 1 · 16 Sep 2026</span><span>You replaced: Tenancy_Agreement_10JalanBesar_renewed2027.pdf (Revision 2)</span>')}
      {fb_item(3,'addressed','document','Food hygiene certificate','The uploaded image is too low in resolution to read the certificate number. Please upload a clearer scan or a PDF copy.','<span>Round 1 · 16 Sep 2026</span><span>You replaced: FoodHygiene_Cert_TanWL_scan.pdf (Revision 2)</span>')}
    </div>
    <div class="alert neutral">{ic('info',18)}<div>“Addressed” means you changed the flagged item. The licensing officer will confirm whether it resolves the request during the next review.</div></div>
  </div>
  <div class="card">
    <div class="card-h"><h2 class="h3">Timeline</h2></div>
    <div class="card-b" style="padding-bottom:4px">{timeline([
      ('p','Resubmitted: Revision 2','Sent to the licensing office with 3 items addressed','17 Sep 2026, 10:31'),
      ('w','Changes requested','3 feedback items released to you','16 Sep 2026, 15:42'),
      ('i','Under review','A licensing officer started the review','15 Sep 2026, 09:05'),
      ('s','Submitted: Revision 1','Application received','10 Sep 2026, 11:23'),
      ('','Draft created','','8 Sep 2026, 14:12'),
    ])}</div>
  </div>
</div>'''
    body = shell('operator','My applications',content,crumbs=[('My applications','OperatorDashboard.dc.html'),('PF-2026-000214',None)],title='PF-2026-000214 · Food Establishment Licence',sub='Kopi &amp; Kaya Toast House · 10 Jalan Besar #01-12',notif=2)
    return page(body, 1280, 1160, 'Operator history')

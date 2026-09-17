from lib import *

def queue():
    def row(ref,biz,who,st,rev,fb,since,act,href,hot=False):
        meta = f'{biz} · {who}'
        sub = f'Revision {rev}' + (f' · {fb}' if fb else '')
        return f'<tr class="rowlink{" hot" if hot else ""}"><td><a class="ref" href="{href}">{ref}</a><div class="meta">{sub}</div></td><td><div style="font-weight:500">{biz}</div><div class="meta">{who}</div></td><td>{status_badge(st,"officer")}</td><td class="num small muted">{since}</td><td class="r"><a class="btn {"primary" if hot else "secondary"} sm" href="{href}">{act}</a></td></tr>'
    group = lambda t,c,extra='': f'<tr><td colspan="5" style="padding:0;border-bottom:0"><div class="qgroup">{t}<span class="cnt num">{c}</span>{extra}</div></td></tr>'
    body_rows = (
      group('Waiting for you', 2, '<span class="meta" style="margin-left:auto;font-weight:400">new submissions and resubmissions, oldest first</span>') +
      row('PF-2026-000227','Nasi Lemak Corner LLP','Siti Nurhaliza','application_received','1','','2 h ago','Start review','OfficerReview.dc.html',True) +
      row('PF-2026-000214','Kopi &amp; Kaya Toast House','Tan Wei Ling','pre_site_resubmitted','2','3 of 3 items addressed','1 h ago','Review resubmission','OfficerResubmission.dc.html',True) +
      group('In progress with you', 2) +
      row('PF-2026-000203','Kopi &amp; Kaya Toast House, Tampines','Tan Wei Ling','under_review','2','1 open item','3 d ago','Continue','OfficerReview.dc.html') +
      row('PF-2026-000219','Sakura Izakaya','Kenji Watanabe','under_review','1','','1 d ago','Continue','OfficerReview.dc.html') +
      group('Waiting on the operator', 1) +
      row('PF-2026-000188','Ah Huat Fishball Noodles','Lim Ah Huat','pending_pre_site_resubmission','1','2 open items','8 d ago','View','OfficerReview.dc.html') +
      group('After review', 2) +
      row('PF-2026-000198','Kopi &amp; Kaya Toast House, Bedok','Tan Wei Ling','site_visit_scheduled','1','','6 d ago','Mark visit done','OfficerReview.dc.html') +
      row('PF-2026-000176','Chettinad Spice Kitchen','Arun Muthu','pending_approval','3','','9 d ago','Decide','OfficerReview.dc.html')
    )
    notif = f"""<div class="notif fade" role="dialog" aria-label="Notifications" style="position:static;width:100%;box-shadow:none;border:0">
  <div class="card-h" style="padding:12px 16px"><span class="h3">Notifications</span><a class="small" href="OfficerQueue.dc.html">Mark all as read</a></div>
  <a class="ni unread" href="OfficerResubmission.dc.html" style="color:inherit;text-decoration:none"><span class="nd"></span><div style="flex:1"><div class="nt">PF-2026-000214 resubmitted</div><div class="nb">Tan Wei Ling addressed 3 of 3 feedback items · Revision 2</div><div class="meta" style="margin-top:2px">17 Sep, 10:31</div></div>{ic('chev',16)}</a>
  <a class="ni unread" href="OfficerReview.dc.html" style="color:inherit;text-decoration:none"><span class="nd"></span><div style="flex:1"><div class="nt">New application PF-2026-000227</div><div class="nb">Nasi Lemak Corner LLP · Food Establishment Licence</div><div class="meta" style="margin-top:2px">17 Sep, 09:58</div></div>{ic('chev',16)}</a>
  <a class="ni unread" href="OfficerReview.dc.html" style="color:inherit;text-decoration:none"><span class="nd"></span><div style="flex:1"><div class="nt">New application PF-2026-000219</div><div class="nb">Sakura Izakaya · Food Establishment Licence</div><div class="meta" style="margin-top:2px">16 Sep, 14:20</div></div>{ic('chev',16)}</a>
  <a class="ni" href="OfficerReview.dc.html" style="color:inherit;text-decoration:none"><span class="nd" style="background:transparent"></span><div style="flex:1"><div class="nt" style="font-weight:500">PF-2026-000188 resubmission requested</div><div class="nb">Feedback released to the operator · 2 items</div><div class="meta" style="margin-top:2px">9 Sep, 16:45</div></div>{ic('chev',16)}</a>
  <a class="small" href="OfficerQueue.dc.html" style="display:block;padding:12px 16px;font-weight:600;border-top:1px solid var(--line);background:var(--surface-2)">See all notifications</a>
</div>"""
    queue.notif = notif
    content = f"""
<div class="card">
  <div class="card-h" style="gap:12px">
    <div class="row" style="gap:4px"><a class="tab active" href="OfficerQueue.dc.html" style="padding:6px 10px">Open<span class="cnt num">7</span></a><a class="tab" href="OfficerQueue.dc.html" style="padding:6px 10px">Closed<span class="cnt num">16</span></a></div>
    <div class="row" style="gap:8px;margin-left:auto"><div style="position:relative"><span style="position:absolute;left:10px;top:11px;color:var(--text-3)">{ic('search',16)}</span><input class="input" style="width:220px;height:36px;padding-left:34px" placeholder="Search"></div><select class="input select" style="width:170px;height:36px"><option>All statuses</option></select></div>
  </div>
  <table class="table"><colgroup><col style="width:210px"><col><col style="width:240px"><col style="width:100px"><col style="width:180px"></colgroup>
    <thead><tr><th>Application</th><th>Business</th><th>Status</th><th>Updated</th><th></th></tr></thead>
    <tbody>{body_rows}</tbody>
  </table>
</div>
<p class="meta" style="margin-top:12px">Groups follow the workflow: cases waiting for you come first. Status labels are the internal ones; operators see their own wording.</p>"""
    body = shell('officer','Review queue',content,title='Review queue',sub='2 applications are waiting for you: 1 new, 1 resubmitted.',notif=3)
    return page(body, 1280, 1120, 'Officer review queue')

def _officer_doc(name, dtype, size, ver, footer=''):
    return doc_card(name,dtype,size,'10 Sep 2026',ver,footer,upl=False)

def review():
    v_profile = ver_block('verified','Verified','Business name “Kopi &amp; Kaya Toast House Pte. Ltd.” and UEN 202312345K match the Business section. Profile dated 3 Aug 2026.',confidence=0.92)+'<div class="aiband">'+ic('sparkle',13)+'Automated check · advisory only</div>'
    v_plan = ver_block('verified','Verified','Floor plan shows a kitchen and preparation area; unit #01-12 matches the Premises section.',confidence=0.78)+'<div class="aiband">'+ic('sparkle',13)+'Automated check · advisory only</div>'
    v_ten = ver_block('issues','2 issues found','Document appears to be a tenancy agreement; two details contradict the form.','<div class="stack-s" style="margin-top:10px">'+issue('high','Tenancy expiry in document is 31 Oct 2026; form states 31 Oct 2027.','Term: 1 Nov 2024 to 31 Oct 2026')+issue('medium','Floor area in document (62 sqm) differs from form (48 sqm).','approximately 62 square metres')+'</div>',confidence=0.81)+'<div class="aiband">'+ic('sparkle',13)+'Automated check · advisory only</div>'
    v_cert = ver_block('unreadable','Could not read','JPEG image; no text could be extracted. Manual review required.')+'<div class="aiband">'+ic('sparkle',13)+'No model call made · image not supported for extraction</div>'
    composer = f'''<div class="card" id="composer">
  <div class="card-h" style="flex-direction:column;align-items:flex-start;gap:2px"><h2 class="h3">Add feedback</h2><span class="meta">Visible to the operator only after you request resubmission</span></div>
  <div class="card-b stack" style="gap:14px">
    {field('Applies to','','select',placeholder='Choose a section or document',help='The section or document type the comment is about.')}
    {field('Template','','select',required=False,placeholder='No template',help='Optional. Fills the comment; you can edit it.')}
    {field('Comment to the operator','','textarea',placeholder='What is wrong, and what should the applicant provide?',help='Write for the applicant. They see this only after you request resubmission.')}
  </div>
  <div class="card-f"><a class="btn ghost" href="OfficerReview.dc.html">Cancel</a><a class="btn primary" href="OfficerReview.dc.html">{ic('plus',14)}Add feedback item</a></div>
</div>'''
    fbpanel = f'''<div class="fb">
  <div class="fb-h">{ic('msg',18)}<h2 class="h3">Feedback, this round</h2><span class="tag" style="margin-left:auto">3 open · not yet released</span></div>
  {fb_item(1,'open','section','Premises','The floor area stated (48 sqm) does not match the tenancy agreement (approximately 62 sqm). Please confirm the correct floor area and amend the Premises section or the document.','<span>You · 16 Sep 2026, 15:40 · template: Floor area mismatch</span>','<div class="row" style="gap:6px;margin-top:8px"><a class="btn ghost sm" href="OfficerReview.dc.html">'+ic('edit',13)+'Edit</a><a class="btn ghost sm" href="OfficerReview.dc.html">Withdraw</a></div>')}
  {fb_item(2,'open','document','Tenancy agreement','The tenancy expires on 31 Oct 2026, which is before the licence period. Please upload a renewed or extended tenancy agreement.','<span>You · 16 Sep 2026, 15:41 · template: Document expired</span>','<div class="row" style="gap:6px;margin-top:8px"><a class="btn ghost sm" href="OfficerReview.dc.html">'+ic('edit',13)+'Edit</a><a class="btn ghost sm" href="OfficerReview.dc.html">Withdraw</a></div>')}
  {fb_item(3,'open','document','Food hygiene certificate','The uploaded image is too low in resolution to read the certificate number. Please upload a clearer scan or a PDF copy.','<span>You · 16 Sep 2026, 15:42 · template: Illegible document</span>','<div class="row" style="gap:6px;margin-top:8px"><a class="btn ghost sm" href="OfficerReview.dc.html">'+ic('edit',13)+'Edit</a><a class="btn ghost sm" href="OfficerReview.dc.html">Withdraw</a></div>')}
</div>'''
    dialog = f'''<div class="dialog-bg" style="position:static;padding:40px;height:100%"><div class="dialog fade" role="dialog" aria-modal="true" aria-labelledby="dlg-t">
  <div class="dialog-h"><h2 class="h2" id="dlg-t">Request resubmission?</h2></div>
  <div class="dialog-b stack" style="gap:12px">
    <p>The application moves to <b>Pending Pre-Site Resubmission</b>. The operator is notified and sees the <b>3 feedback items</b> below. Only the flagged section and document types will be editable for them.</p>
    <ul class="small" style="margin:0;padding-left:18px;line-height:20px"><li>Section: Premises</li><li>Document: Tenancy agreement</li><li>Document: Food hygiene certificate</li></ul>
    <div class="field"><label class="label">Note to operator <span class="muted3" style="font-weight:400">(optional)</span></label><textarea class="input" style="min-height:72px">Please respond within 14 days so that we can proceed to schedule the site visit.</textarea></div>
    <p class="meta">Feedback cannot be added or withdrawn while the operator is responding.</p>
  </div>
  <div class="dialog-f"><a class="btn ghost" href="OfficerReview.dc.html">Cancel</a><a class="btn primary" href="OperatorApplication.dc.html">Request resubmission</a></div>
</div></div>'''
    review.dialog = dialog
    content = f'''
<div class="statusbar" style="margin-bottom:16px">
  {status_badge('under_review','officer',lg=True)}
  <span class="expl">Review started by you on 15 Sep. Operator sees: <b>Under Review</b>.</span>
  <span class="meta num" style="margin-left:auto;white-space:nowrap">Revision 1 · submitted 10 Sep 2026</span><a class="btn secondary sm disabled" href="OfficerCompare.dc.html" title="Available from the second revision">{ic('compare',14)}Compare</a>
</div>
<div class="tabs"><a class="tab active" href="OfficerReview.dc.html">Submission</a><a class="tab" href="OfficerReview.dc.html">Documents<span class="cnt num">4</span></a><a class="tab" href="OfficerReview.dc.html">Feedback<span class="cnt num">3</span></a><a class="tab" href="OfficerHistory.dc.html">History &amp; audit</a></div>
<div class="split" style="grid-template-columns:minmax(0,1fr) 400px">
  <div class="stack" style="gap:20px">
    <div class="facts"><div><span class="fk">Applicant</span><span class="fv">Tan Wei Ling</span><span class="meta">weiling.tan@kopikaya.sg</span></div><div><span class="fk">Submitted</span><span class="fv num">10 Sep 2026, 11:23</span><span class="meta">Revision 1</span></div><div><span class="fk">Licence</span><span class="fv">Food Establishment</span><span class="meta">4 sections · 4 documents</span></div></div>
    <section class="fsec"><div class="fsec-h"><h2 class="h3">Business details</h2><a class="btn ghost sm" href="#composer" style="margin-left:auto">{ic('msg',14)}Comment on section</a></div>
      <div class="fsec-b"><dl class="kv"><dt>Business name</dt><dd>Kopi &amp; Kaya Toast House Pte. Ltd.</dd><dt>UEN</dt><dd class="mono">202312345K</dd><dt>Entity type</dt><dd>Private limited company</dd><dt>Contact</dt><dd>Tan Wei Ling · +65 9123 4567</dd></dl></div></section>
    <section class="fsec flagged"><div class="fsec-h"><h2 class="h3">Premises</h2><span class="tag editable">{ic('flag',12)} 1 feedback item</span><a class="btn ghost sm" href="#composer" style="margin-left:auto">{ic('msg',14)}Comment on section</a></div>
      <div class="fsec-b"><dl class="kv"><dt>Address</dt><dd>10 Jalan Besar #01-12, Singapore 208787</dd><dt>Premises type</dt><dd>Shophouse</dd><dt>Floor area</dt><dd>48 sqm <span class="tag" style="margin-left:6px;background:var(--error-soft);color:var(--error);border-color:var(--error-line)">Document says 62 sqm</span></dd><dt>Tenancy expiry</dt><dd>31 Oct 2027 <span class="tag" style="margin-left:6px;background:var(--error-soft);color:var(--error);border-color:var(--error-line)">Document says 31 Oct 2026</span></dd></dl></div></section>
    <section class="fsec"><div class="fsec-h"><h2 class="h3">Operations</h2><a class="btn ghost sm" href="#composer" style="margin-left:auto">{ic('msg',14)}Comment on section</a></div>
      <div class="fsec-b"><dl class="kv"><dt>Cuisine</dt><dd>Traditional kaya toast, soft-boiled eggs, kopi and teh; light local breakfast and lunch sets.</dd><dt>Seating capacity</dt><dd>24</dd><dt>Operating hours</dt><dd>Mon–Sun, 7.00am–9.00pm</dd><dt>Food handlers</dt><dd>4</dd></dl></div></section>
    <section class="fsec"><div class="fsec-h"><h2 class="h3">Documents</h2><span class="meta">Automated checks are advisory; verify against the file.</span></div>
      <div class="fsec-b stack" style="gap:12px">
        {_officer_doc('ACRA_BizProfile_KopiKaya_Aug2026.pdf','Business profile (ACRA)','412 KB',v_profile,f'<a class="btn ghost sm" href="OfficerReview.dc.html">{ic("download",14)}Download</a><a class="btn ghost sm" href="OfficerReview.dc.html">{ic("refresh",14)}Re-run check</a><a class="btn ghost sm" href="#composer" style="margin-left:auto">{ic("msg",14)}Comment</a>')}
        {_officer_doc('FloorPlan_JalanBesar_01-12_rev3.pdf','Floor plan','2.1 MB',v_plan,f'<a class="btn ghost sm" href="OfficerReview.dc.html">{ic("download",14)}Download</a><a class="btn ghost sm" href="OfficerReview.dc.html">{ic("refresh",14)}Re-run check</a><a class="btn ghost sm" href="#composer" style="margin-left:auto">{ic("msg",14)}Comment</a>')}
        <div class="fsec flagged" style="border-radius:var(--radius-lg)">{_officer_doc('Tenancy_Agreement_10JalanBesar_signed.pdf','Tenancy agreement','1.4 MB',v_ten,f'<a class="btn ghost sm" href="OfficerReview.dc.html">{ic("download",14)}Download</a><a class="btn ghost sm" href="OfficerReview.dc.html">{ic("refresh",14)}Re-run check</a><span class="tag editable" style="margin-left:auto">{ic("flag",12)} 1 feedback item</span>')}</div>
        <div class="fsec flagged" style="border-radius:var(--radius-lg)">{doc_card('FoodHygiene_Cert_TanWL.jpg','Food hygiene certificate','1.9 MB','10 Sep 2026',v_cert,f'<a class="btn ghost sm" href="OfficerReview.dc.html">{ic("download",14)}Download</a><span class="tag editable" style="margin-left:auto">{ic("flag",12)} 1 feedback item</span>',icon='image',upl=False)}</div>
      </div></section>
  </div>
  <div class="stack" style="gap:20px">
    {fbpanel}
    {composer}
  </div>
</div>'''
    body = shell('officer','Review queue',content,crumbs=[('Review queue','OfficerQueue.dc.html'),('PF-2026-000214',None)],title='PF-2026-000214 · Kopi &amp; Kaya Toast House',sub='Kopi &amp; Kaya Toast House Pte. Ltd. · Food Establishment Licence · 10 Jalan Besar #01-12, Singapore 208787',actions=f'<a class="btn secondary disabled" href="OfficerReview.dc.html" title="Resolve or withdraw open feedback first">Schedule site visit</a><a class="btn primary" href="OfficerReview.dc.html">Request resubmission (3)</a><button class="iconbtn" aria-label="More actions: Reject, Download all" style="border-color:var(--line-strong)">{ic("dots",18)}</button>',notif=3)
    return page(body, 1280, 2020, 'Officer review workspace')

def resubmission():
    v_ten = ver_block('verified','Verified','Renewed tenancy agreement; term 1 Nov 2026 to 31 Oct 2027 matches the Premises section. Floor area 62 sqm matches.',confidence=0.88)+'<div class="aiband">'+ic('sparkle',13)+'Automated check · advisory only</div>'
    v_cert = ver_block('review','Needs officer review','Certificate holder “Tan Wei Ling” matches the contact person. Confidence below the threshold because the certificate number is partially obscured.','<div class="stack-s" style="margin-top:10px">'+issue('low','Certificate number only partially legible.','Cert. No. FH-2024-08▮▮▮')+'</div>',confidence=0.52)+'<div class="aiband">'+ic('sparkle',13)+'Automated check · advisory only</div>'
    fbpanel = f'''<div class="fb">
  <div class="fb-h">{ic('msg',18)}<h2 class="h3">Feedback, round 1</h2><span class="tag" style="margin-left:auto">3 addressed · 0 open</span></div>
  {fb_item(1,'addressed','section','Premises','The floor area stated (48 sqm) does not match the tenancy agreement (approximately 62 sqm). Please confirm the correct floor area.','<span>Rahim bin Abdullah · 16 Sep 2026</span><span style="color:var(--info);font-weight:600">Changed: floor area 48 → 62</span>','<div class="row" style="gap:6px;margin-top:8px"><a class="btn secondary sm" href="OfficerResubmission.dc.html">'+ic('check',13)+'Mark resolved</a><a class="btn ghost sm" href="OfficerCompare.dc.html">View change</a></div>')}
  {fb_item(2,'addressed','document','Tenancy agreement','The tenancy expires on 31 Oct 2026, which is before the licence period. Please upload a renewed or extended tenancy agreement.','<span>Rahim bin Abdullah · 16 Sep 2026</span><span style="color:var(--info);font-weight:600">Replaced with a renewed agreement</span>','<div class="row" style="gap:6px;margin-top:8px"><a class="btn secondary sm" href="OfficerResubmission.dc.html">'+ic('check',13)+'Mark resolved</a><a class="btn ghost sm" href="OfficerCompare.dc.html">View change</a></div>')}
  {fb_item(3,'resolved','document','Food hygiene certificate','The uploaded image is too low in resolution to read the certificate number. Please upload a clearer scan or a PDF copy.','<span>Rahim bin Abdullah · 16 Sep 2026</span><span style="color:var(--success);font-weight:600">Resolved by you · 17 Sep 2026, 11:02</span>')}
</div>'''
    toast = f'<div style="position:absolute;right:24px;top:100px;z-index:6" class="fade"><div class="toast"><span class="ti">{ic("check",18)}</span><div><div class="tt">Feedback item 3 marked resolved</div><div class="tb">Recorded in the audit trail · Undo</div></div></div></div>'
    content = f'''
<div class="statusbar" style="margin-bottom:16px">
  {status_badge('under_review','officer',lg=True)}
  <span class="expl">Revision 2 received 17 Sep, 10:31 · 3 changes · review restarted by you at 10:58. Operator sees: <b>Under Review</b>.</span>
  <span class="meta num" style="margin-left:auto;white-space:nowrap">Revision 2 of 2</span><a class="btn secondary sm" href="OfficerCompare.dc.html">{ic('compare',14)}Compare Rev 1 → 2</a>
</div>
<div class="tabs"><a class="tab active" href="OfficerResubmission.dc.html">Submission</a><a class="tab" href="OfficerResubmission.dc.html">Documents<span class="cnt num">4</span></a><a class="tab" href="OfficerResubmission.dc.html">Feedback<span class="cnt num">3</span></a><a class="tab" href="OfficerHistory.dc.html">History &amp; audit</a></div>
<div class="split" style="grid-template-columns:minmax(0,1fr) 400px">
  <div class="stack" style="gap:16px">
    <div class="rev current"><span class="rn">Revision 2</span><span class="rmid"><span class="small num">Resubmitted 17 Sep, 10:31 by Tan Wei Ling</span><span class="tag changed">1 section · 2 documents changed</span></span><span class="racts"><a class="btn ghost sm" href="OfficerHistory.dc.html">All revisions</a></span></div>
    <section class="fsec" style="border-color:var(--info-line)"><div class="fsec-h"><h2 class="h3">Premises</h2><span class="tag changed">Changed</span><span class="meta">1 field</span><a class="btn ghost sm" href="OfficerCompare.dc.html" style="margin-left:auto">{ic('compare',14)}Compare</a></div>
      <div class="fsec-b"><dl class="kv"><dt>Address</dt><dd class="muted3" style="font-weight:400">10 Jalan Besar #01-12, Singapore 208787</dd><dt>Premises type</dt><dd class="muted3" style="font-weight:400">Shophouse</dd><dt>Floor area</dt><dd><span style="background:var(--success-soft);padding:1px 6px;border-radius:4px">62 sqm</span> <span class="meta" style="text-decoration:line-through;margin-left:6px">48 sqm</span></dd><dt>Tenancy expiry</dt><dd class="muted3" style="font-weight:400">31 Oct 2027</dd></dl></div></section>
    <section class="fsec" style="border-color:var(--info-line)"><div class="fsec-h"><h2 class="h3">Documents</h2><span class="tag changed">2 replaced</span></div>
      <div class="fsec-b stack" style="gap:12px">
        <div class="doc" style="border-color:var(--info-line)"><div class="doc-h"><span class="doc-ic">{ic('file',18)}</span><div class="doc-t"><div class="name">Tenancy_Agreement_10JalanBesar_renewed2027.pdf</div><div class="meta">Tenancy agreement · 1.5 MB · uploaded 17 Sep 2026 · replaces Tenancy_Agreement_10JalanBesar_signed.pdf</div></div><span class="tag changed">Replaced</span></div>{v_ten}<div class="doc-f"><a class="btn ghost sm" href="OfficerResubmission.dc.html">{ic('download',14)}Download</a><a class="btn ghost sm" href="OfficerResubmission.dc.html">Previous file</a></div></div>
        <div class="doc" style="border-color:var(--info-line)"><div class="doc-h"><span class="doc-ic">{ic('file',18)}</span><div class="doc-t"><div class="name">FoodHygiene_Cert_TanWL_scan.pdf</div><div class="meta">Food hygiene certificate · 640 KB · uploaded 17 Sep 2026 · replaces FoodHygiene_Cert_TanWL.jpg</div></div><span class="tag changed">Replaced</span></div>{v_cert}<div class="doc-f"><a class="btn ghost sm" href="OfficerResubmission.dc.html">{ic('download',14)}Download</a><a class="btn ghost sm" href="OfficerResubmission.dc.html">Previous file</a><a class="btn ghost sm" href="OfficerResubmission.dc.html">{ic('refresh',14)}Re-run check</a></div></div>
        <div class="row small muted" style="padding:4px 2px">{ic('lock',14)}<span>Business profile and Floor plan are unchanged from Revision 1.</span><a class="small" href="OfficerResubmission.dc.html" style="margin-left:auto">Show unchanged</a></div>
      </div></section>
    <details class="fsec"><summary class="fsec-h" style="cursor:pointer;list-style:none"><h2 class="h3">Business details</h2><span class="tag">Unchanged</span><span class="meta" style="margin-left:auto">{ic('chevd',16)}</span></summary></details>
    <details class="fsec"><summary class="fsec-h" style="cursor:pointer;list-style:none"><h2 class="h3">Operations</h2><span class="tag">Unchanged</span><span class="meta" style="margin-left:auto">{ic('chevd',16)}</span></summary></details>
    <details class="fsec"><summary class="fsec-h" style="cursor:pointer;list-style:none"><h2 class="h3">Declarations</h2><span class="tag">Unchanged</span><span class="meta" style="margin-left:auto">{ic('chevd',16)}</span></summary></details>
  </div>
  <div class="stack" style="gap:20px">
    {fbpanel}
    <div class="alert warning">{ic('alert',18)}<div><b>2 addressed items are not yet resolved.</b> Unchanged sections are collapsed below. You can schedule the site visit now (no items are open), but confirm each change first so the record is complete.</div></div>
  </div>
</div>'''
    body = shell('officer','Review queue',content,crumbs=[('Review queue','OfficerQueue.dc.html'),('PF-2026-000214',None)],title='PF-2026-000214 · Kopi &amp; Kaya Toast House',sub='Kopi &amp; Kaya Toast House Pte. Ltd. · Food Establishment Licence · 10 Jalan Besar #01-12, Singapore 208787',actions=f'<a class="btn secondary disabled" href="OfficerResubmission.dc.html" title="Needs at least one open feedback item">Request resubmission</a><a class="btn primary" href="OfficerResubmission.dc.html">Schedule site visit</a><button class="iconbtn" aria-label="More actions: Reject, Download all" style="border-color:var(--line-strong)">{ic("dots",18)}</button>',notif=3,overlay=toast)
    return page(body, 1280, 1500, 'Officer resubmission review')

def compare():
    def r(k,old,new,chg=False,mark='chg'):
        if chg: return f'<div class="diff-r chg"><div class="k">{k}</div><div class="old">{old}</div><div class="new"><span class="cm {mark}">{ {"chg":"Changed","add":"Added","rep":"Replaced"}[mark] }</span>{new}</div></div>'
        return f'<div class="diff-r same"><div class="k">{k}</div><div>{old}</div><div>{new}</div></div>'
    content = f'''
<div class="statusbar" style="margin-bottom:16px">
  {status_badge('under_review','officer',lg=True)}
  <div class="row" style="gap:10px;margin-left:16px"><span class="small muted">Comparing</span><select class="input select" style="width:180px;height:36px"><option>Revision 1 · 10 Sep</option></select><span class="muted3">{ic('arrowr',16)}</span><select class="input select" style="width:180px;height:36px"><option>Revision 2 · 17 Sep (current)</option></select></div>
  <label class="check small" style="margin-left:auto"><input type="checkbox" checked><span>Show unchanged fields</span></label>
  <a class="btn secondary" href="OfficerResubmission.dc.html">{ic('arrowl',16)}Back to review</a>
</div>
<div class="row" style="gap:24px;margin-bottom:16px;padding:0 2px"><span class="eyebrow">Summary of changes</span><span class="small"><b class="num">1</b> section changed · Premises</span><span class="small"><b class="num">2</b> documents replaced</span><span class="small"><b class="num">3 / 3</b> feedback items addressed</span></div>
<div class="stack" style="gap:16px">
  <div class="diff">
    <div class="card-h" style="padding:12px 16px"><h2 class="h3">Premises</h2><span class="tag changed">1 of 5 fields changed</span><span class="tag editable" style="margin-left:auto">{ic('flag',12)} Feedback 1 · Addressed</span></div>
    <div class="diff-h"><div>Field</div><div>Revision 1</div><div>Revision 2 (current)</div></div>
    {r('Premises address','10 Jalan Besar #01-12','10 Jalan Besar #01-12')}
    {r('Postal code','208787','208787')}
    {r('Premises type','Shophouse','Shophouse')}
    {r('Floor area (sqm)','48','62',True)}
    {r('Tenancy expiry','31 Oct 2027','31 Oct 2027')}
  </div>
  <div class="diff">
    <div class="card-h" style="padding:12px 16px"><h2 class="h3">Documents</h2><span class="tag changed">2 of 4 replaced</span></div>
    <div class="diff-h"><div>Document type</div><div>Revision 1</div><div>Revision 2 (current)</div></div>
    {r('Business profile (ACRA)','ACRA_BizProfile_KopiKaya_Aug2026.pdf','ACRA_BizProfile_KopiKaya_Aug2026.pdf')}
    {r('Floor plan','FloorPlan_JalanBesar_01-12_rev3.pdf','FloorPlan_JalanBesar_01-12_rev3.pdf')}
    {r('Tenancy agreement','Tenancy_Agreement_10JalanBesar_signed.pdf<div class=meta>Expiry 31 Oct 2026 · 2 issues</div>','Tenancy_Agreement_10JalanBesar_renewed2027.pdf<div class=meta style="font-weight:400">Expiry 31 Oct 2027 · Verified</div>',True,'rep')}
    {r('Food hygiene certificate','FoodHygiene_Cert_TanWL.jpg<div class=meta>Could not be read</div>','FoodHygiene_Cert_TanWL_scan.pdf<div class=meta style="font-weight:400">Needs officer review</div>',True,'rep')}
  </div>
  <div class="diff">
    <div class="card-h" style="padding:12px 16px"><h2 class="h3">Business details</h2><span class="tag">Unchanged</span></div>
    <div class="diff-h"><div>Field</div><div>Revision 1</div><div>Revision 2 (current)</div></div>
    {r('Business name','Kopi &amp; Kaya Toast House Pte. Ltd.','Kopi &amp; Kaya Toast House Pte. Ltd.')}
    {r('UEN','202312345K','202312345K')}
    {r('Entity type','Private limited company','Private limited company')}
  </div>
  <div class="row small muted" style="padding:0 2px">{ic('lock',14)}<span>Operations and Declarations are unchanged (hidden). Revisions are immutable; this comparison is computed from the two stored snapshots.</span></div>
</div>'''
    body = shell('officer','Review queue',content,crumbs=[('Review queue','OfficerQueue.dc.html'),('PF-2026-000214','OfficerResubmission.dc.html'),('Compare revisions',None)],title='Compare revisions',sub='PF-2026-000214 · Kopi &amp; Kaya Toast House Pte. Ltd.',notif=3)
    return page(body, 1280, 1180, 'Compare revisions')

def audit():
    ev = [
     ('feedback.resolved','Feedback item 3 marked resolved','Rahim bin Abdullah (officer)','17 Sep 2026, 11:02','Food hygiene certificate · resolved in Revision 2'),
     ('status.changed','Status: Pre-Site Resubmitted → Under Review','Rahim bin Abdullah (officer)','17 Sep, 10:58','Start review'),
     ('verification.completed','Verification completed: needs review','System','17 Sep 2026, 10:32','FoodHygiene_Cert_TanWL_scan.pdf · confidence 0.52'),
     ('verification.completed','Verification completed: verified','System','17 Sep 2026, 10:31','Tenancy_Agreement_10JalanBesar_renewed2027.pdf · confidence 0.88'),
     ('feedback.addressed','Feedback items 1, 2, 3 marked addressed','System','17 Sep 2026, 10:31','Targets changed in Revision 2'),
     ('status.changed','Status: Pending Pre-Site Resubmission → Pre-Site Resubmitted','Tan Wei Ling (operator)','17 Sep 2026, 10:31','Resubmit'),
     ('revision.submitted','Revision 2 submitted','Tan Wei Ling (operator)','17 Sep 2026, 10:31','1 section changed · 2 documents replaced'),
     ('document.replaced','Document replaced: Food hygiene certificate','Tan Wei Ling (operator)','17 Sep 2026, 10:12','FoodHygiene_Cert_TanWL_scan.pdf (sha256 9f3c…e21a)'),
     ('document.replaced','Document replaced: Tenancy agreement','Tan Wei Ling (operator)','17 Sep 2026, 10:09','Tenancy_Agreement_10JalanBesar_renewed2027.pdf (sha256 41bb…07d4)'),
     ('feedback.released','Feedback released to operator (3 items)','System','16 Sep 2026, 15:42','Round 1'),
     ('status.changed','Status: Under Review → Pending Pre-Site Resubmission','Rahim bin Abdullah (officer)','16 Sep 2026, 15:42','Note: “Please respond within 14 days…”'),
     ('feedback.created','Feedback item 3 created: Document: Food hygiene certificate','Rahim bin Abdullah (officer)','16 Sep 2026, 15:42','Template: Illegible document'),
     ('feedback.created','Feedback item 2 created: Document: Tenancy agreement','Rahim bin Abdullah (officer)','16 Sep 2026, 15:41','Template: Document expired'),
     ('feedback.created','Feedback item 1 created: Section: Premises','Rahim bin Abdullah (officer)','16 Sep 2026, 15:40','Template: Floor area mismatch'),
     ('status.changed','Status: Application Received → Under Review','Rahim bin Abdullah (officer)','15 Sep, 09:05','Start review'),
     ('verification.completed','Verification completed: 2 issues found','System','10 Sep 2026, 11:24','Tenancy_Agreement_10JalanBesar_signed.pdf · confidence 0.81'),
     ('status.changed','Status: Draft → Application Received','Tan Wei Ling (operator)','10 Sep 2026, 11:23','Submit'),
     ('revision.submitted','Revision 1 submitted','Tan Wei Ling (operator)','10 Sep 2026, 11:23','4 sections · 4 documents'),
     ('application.created','Application created','Tan Wei Ling (operator)','8 Sep 2026, 14:12','Food Establishment Licence'),
    ]
    trs=''
    for t,title,actor,when,detail in ev:
        kind = 'p' if t.startswith('status') else 's' if t.startswith('revision') else 'w' if t.startswith('feedback') else 'i' if t.startswith('verification') else ''
        actor_s = actor.replace(' (officer)','').replace(' (operator)','')
        trs += f'<tr><td class="num small" style="white-space:nowrap;color:var(--text-2)">{when.replace(" 2026","")}</td><td><div style="font-weight:600;font-size:14px">{title}</div><div class="meta">{detail} · <span class="mono" style="font-size:11px">{t}</span></div></td><td class="small">{actor_s}</td></tr>'
    content = f'''
<div class="statusbar" style="margin-bottom:16px">{status_badge('under_review','officer',lg=True)}<span class="expl">Every submission, status change, feedback action, document upload and verification outcome is recorded and cannot be edited or deleted.</span></div>
<div class="tabs"><a class="tab" href="OfficerResubmission.dc.html">Submission</a><a class="tab" href="OfficerResubmission.dc.html">Documents<span class="cnt num">4</span></a><a class="tab" href="OfficerResubmission.dc.html">Feedback<span class="cnt num">3</span></a><a class="tab active" href="OfficerHistory.dc.html">History &amp; audit</a></div>
<div class="split" style="grid-template-columns:minmax(0,1fr) 340px">
  <div class="card">
    <div class="card-h"><h2 class="h3">Audit trail</h2><div class="row" style="gap:8px"><select class="input select" style="width:180px;height:34px"><option>All event types</option></select><a class="btn ghost sm" href="OfficerHistory.dc.html">{ic('download',14)}Export CSV</a></div></div>
    <table class="table"><colgroup><col style="width:130px"><col><col style="width:150px"></colgroup><thead><tr><th>When</th><th>Event</th><th>Actor</th></tr></thead><tbody>{trs}</tbody></table>
  </div>
  <div class="stack">
    <div class="card"><div class="card-h"><h2 class="h3">Revisions</h2></div><div class="card-b stack-s">
      <div class="rev current"><span class="rn">Revision 2</span><span class="rmid"><span class="small num">17 Sep, 10:31</span></span><span class="racts"><a class="btn ghost sm" href="OfficerCompare.dc.html">{ic('compare',14)}Compare</a></span></div>
      <div class="rev"><span class="rn">Revision 1</span><span class="rmid"><span class="small num">10 Sep, 11:23</span></span><span class="racts"><a class="btn ghost sm" href="OfficerHistory.dc.html">View</a></span></div>
    </div></div>
    <div class="card"><div class="card-h"><h2 class="h3">Status history</h2></div><div class="card-b" style="padding-bottom:4px">{timeline([
      ('p','Under Review','Started by Rahim bin Abdullah','17 Sep 2026, 10:58'),
      ('i','Pre-Site Resubmitted','Revision 2 by Tan Wei Ling','17 Sep 2026, 10:31'),
      ('w','Pending Pre-Site Resubmission','3 items released · operator notified','16 Sep 2026, 15:42'),
      ('p','Under Review','Started by Rahim bin Abdullah','15 Sep 2026, 09:05'),
      ('s','Application Received','Revision 1 by Tan Wei Ling','10 Sep 2026, 11:23'),
    ])}</div></div>
  </div>
</div>'''
    body = shell('officer','Review queue',content,crumbs=[('Review queue','OfficerQueue.dc.html'),('PF-2026-000214','OfficerResubmission.dc.html'),('History &amp; audit',None)],title='PF-2026-000214 · Kopi &amp; Kaya Toast House',sub='Kopi &amp; Kaya Toast House Pte. Ltd. · Food Establishment Licence · 10 Jalan Besar #01-12, Singapore 208787',notif=3)
    return page(body, 1280, 1640, 'Officer history and audit trail')

def dialog_request():
    review()
    return page(review.dialog, 640, 560, 'Dialog — request resubmission')

def notifications_panel():
    queue()
    return page(f'<div style="height:100%;background:#fff">{queue.notif}</div>', 420, 480, 'Notifications panel')

def compare_collapsed():
    """Same screen with the navigation collapsed via the hamburger: content widens."""
    import re as _re
    html = compare()
    return html.replace('<nav class="sidenav" aria-label="Main">','<nav class="sidenav collapsed" aria-label="Main">').replace('aria-label="Collapse navigation" aria-expanded="true"','aria-label="Expand navigation" aria-expanded="false"')

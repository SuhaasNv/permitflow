from lib import *
import screens_operator as _so

def admin():
    content = f'''
<div class="alert neutral" style="margin-bottom:20px">{ic('eye',18)}<div><b>Read-only oversight.</b> Administrators can open any application in the officer view but cannot change status, feedback or documents.</div></div>
<p class="muted" style="margin:-8px 0 20px;max-width:760px"><b class="num">23</b> open applications, <b class="num" style="color:var(--warning)">3</b> idle for more than 7 days (longest: PF-2026-000188, 8 days waiting on the operator). <b class="num">5</b> received today: 3 new, 2 resubmitted.</p>
<div class="split" style="grid-template-columns:minmax(0,1fr) 420px">
  <div class="stack" style="gap:20px">
    <div class="card">
      <div class="card-h"><h2 class="h3">Applications by internal status</h2><span class="meta">Live</span></div>
      <table class="table"><thead><tr><th>Status</th><th class="r">Count</th><th class="r">Median age</th><th class="r">Idle &gt; 7d</th></tr></thead><tbody>
        <tr><td>{status_badge('application_received','officer')}</td><td class="r num">8</td><td class="r num">1.2 d</td><td class="r num">0</td></tr>
        <tr><td>{status_badge('under_review','officer')}</td><td class="r num">6</td><td class="r num">3.5 d</td><td class="r num">1</td></tr>
        <tr><td>{status_badge('pending_pre_site_resubmission','officer')}</td><td class="r num">5</td><td class="r num">4.0 d</td><td class="r num" style="color:var(--error);font-weight:600">2</td></tr>
        <tr><td>{status_badge('pre_site_resubmitted','officer')}</td><td class="r num">1</td><td class="r num">0.1 d</td><td class="r num">0</td></tr>
        <tr><td>{status_badge('site_visit_scheduled','officer')}</td><td class="r num">2</td><td class="r num">6.1 d</td><td class="r num">0</td></tr>
        <tr><td>{status_badge('pending_approval','officer')}</td><td class="r num">1</td><td class="r num">9.0 d</td><td class="r num">0</td></tr>
        <tr><td>{status_badge('approved','officer')} <span class="meta">last 30 d</span></td><td class="r num">14</td><td></td><td></td></tr>
        <tr><td>{status_badge('rejected','officer')} <span class="meta">last 30 d</span></td><td class="r num">2</td><td></td><td></td></tr>
      </tbody></table>
    </div>
    <div class="card">
      <div class="card-h"><h2 class="h3">AI verification health · last 24 h</h2><span class="tag">Provider: openai · gpt-4o-mini</span></div>
      <div class="card-b stack" style="gap:14px">
        <div class="row" style="gap:32px"><div><div class="eyebrow">Runs</div><div class="h2 num">56</div></div><div><div class="eyebrow">Failed</div><div class="h2 num">1</div></div><div><div class="eyebrow">Unavailable</div><div class="h2 num">0</div></div><div><div class="eyebrow">Median latency</div><div class="h2 num">3.9 s</div></div><div><div class="eyebrow">p95 latency</div><div class="h2 num">7.4 s</div></div></div>
        <div class="sbar"><i style="width:68%;background:var(--success)"></i><i style="width:16%;background:var(--error)"></i><i style="width:12.5%;background:var(--warning)"></i><i style="width:2%;background:var(--neutral-line)"></i><i style="width:1.5%;background:#7A271A"></i></div>
        <div class="legend v"><span><i style="background:var(--success)"></i>Verified 38</span><span><i style="background:var(--error)"></i>Issues found 9</span><span><i style="background:var(--warning)"></i>Needs officer review 7</span><span><i style="background:var(--neutral-line)"></i>Could not read 1</span><span><i style="background:#7A271A"></i>Failed 1</span></div>
      </div>
    </div>
  </div>
  <div class="card">
    <div class="card-h"><h2 class="h3">Audit feed</h2><span class="meta">Latest 50 across all applications</span></div>
    <div class="card-b" style="padding:4px 20px 8px">{timeline([
      ('w','Feedback resolved · PF-2026-000214','Rahim bin Abdullah · Food hygiene certificate','11:02'),
      ('p','Under Review · PF-2026-000214','Rahim bin Abdullah · start review','10:58'),
      ('i','Verification needs review · PF-2026-000214','System · confidence 0.52','10:32'),
      ('s','Revision 2 · PF-2026-000214','Tan Wei Ling · resubmitted','10:31'),
      ('s','Revision 1 · PF-2026-000227','Siti Nurhaliza · submitted','09:58'),
      ('','Draft created · PF-2026-000231','Tan Wei Ling','08:51'),
      ('i','Verification failed · PF-2026-000219','System · provider schema error','Yesterday, 14:22'),
    ])}</div>
    <div class="card-f" style="justify-content:flex-start"><a class="small" href="AdminOverview.dc.html">Open full feed</a></div>
  </div>
</div>'''
    body = shell('admin','Overview',content,title='Operations overview',sub='Wednesday 17 Sep 2026, 11:05 · live')
    return page(body, 1280, 1160, 'Admin overview (concept)')

def design_system():
    sw = lambda name,var,txt='': f'<div><div style="height:56px;border-radius:6px;background:var({var});border:1px solid var(--line)"></div><div class="small" style="margin-top:6px;font-weight:600">{name}</div><div class="meta mono">{txt}</div></div>'
    statuses=''
    for code,(op,off,kind) in STATUS.items():
        statuses += f'<tr><td class="mono" style="font-size:12px">{code}</td><td>{badge(kind,off) if off!="—" else "<span class=meta>not shown to officers</span>"}</td><td>{badge(kind,op)}</td></tr>'
    vers = ''.join([
      ver_block('pending','Queued for checking','The check will start shortly.'),
      ver_block('running','Checking document…','Reading and comparing with the form.','<div class="vprog"><i></i></div>'),
      ver_block('verified','Verified','Details match the form.',confidence=0.92),
      ver_block('issues','2 issues found','Details contradict the form.',confidence=0.81),
      ver_block('review','Needs officer review','Low confidence or suspicious content.',confidence=0.52),
      ver_block('unreadable','Could not read this document','Image or empty PDF; no text extracted.'),
      ver_block('failed','Check failed','The checker returned an invalid result. Re-run available.'),
      ver_block('unavailable','Check unavailable','The checking service is not configured or timed out. You can still submit.'),
    ])
    body = f'''
<div style="padding:48px 56px;display:flex;flex-direction:column;gap:40px;background:var(--bg)">
  <div><div class="eyebrow p" style="margin-bottom:8px">PermitFlow design system · v0.1</div><h1 class="h1" style="font-size:32px;line-height:40px">Foundations and components</h1><p class="muted" style="margin-top:6px;max-width:720px">Restrained, government-service tone. Colour carries meaning; typography carries hierarchy. Every status uses a label and an icon or dot, never colour alone.</p></div>
  <section class="stack"><h2 class="h2">Colour</h2>
    <div style="display:grid;grid-template-columns:repeat(8,minmax(0,1fr));gap:16px">
      {sw('Primary','--primary','#A8192A')}{sw('Primary hover','--primary-hover','#8A1422')}{sw('Primary soft','--primary-soft','#FBEDEE')}{sw('Canvas','--bg','#F3F4F6')}{sw('Surface','--surface','#FFFFFF')}{sw('Line','--line','#D9DEE5')}{sw('Text','--text','#1B2430')}{sw('Text 2','--text-2','#465060')}
      {sw('Success','--success','#067647')}{sw('Success soft','--success-soft','#ECFDF3')}{sw('Warning','--warning','#9A4A00')}{sw('Warning soft','--warning-soft','#FFF6E5')}{sw('Error','--error','#B42318')}{sw('Error soft','--error-soft','#FEF3F2')}{sw('Info','--info','#175CD3')}{sw('Info soft','--info-soft','#EEF4FF')}
    </div>
    <p class="small muted">All text colours meet 4.5:1 on white and on their soft backgrounds. Primary red is reserved for the brand mark, primary actions and “needs you” signals, never for decoration.</p>
  </section>
  <section class="stack"><h2 class="h2">Typography: Public Sans</h2>
    <div class="card card-b stack" style="gap:14px">
      <div class="row-b"><span class="h1" style="font-size:40px;line-height:48px">Display 40 / 48 · 600</span><span class="meta">Landing hero only</span></div>
      <div class="row-b"><span class="h1">Page title 26 / 32 · 600</span><span class="meta">One per screen</span></div>
      <div class="row-b"><span class="h2">Section title 20 / 28 · 600</span><span class="meta">Dialogs, major panels</span></div>
      <div class="row-b"><span class="h3">Subsection 16 / 24 · 600</span><span class="meta">Card headers, form sections</span></div>
      <div class="row-b"><span>Body 15 / 22 · 400</span><span class="meta">Default reading size</span></div>
      <div class="row-b"><span class="small">Supporting 13 / 20 · 400</span><span class="meta">Help text, table cells, secondary</span></div>
      <div class="row-b"><span class="label">Label 13 / 18 · 600</span><span class="meta">Form labels, table headers (uppercase 12)</span></div>
      <div class="row-b"><span class="meta">Metadata 12 / 16 · 400 · text-3</span><span class="meta">Timestamps, counters</span></div>
      <div class="row-b"><span class="mono">Mono 13 · IBM Plex Mono · PF-2026-000214</span><span class="meta">References, UEN, event types</span></div>
    </div>
  </section>
  <section class="stack"><h2 class="h2">Buttons and inputs</h2>
    <div class="card card-b stack" style="gap:20px">
      <div class="row" style="gap:12px;flex-wrap:wrap"><a class="btn primary" href="#">Primary action</a><a class="btn secondary" href="#">Secondary</a><a class="btn ghost" href="#">Ghost</a><a class="btn danger" href="#">Reject…</a><a class="btn primary disabled" href="#">Disabled</a><a class="btn primary sm" href="#">Small</a><button class="iconbtn" aria-label="Notifications">{ic('bell',20)}<span class="dotcount">3</span></button></div>
      <div class="fgrid" style="grid-template-columns:repeat(4,minmax(0,1fr))">{field('Default','', placeholder='Placeholder',help='Helper text')}{field('Focused','Typing…',attrs='style="border-color:var(--focus);box-shadow:0 0 0 3px rgba(23,92,211,.18)"')}{field('Invalid','20878',error='Enter the 6-digit postal code.')}{field('Read-only','Carried forward',ro=True,required=False)}</div>
    </div>
  </section>
  <section class="stack"><h2 class="h2">Status badges: role-specific labels</h2>
    <div class="card"><table class="table"><thead><tr><th>Internal code</th><th>Officer sees</th><th>Operator sees</th></tr></thead><tbody>{statuses}</tbody></table></div>
    <p class="small muted">Colour groups: neutral = draft · info = in progress with the office · warning = needs the operator · success/error = outcome. Operators never receive the internal code; “Route to Approval” never reaches an operator screen.</p>
    <div class="row" style="gap:8px;flex-wrap:wrap"><span class="tag">Fact tag</span><span class="tag changed">Changed</span><span class="tag changed">Replaced</span><span class="tag editable">{ic('flag',12)} 1 feedback item</span><span class="tag editable">{ic('edit',12)} Open for changes</span><span class="tag readonly">{ic('lock',12)} Read-only</span><span class="meta">Tags: facts and markers (info = changed, warning = flagged/editable, neutral = read-only). Badges: state only.</span></div>
  </section>
  <section class="stack"><h2 class="h2">Document verification states (8)</h2>
    <div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px"><div class="doc">{vers[:len(vers)//2] if False else ''}</div></div>
  </section>
</div>'''
    # split vers into two columns properly
    parts = [
      ver_block('pending','Queued for checking','The check will start shortly.'),
      ver_block('running','Checking document…','Reading and comparing with the form.','<div class="vprog"><i></i></div>'),
      ver_block('verified','Verified','Details match the form.',confidence=0.92),
      ver_block('issues','2 issues found','Details contradict the form.',confidence=0.81),
      ver_block('review','Needs officer review','Low confidence or suspicious content.',confidence=0.52),
      ver_block('unreadable','Could not read this document','Image or empty PDF; no text extracted.'),
      ver_block('failed','Check failed','The checker returned an invalid result. Re-run available.'),
      ver_block('unavailable','Check unavailable','Service not configured or timed out. You can still submit.'),
    ]
    col1 = '<div class="doc">'+''.join(parts[:4])+'</div>'; col2='<div class="doc">'+''.join(parts[4:])+'</div>'
    body = body.replace('<div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px"><div class="doc"></div></div>', f'<div style="display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px">{col1}{col2}</div>')
    body += ''
    extra = f'''
<div style="padding:0 56px 48px;display:flex;flex-direction:column;gap:40px;background:var(--bg)">
  <section class="stack"><h2 class="h2">Feedback lifecycle, alerts, states</h2>
    <div class="grid2">
      <div class="fb">{fb_item(1,'open','section','Premises','Open: waiting for the operator.','<span>Round 1</span>')}{fb_item(2,'addressed','document','Tenancy agreement','Addressed: target changed in the new revision (automatic).','<span>Round 1</span>')}{fb_item(3,'resolved','document','Food hygiene certificate','Resolved: confirmed by the officer.','<span>Round 1</span>')}</div>
      <div class="stack-s">
        <div class="alert info">{ic('info',18)}<div><b>Info.</b> Guidance and system information.</div></div>
        <div class="alert warning">{ic('alert',18)}<div><b>Warning.</b> Attention required; not blocking.</div></div>
        <div class="alert error">{ic('alert',18)}<div><b>Error.</b> Validation failed or action blocked.</div></div>
        <div class="alert success">{ic('check',18)}<div><b>Success.</b> Saved, submitted, resolved.</div></div>
        <div class="toast"><span class="ti">{ic('check',18)}</span><div><div class="tt">Section saved</div><div class="tb">Draft updated just now</div></div></div>
      </div>
    </div>
    <div class="grid3">
      <div class="card"><div class="card-h"><span class="h3">Loading</span></div><div class="card-b stack-s"><div class="skel" style="width:60%"></div><div class="skel"></div><div class="skel" style="width:80%"></div><div class="skel" style="width:40%;height:24px;margin-top:6px"></div></div></div>
      <div class="card"><div class="empty"><div class="ei">{ic('folder',22)}</div><div class="et">No applications yet</div><div class="ed">Start a new application to apply for a Food Establishment Licence.</div><a class="btn primary sm" href="#" style="margin-top:14px">New application</a></div></div>
      <div class="card"><div class="empty"><div class="ei" style="background:var(--error-soft);color:var(--error)">{ic('x',22)}</div><div class="et">Could not load this application</div><div class="ed">Request ID 7f3a-19c2. Try again, or contact support if it keeps happening.</div><a class="btn secondary sm" href="#" style="margin-top:14px">{ic('refresh',14)}Retry</a></div></div>
    </div>
    <div class="grid2">
      <div class="card"><div class="empty"><div class="ei">{ic('lock',22)}</div><div class="et">Not available for your role</div><div class="ed">This page is for licensing officers. If you think this is a mistake, contact your administrator.</div></div></div>
      <div class="card"><div class="empty"><div class="ei">{ic('search',22)}</div><div class="et">Application not found</div><div class="ed">It may have been removed, or the link is incorrect.</div><a class="btn ghost sm" href="#" style="margin-top:14px">Back to my applications</a></div></div>
    </div>
  </section>
</div>'''
    return page(body+extra, 1440, 2520, 'Design system')

def mobile_dashboard():
    body = f'''
<div style="display:flex;flex-direction:column;height:100%;background:var(--bg)">
  <header class="topbar" style="padding:0 16px;gap:12px"><span class="brand">{LOGO_MARK}<span class="brand-name">PermitFlow</span></span><div class="top-right" style="gap:4px"><button class="iconbtn" aria-label="Notifications">{ic('bell',20)}<span class="dotcount">2</span></button><span class="avatar">TW</span></div></header>
  <main style="flex:1;padding:20px 16px;display:flex;flex-direction:column;gap:16px;overflow:hidden">
    <div><div class="eyebrow">Wednesday 17 Sep</div><h1 class="h1" style="font-size:22px;line-height:28px">Good morning, Wei Ling</h1></div>
    <a class="card" href="OperatorApplication.dc.html" style="padding:14px 16px;border-color:var(--warning-line);display:block;color:inherit;text-decoration:none">
      <div class="row-b" style="margin-bottom:6px">{badge('warning','Needs your action')}<span class="meta num">16 Sep</span></div>
      <div style="font-weight:600">PF-2026-000214 · Jalan Besar</div>
      <div class="small muted">The licensing office asked for 3 changes.</div>
      <div class="row" style="margin-top:10px;color:var(--primary);font-weight:600;font-size:14px">Respond {ic('arrowr',14)}</div>
    </a>
    <div class="row-b"><h2 class="h3">My applications</h2><span class="meta">4</span></div>
    <div class="card" style="overflow:hidden">
      <a class="row-b" href="OperatorApplication.dc.html" style="padding:12px 16px;border-bottom:1px solid var(--line);color:inherit;text-decoration:none"><div><div style="font-weight:600;font-size:14px">PF-2026-000203</div><div class="meta">Tampines · Rev 2</div></div>{status_badge('under_review')}</a>
      <a class="row-b" href="OperatorApplication.dc.html" style="padding:12px 16px;border-bottom:1px solid var(--line);color:inherit;text-decoration:none"><div><div style="font-weight:600;font-size:14px">PF-2026-000198</div><div class="meta">Bedok · Rev 1</div></div>{status_badge('site_visit_scheduled')}</a>
      <a class="row-b" href="OperatorApplication.dc.html" style="padding:12px 16px;border-bottom:1px solid var(--line);color:inherit;text-decoration:none"><div><div style="font-weight:600;font-size:14px">PF-2026-000214</div><div class="meta">Jalan Besar · Rev 1</div></div>{status_badge('pending_pre_site_resubmission')}</a>
      <a class="row-b" href="ApplicationForm.dc.html" style="padding:12px 16px;color:inherit;text-decoration:none"><div><div style="font-weight:600;font-size:14px">PF-2026-000231</div><div class="meta">Clementi · draft, 1 of 6 steps</div></div>{status_badge('draft')}</a>
    </div>
    <a class="btn primary" href="ApplicationForm.dc.html" style="height:48px">{ic('plus',16)}New application</a>
    <div class="row-b"><h2 class="h3">Recent activity</h2></div>
    <div class="card card-b" style="padding:16px 16px 0">{timeline([('w','Changes requested','PF-2026-000214 · 3 items','16 Sep, 15:42'),('i','Under review','PF-2026-000203','14 Sep, 09:10')])}</div>
  </main>
  <nav style="height:64px;border-top:1px solid var(--line);background:#fff;display:flex;padding:6px 8px" aria-label="Bottom navigation">
    <a class="navitem active" href="OperatorDashboard.dc.html" style="flex:1;flex-direction:column;gap:2px;font-size:11px;padding:6px">{ic('home',20)}Home</a>
    <a class="navitem" href="OperatorDashboard.dc.html" style="flex:1;flex-direction:column;gap:2px;font-size:11px;padding:6px">{ic('folder',20)}Applications</a>
    <a class="navitem" href="OperatorDashboard.dc.html" style="flex:1;flex-direction:column;gap:2px;font-size:11px;padding:6px">{ic('bell',20)}Alerts</a>
    <a class="navitem" href="OperatorDashboard.dc.html" style="flex:1;flex-direction:column;gap:2px;font-size:11px;padding:6px">{ic('help',20)}Help</a>
  </nav>
</div>'''
    return page(body, 390, 844, 'Operator dashboard — phone')

def mobile_application():
    body = f'''
<div style="display:flex;flex-direction:column;height:100%;background:var(--bg)">
  <header class="topbar" style="padding:0 8px 0 4px;gap:4px"><a class="iconbtn" href="OperatorDashboard.dc.html" aria-label="Back">{ic('arrowl',20)}</a><div style="min-width:0"><div style="font-weight:600;font-size:14px;line-height:18px">PF-2026-000214</div><div class="meta" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">Kopi &amp; Kaya Toast House · Jalan Besar</div></div><div class="top-right"><a class="iconbtn" href="OperatorHistory.dc.html" aria-label="History">{ic('history',20)}</a></div></header>
  <main style="flex:1;padding:16px;display:flex;flex-direction:column;gap:14px;overflow:hidden">
    <div class="card" style="padding:12px 14px"><div class="row-b" style="margin-bottom:4px">{status_badge('pending_pre_site_resubmission')}<span class="meta">Rev 1</span></div><div class="small muted">Update the 3 flagged items and resubmit. Everything else is kept.</div><div class="progress" style="margin-top:10px"><i style="width:33%"></i></div><div class="meta" style="margin-top:6px">1 of 3 flagged items changed</div></div>
    <div class="fb">
      <div class="fb-h" style="padding:10px 14px">{ic('msg',16)}<span class="h3" style="font-size:14px">Feedback · Round 1</span></div>
      <a class="fbi" href="#premises" style="padding:12px 14px;color:inherit;text-decoration:none"><span class="fbn">1</span><div class="fbt"><div class="fbtarget"><span class="tag">Section: Premises</span>{badge('warning','Open')}</div><div class="fbmsg" style="font-size:13px;line-height:19px">Floor area (48 sqm) does not match the tenancy agreement (62 sqm).</div></div>{ic('chev',16)}</a>
      <a class="fbi" href="#doc" style="padding:12px 14px;color:inherit;text-decoration:none"><span class="fbn">2</span><div class="fbt"><div class="fbtarget"><span class="tag">Document: Tenancy agreement</span>{badge('warning','Open')}</div><div class="fbmsg" style="font-size:13px;line-height:19px">Tenancy expires 31 Oct 2026. Upload a renewed agreement.</div></div>{ic('chev',16)}</a>
      <a class="fbi" href="#doc" style="padding:12px 14px;color:inherit;text-decoration:none"><span class="fbn">3</span><div class="fbt"><div class="fbtarget"><span class="tag">Document: Food hygiene certificate</span>{badge('warning','Open')}</div><div class="fbmsg" style="font-size:13px;line-height:19px">Image too low in resolution. Upload a clearer scan.</div></div>{ic('chev',16)}</a>
    </div>
    <section class="fsec flagged" id="premises"><div class="fsec-h" style="padding:12px 14px"><h2 class="h3" style="font-size:14px">Premises</h2><span class="tag editable" style="margin-left:auto">Open for changes</span></div>
      <div class="fsec-b stack" style="padding:14px;gap:12px">{field('Floor area (sqm)','62','number',help='Previously 48 sqm.')}</div></section>
    <section class="fsec locked"><div class="fsec-h" style="padding:12px 14px"><h2 class="h3" style="font-size:14px">Business details</h2><span class="tag readonly" style="margin-left:auto">{ic('lock',11)} Read-only</span></div></section>
  </main>
  <div style="padding:12px 16px 20px;border-top:1px solid var(--line);background:#fff"><a class="btn primary" href="OfficerQueue.dc.html" style="height:48px;width:100%">Resubmit application</a><div class="meta" style="text-align:center;margin-top:8px">1 of 3 flagged items changed. You can resubmit now, or continue with the other items first</div></div>
</div>'''
    return page(body, 390, 844, 'Operator application — phone')

def landing():
    body = f"""
<div class="land" style="height:100%;display:flex;flex-direction:column">
  <div class="masthead">{ic('lock',12)}<span><b>PermitFlow</b> · licensing services for food establishments</span></div>
  <header style="height:64px;border-bottom:1px solid var(--line);display:flex;align-items:center"><div class="wrap row-b" style="width:100%"><a class="brand" href="Landing.dc.html">{LOGO_MARK}<span class="brand-name">PermitFlow</span></a><nav class="row" style="gap:24px;font-size:14px;font-weight:500"><a href="#how" style="color:var(--text-2)">How it works</a><a href="#need" style="color:var(--text-2)">What you need</a><a href="#track" style="color:var(--text-2)">Track an application</a><a class="btn primary sm" href="Main.dc.html" style="height:36px">Sign in</a></nav></div></header>
  <section class="land-hero"><div class="wrap" style="display:grid;grid-template-columns:minmax(0,1fr) 360px;gap:64px;align-items:start">
    <div>
    <div class="eyebrow p" style="margin-bottom:14px">Food Establishment Licence</div>
    <h1>Apply for a food establishment licence and respond to the licensing officer in one place.</h1>
    <p class="lead">Complete the application in sections, upload your documents and see automatic checks before you submit. If the licensing office needs changes, you update only what was flagged. Nothing you entered is lost.</p>
    <div class="row" style="gap:12px;margin-top:28px"><a class="btn primary" href="Main.dc.html" style="height:48px;padding:0 24px">Sign in to apply</a><a class="btn secondary" href="#how" style="height:48px;padding:0 24px">How it works</a></div>
    <p class="meta" style="margin-top:16px">Takes about 20 minutes. You can save a draft and return later.</p>
    </div>
    <div class="card" style="padding:20px 24px;margin-top:44px" id="need">
      <div class="label" style="margin-bottom:12px">What you need</div>
      <div class="stack-s small" style="gap:10px">
        <div class="row" style="gap:10px;align-items:flex-start"><span style="color:var(--success);margin-top:2px">{ic('check',15)}</span><div><b>ACRA business profile</b><div class="muted">Issued within the last 6 months</div></div></div>
        <div class="row" style="gap:10px;align-items:flex-start"><span style="color:var(--success);margin-top:2px">{ic('check',15)}</span><div><b>Floor plan of the premises</b><div class="muted">Showing the food preparation area</div></div></div>
        <div class="row" style="gap:10px;align-items:flex-start"><span style="color:var(--success);margin-top:2px">{ic('check',15)}</span><div><b>Signed tenancy agreement</b><div class="muted">Covering the full licence period</div></div></div>
        <div class="row" style="gap:10px;align-items:flex-start"><span style="color:var(--success);margin-top:2px">{ic('check',15)}</span><div><b>Food hygiene certificate</b><div class="muted">For the business or a named food handler</div></div></div>
      </div>
      <div class="meta" style="margin-top:14px;line-height:18px">PDF, PNG, JPG or TXT, up to 10 MB each. PDF is recommended: it is the only format the automatic check can read.</div>
    </div>
  </div></section>
  <section class="land-sec" id="how"><div class="wrap">
    <h2>How it works</h2>
    <div class="hiw">
      <div><div class="n">01</div><div class="t">Apply</div><div class="d">Four short sections: business, premises, operations and declarations. Each one validates as you go.</div></div>
      <div><div class="n">02</div><div class="t">Automatic document checks</div><div class="d">Each upload is read and compared with your form so you can fix likely problems early. The checks are advisory: they never decide the outcome.</div></div>
      <div><div class="n">03</div><div class="t">Officer review</div><div class="d">A licensing officer reviews your application. If something needs changing, you receive feedback tied to the exact section or document.</div></div>
      <div><div class="n">04</div><div class="t">Site visit and outcome</div><div class="d">After a satisfactory review and a visit to the premises, you are notified of the decision here and by email.</div></div>
    </div>
  </div></section>
  <section class="land-sec" id="track" style="border-bottom:0"><div class="wrap">
    <h2>Track every step</h2>
    <div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:32px;max-width:960px">
      <div><div style="margin-bottom:8px">{status_badge('under_review')}</div><div class="small muted">The licensing office is working on it. Nothing is needed from you.</div></div>
      <div><div style="margin-bottom:8px">{status_badge('pending_pre_site_resubmission')}</div><div class="small muted">Feedback is waiting for you. Only the flagged parts reopen for editing.</div></div>
      <div><div style="margin-bottom:8px">{status_badge('approved')}</div><div class="small muted">The outcome, with the officer's note, stays on your dashboard with the full history.</div></div>
    </div>
    <p class="muted" style="margin-top:20px;max-width:640px">Every application keeps a complete record: each revision you submitted, every comment from the licensing office, and when each status changed.</p>
  </div></section>
  <footer class="land-foot" style="border-top:1px solid var(--line);margin-top:auto"><div class="wrap row" style="gap:24px;width:100%"><span>© 2026 PermitFlow (fictional prototype)</span><a href="Landing.dc.html">Privacy</a><a href="Landing.dc.html">Terms of use</a><a href="Landing.dc.html">Accessibility</a><a href="Landing.dc.html">Contact</a><a href="OfficerQueue.dc.html" style="margin-left:auto">Staff sign-in</a></div></footer>
</div>"""
    return page(body, 1280, 1720, 'Landing page')

def admin_users():
    def urow(ini,name,email,role,status,created,last):
        st = badge('success','Active') if status=='active' else badge('neutral','Deactivated')
        return f'<tr><td><div class="row" style="gap:10px"><span class="avatar" style="width:28px;height:28px;font-size:11px">{ini}</span><div><div style="font-weight:600">{name}</div><div class="meta">{email}</div></div></div></td><td><span class="role {role}">{role.capitalize()}</span></td><td>{st}</td><td class="num small muted">{created}</td><td class="num small muted">{last}</td><td class="r"><a class="btn ghost sm" href="AdminUsers.dc.html">Change role</a><a class="btn ghost sm" href="AdminUsers.dc.html">{"Deactivate" if status=="active" else "Reactivate"}</a></td></tr>'
    rows = ''.join([
      urow('RA','Rahim bin Abdullah','rahim.abdullah@licensing.example.sg','officer','active','2 Jan 2026','Today, 11:02'),
      urow('PN','Priya Nair','priya.nair@licensing.example.sg','admin','active','2 Jan 2026','Today, 11:05'),
      urow('MC','Marcus Chen','marcus.chen@licensing.example.sg','officer','active','15 Mar 2026','Yesterday, 17:40'),
      urow('TW','Tan Wei Ling','weiling.tan@kopikaya.sg','operator','active','8 Sep 2026','Today, 10:31'),
      urow('SN','Siti Nurhaliza','siti@nasilemakcorner.sg','operator','active','12 Sep 2026','Today, 09:58'),
      urow('KW','Kenji Watanabe','kenji@sakura-izakaya.sg','operator','active','14 Sep 2026','16 Sep, 14:20'),
      urow('LA','Lim Ah Huat','ahhuat.noodles@gmail.example','operator','active','1 Sep 2026','9 Sep, 16:45'),
      urow('JL','Jasmine Lee','jasmine.lee@licensing.example.sg','officer','inactive','2 Jan 2026','30 Jun 2026'),
    ])
    drawer = f"""<aside class="drawer fade" role="dialog" aria-labelledby="dr-t">
  <div class="drawer-h"><h2 class="h3" id="dr-t">Add user</h2><button class="iconbtn" aria-label="Close">{ic('x',18)}</button></div>
  <div class="drawer-b">
    {field('Full name','Marcus Chen'.replace('Marcus Chen','Nurul Aisyah'))}
    {field('Email address','nurul.aisyah@licensing.example.sg','email',help='The sign-in link is sent to this address.')}
    <div class="field"><span class="label">Role<span class="req">*</span></span>
      <label class="radio"><input type="radio" name="role"><div><div style="font-weight:600;font-size:14px">Operator</div><div class="small muted">Applies for licences. Sees only their own applications.</div></div></label>
      <label class="radio on"><input type="radio" name="role" checked><div><div style="font-weight:600;font-size:14px">Licensing officer</div><div class="small muted">Reviews any application, gives feedback, changes status.</div></div></label>
      <label class="radio"><input type="radio" name="role"><div><div style="font-weight:600;font-size:14px">Administrator</div><div class="small muted">Manages users and monitors the platform. Read-only on applications.</div></div></label>
    </div>
    <div class="alert neutral" style="padding:10px 12px">{ic('history',16)}<div class="small">Every user change is recorded in the audit trail with your name and the time.</div></div>
  </div>
  <div class="drawer-f"><a class="btn ghost" href="AdminUsers.dc.html">Cancel</a><a class="btn primary" href="AdminUsers.dc.html">Create user and send invite</a></div>
</aside>"""
    content = f"""
<div class="card">
  <div class="card-h"><div class="row" style="gap:4px"><a class="tab active" href="AdminUsers.dc.html" style="padding:6px 10px">All<span class="cnt num">8</span></a><a class="tab" href="AdminUsers.dc.html" style="padding:6px 10px">Officers<span class="cnt num">3</span></a><a class="tab" href="AdminUsers.dc.html" style="padding:6px 10px">Operators<span class="cnt num">4</span></a><a class="tab" href="AdminUsers.dc.html" style="padding:6px 10px">Administrators<span class="cnt num">1</span></a></div><div class="row" style="gap:8px"><div style="position:relative"><span style="position:absolute;left:10px;top:11px;color:var(--text-3)">{ic('search',16)}</span><input class="input" style="width:200px;height:36px;padding-left:34px" placeholder="Search"></div></div></div>
  <table class="table"><colgroup><col style="width:330px"><col style="width:120px"><col style="width:120px"><col style="width:110px"><col style="width:130px"><col></colgroup>
    <thead><tr><th>User</th><th>Role</th><th>Status</th><th>Created</th><th>Last active</th><th></th></tr></thead>
    <tbody>{rows}</tbody></table>
</div>
<p class="meta" style="margin-top:12px">Deactivated users cannot sign in; their history stays attached to their applications and audit events. Changing a role takes effect at the user's next request.</p>"""
    body = shell('admin','Users',content,title='Users',sub='Create accounts, change roles and deactivate access.',actions=f'<a class="btn primary" href="AdminUsers.dc.html">{ic("plus",16)}Add user</a>')
    # place drawer over the right of the body
    body += f'<div class="drawer-bg">{drawer}</div>'
    return page(body, 1280, 1000, 'Admin users')

def tablet_documents():
    html = _so.documents()
    import re as _re
    html = _re.sub(r'<div class="root " style="width: 1280px; height: \d+px;', '<div class="root tablet" style="width: 1024px; height: 1700px;', html, count=1)
    html = _re.sub(r'"\$preview":\{"width":1280,"height":\d+\}', '"$preview":{"width":1024,"height":1700}', html, count=1)
    return html

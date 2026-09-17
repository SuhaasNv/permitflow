from css import CSS

FONT = '<link href="https://fonts.googleapis.com/css2?family=Public+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">'

def svg(path, size=18, stroke=2):
    return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{path}</svg>'

ICON = {
 'check': '<path d="M20 6 9 17l-5-5"/>',
 'x': '<path d="M18 6 6 18M6 6l12 12"/>',
 'alert': '<path d="m10.3 3.9-8.5 14.6A2 2 0 0 0 3.5 21.5h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><path d="M12 9v4M12 17h.01"/>',
 'info': '<circle cx="12" cy="12" r="10"/><path d="M12 16v-4M12 8h.01"/>',
 'clock': '<circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>',
 'file': '<path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5z"/><path d="M14 2v6h6"/>',
 'image': '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="m21 15-5-5L5 21"/>',
 'upload': '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m17 8-5-5-5 5M12 3v12"/>',
 'refresh': '<path d="M21 12a9 9 0 1 1-2.6-6.4"/><path d="M21 3v6h-6"/>',
 'download': '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><path d="m7 10 5 5 5-5M12 15V3"/>',
 'bell': '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.7 21a2 2 0 0 1-3.4 0"/>',
 'home': '<path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M9 22V12h6v10"/>',
 'folder': '<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>',
 'help': '<circle cx="12" cy="12" r="10"/><path d="M9.1 9a3 3 0 0 1 5.8 1c0 2-3 3-3 3M12 17h.01"/>',
 'inbox': '<path d="M22 12h-6l-2 3h-4l-2-3H2"/><path d="M5.5 5.1 2 12v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2v-6l-3.5-6.9A2 2 0 0 0 16.8 4H7.2a2 2 0 0 0-1.7 1.1z"/>',
 'users': '<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.9M16 3.1a4 4 0 0 1 0 7.8"/>',
 'activity': '<path d="M22 12h-4l-3 9L9 3l-3 9H2"/>',
 'chev': '<path d="m9 18 6-6-6-6"/>',
 'chevd': '<path d="m6 9 6 6 6-6"/>',
 'plus': '<path d="M12 5v14M5 12h14"/>',
 'msg': '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
 'eye': '<path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>',
 'lock': '<rect x="3" y="11" width="18" height="11" rx="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/>',
 'edit': '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4z"/>',
 'shield': '<path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>',
 'sparkle': '<path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M5.6 18.4l2.1-2.1M16.3 7.7l2.1-2.1"/><circle cx="12" cy="12" r="3"/>',
 'compare': '<path d="M16 3h5v5M4 20 21 3M21 16v5h-5M15 15l6 6M4 4l5 5"/>',
 'history': '<path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l3 2"/>',
 'send': '<path d="m22 2-7 20-4-9-9-4z"/><path d="M22 2 11 13"/>',
 'search': '<circle cx="11" cy="11" r="8"/><path d="m21 21-4.3-4.3"/>',
 'filter': '<path d="M22 3H2l8 9.5V19l4 2v-8.5z"/>',
 'arrowr': '<path d="M5 12h14M12 5l7 7-7 7"/>',
 'arrowl': '<path d="M19 12H5M12 19l-7-7 7-7"/>',
 'calendar': '<rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/>',
 'ban': '<circle cx="12" cy="12" r="10"/><path d="m4.9 4.9 14.2 14.2"/>',
 'flag': '<path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"/><path d="M4 22v-7"/>',
 'menu': '<path d="M3 12h18M3 6h18M3 18h18"/>',
 'dots': '<circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/>',
}
def ic(name, size=18, stroke=2): return svg(ICON[name], size, stroke)

LOGO_MARK = '<svg width="28" height="28" viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="7" fill="#A8192A"/><path d="M9 10h14M9 16h9M9 22h4M16.5 22l2.5 2.5L24 18" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/></svg>'

def badge(kind, label, lg=False):
    return f'<span class="badge {kind}{" lg" if lg else ""}"><span class="dot"></span>{label}</span>'

# Operator label -> badge kind ; officer label -> badge kind
STATUS = {
 'draft': ('Draft','—','neutral'),
 'application_received': ('Submitted','Application Received','info'),
 'under_review': ('Under Review','Under Review','info'),
 'pending_pre_site_resubmission': ('Pending Pre-Site Resubmission','Pending Pre-Site Resubmission','warning'),
 'pre_site_resubmitted': ('Pre-Site Resubmitted','Pre-Site Resubmitted','info'),
 'site_visit_scheduled': ('Pending Site Visit','Site Visit Scheduled','info'),
 'site_visit_done': ('Pending Post-Site Clarification','Site Visit Done','info'),
 'awaiting_post_site_clarification': ('Pending Post-Site Clarification','Awaiting Post-Site Clarification','info'),
 'pending_post_site_resubmission': ('Pending Post-Site Resubmission','Awaiting Post-Site Resubmission','warning'),
 'post_site_clarification_resubmitted': ('Post-Site Resubmitted','Post-Site Clarification Resubmitted','info'),
 'pending_approval': ('Pending Approval','Route to Approval','info'),
 'approved': ('Approved','Approved','success'),
 'rejected': ('Rejected','Rejected','error'),
}
def status_badge(code, role='operator', lg=False):
    op, off, kind = STATUS[code]
    return badge(kind, op if role=='operator' else off, lg)

def page(body, w, h, title, extra_css='', root_class=''):
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
  {FONT}
  <style>{CSS}{extra_css}</style>
</helmet>
<div class="root {root_class}" style="width: {w}px; height: {h}px; position: relative;" aria-label="{title}">
{body}
</div>
</x-dc>
<script data-dc-script data-props='{{"$preview":{{"width":{w},"height":{h}}}}}'>
class Component extends DCLogic {{
  renderVals() {{ return {{}}; }}
}}
</script>
</body>
</html>
'''

NAV = {
 'operator': [('Dashboard','home','OperatorDashboard.dc.html'),('My applications','folder','OperatorDashboard.dc.html'),('Notifications','bell','OperatorDashboard.dc.html'),('Help &amp; support','help','OperatorDashboard.dc.html')],
 'officer': [('Review queue','inbox','OfficerQueue.dc.html'),('Notifications','bell','OfficerQueue.dc.html'),('Comment templates','msg','OfficerQueue.dc.html'),('Help &amp; support','help','OfficerQueue.dc.html')],
 'admin': [('Overview','activity','AdminOverview.dc.html'),('Applications','folder','AdminOverview.dc.html'),('AI verification health','sparkle','AdminOverview.dc.html'),('Users','users','AdminUsers.dc.html'),('Audit feed','history','AdminOverview.dc.html')],
}
USER = {
 'operator': ('Tan Wei Ling','Operator · Kopi &amp; Kaya Toast House Pte. Ltd.','TW'),
 'officer': ('Rahim bin Abdullah','Licensing Officer · Food Establishments','RA'),
 'admin': ('Priya Nair','Platform Administrator','PN'),
}
COUNTS = {'operator': {'Notifications':2}, 'officer': {'Review queue':2,'Notifications':3}, 'admin': {}}

def shell(role, active, content, crumbs=None, title=None, sub=None, actions='', overlay='', notif=0, collapsed=False, tablet=False):
    name, rl, ini = USER[role]
    nav = ''.join(
        f'<a class="navitem{" active" if n==active else ""}" href="{href}" title="{n}">{ic(i,18)}<span>{n}</span>' +
        (f'<span class="cnt num">{COUNTS[role][n]}</span>' if n in COUNTS[role] else '') + '</a>'
        for n,i,href in NAV[role])
    crumb_html = ''
    if crumbs:
        parts=[]
        for i,(t,href) in enumerate(crumbs):
            if i: parts.append(f'<span class="sep">{ic("chev",14)}</span>')
            parts.append(f'<a href="{href}">{t}</a>' if href else f'<span style="color:var(--text)">{t}</span>')
        crumb_html = f'<nav class="crumbs" aria-label="Breadcrumb">{"".join(parts)}</nav>'
    head = ''
    if title:
        head = f'<div class="pagehead"><div><h1 class="h1">{title}</h1>{f"<p class=sub>{sub}</p>" if sub else ""}</div><div class="actions">{actions}</div></div>'
    bell_cnt = f'<span class="dotcount num">{notif}</span>' if notif else ''
    return f'''
<div class="masthead">{ic('lock',12)}<span><b>Secure licensing portal</b> · Food Establishments Unit</span><span class="mr"><span>Session expires after 8 hours</span></span></div>
<header class="topbar">
  <button class="iconbtn" aria-label="{ 'Expand navigation' if collapsed else 'Collapse navigation' }" aria-expanded="{ 'false' if collapsed else 'true' }" style="margin-left:-8px">{ic('menu',20)}</button>
  <a class="brand" href="Main.dc.html" aria-label="PermitFlow home">{LOGO_MARK}<span class="brand-name">PermitFlow</span><span class="brand-sub">Licensing Services</span></a>
  <div class="top-right">
    <button class="iconbtn" aria-label="Notifications">{ic('bell',20)}{bell_cnt}</button>
    <div class="userchip"><span class="avatar">{ini}</span><div><div style="font-size:13px;font-weight:600;line-height:16px">{name}</div><div class="meta">{rl}</div></div></div>
    <a class="btn ghost sm" href="Main.dc.html">Sign out</a>
  </div>
</header>
<div class="body">
  <nav class="sidenav{' collapsed' if collapsed else ''}" aria-label="Main">
    <div class="navlabel">{ {'operator':'Operator','officer':'Licensing officer','admin':'Administration'}[role] }</div>
    {nav}
    <div class="navfoot"><a href="Main.dc.html">Privacy</a> · <a href="Main.dc.html">Terms</a> · <a href="Main.dc.html">Accessibility</a><br>© 2026 PermitFlow</div>
  </nav>
  <main class="main">
    {crumb_html}{head}
    {content}
  </main>
</div>
{overlay}
'''

def field(label, value='', kind='input', required=True, help='', error='', placeholder='', ro=False, wide=False, invalid=False, attrs=''):
    req = '<span class="req" aria-hidden="true">*</span>' if required else ''
    cls = 'input' + (' ro' if ro else '') + (' invalid' if invalid or error else '')
    if kind=='textarea':
        ctl = f'<textarea class="{cls}" {"readonly" if ro else ""} {attrs}>{value}</textarea>'
    elif kind=='select':
        ctl = f'<select class="{cls} select" {"disabled" if ro else ""} {attrs}><option>{value or placeholder}</option></select>'
    elif kind=='date':
        from datetime import datetime as _dt
        try: shown=_dt.strptime(value,'%Y-%m-%d').strftime('%d/%m/%Y')
        except Exception: shown=value
        ctl = f'<div class="datefield"><input class="{cls}" type="text" inputmode="numeric" value="{shown}" placeholder="DD/MM/YYYY" {"readonly" if ro else ""} {attrs}>{ic("calendar",16)}</div>'
    else:
        ctl = f'<input class="{cls}" type="{kind}" value="{value}" placeholder="{placeholder}" {"readonly" if ro else ""} {attrs}>'
    h = f'<div class="help">{help}</div>' if help and not error else ''
    e = f'<div class="errtext" role="alert">{ic("alert",14)}{error}</div>' if error else ''
    return f'<div class="field"{" style=grid-column:1/-1" if wide else ""}><label class="label">{label}{req}</label>{ctl}{h}{e}</div>'

def ver_block(state, title, desc, extra='', confidence=None, meta=''):
    icons={'pending':'clock','running':None,'verified':'check','issues':'alert','review':'eye','unreadable':'image','failed':'x','unavailable':'ban'}
    i = icons[state]
    vi = f'<span class="vi">{ic(i,16)}</span>' if i else '<span class="vi"><span class="spin"></span></span>'
    conf = ''
    if confidence is not None:
        conf = f'<span class="conf" title="Model self-reported confidence; a hint, not a decision">Confidence <i><b style="width:{int(confidence*100)}%"></b></i> {confidence:.2f}</span>'
    return f'<div class="ver {state}">{vi}<div class="vt"><div class="vh">{title}{conf}</div><div class="vd">{desc}</div>{extra}</div></div>'

def doc_card(name, dtype, size, when, ver_html, footer='', icon='file', upl=True):
    return f'''<div class="doc">
  <div class="doc-h"><span class="doc-ic">{ic(icon,18)}</span><div class="doc-t"><div class="name">{name}</div><div class="meta">{dtype} · {size} · uploaded {when}</div></div>{badge('success','Upload complete') if (size and upl) else ''}</div>
  {ver_html}
  {f'<div class="doc-f">{footer}</div>' if footer else ''}
</div>'''

def issue(sev, msg, ev=''):
    return f'<div class="issue"><span class="sev {sev}">{sev}</span><div>{msg}{f"<div class=ev>Evidence: “{ev}”</div>" if ev else ""}</div></div>'

def fb_item(n, state, target_kind, target, msg, meta, extra=''):
    lbl = {'open':('warning','Open'),'addressed':('info','Addressed in Rev 2'),'resolved':('success','Resolved')}[state]
    tk = 'Section' if target_kind=='section' else 'Document'
    return f'''<div class="fbi {state}"><span class="fbn">{n}</span><div class="fbt">
  <div class="fbtarget"><span class="tag">{tk}: {target}</span>{badge(lbl[0],lbl[1])}</div>
  <div class="fbmsg">{msg}</div>
  <div class="fbmeta meta">{meta}</div>{extra}</div></div>'''

def timeline(items):
    items=[(('i' if d=='p' else d),t,de,w) for d,t,de,w in items]
    out=''
    for dot, title, desc, when in items:
        out += f'<div class="tli"><span class="tdot {dot}">{ic("check",12) if dot in ("s","p") else ic("dots",12) if dot=="" else ic("flag",12) if dot=="w" else ic("arrowr",12)}</span><div><div class="tt">{title}</div><div class="td">{desc}</div><div class="tm meta">{when}</div></div></div>'
    return f'<div class="tl">{out}</div>'

def stepper(steps, current):
    out=''
    for i,s in enumerate(steps):
        cls = 'done' if i<current else 'current' if i==current else ''
        out += f'<span class="step {cls}"><span class="n">{ic("check",12) if i<current else i+1}</span>{s}</span>'
        if i<len(steps)-1: out += f'<span class="step-line{" done" if i<current else ""}"></span>'
    return f'<div class="stepper">{out}</div>'

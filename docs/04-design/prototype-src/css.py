CSS = r"""
:root{
  --bg:#F3F4F6; --surface:#FFFFFF; --surface-2:#F9FAFB; --line:#D9DEE5; --line-strong:#AEB6C2;
  --text:#1B2430; --text-2:#465060; --text-3:#66717F;
  --primary:#A8192A; --primary-hover:#8A1422; --primary-soft:#FBEDEE; --primary-line:#EFB8BE;
  --success:#067647; --success-soft:#ECFDF3; --success-line:#A6E9C4;
  --warning:#9A4A00; --warning-soft:#FFF6E5; --warning-line:#F5CF86;
  --error:#B42318; --error-soft:#FEF3F2; --error-line:#F4B7B1;
  --info:#175CD3; --info-soft:#EEF4FF; --info-line:#B2CCFA;
  --neutral:#475467; --neutral-soft:#F2F4F7; --neutral-line:#D0D5DD;
  --focus:#175CD3; --radius:6px; --radius-lg:10px;
  --shadow-1:0 1px 2px rgba(16,24,40,.06); --shadow-2:0 4px 12px rgba(16,24,40,.10);
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:'Public Sans',system-ui,-apple-system,'Segoe UI',sans-serif;font-size:15px;line-height:22px;-webkit-font-smoothing:antialiased}
a{color:var(--primary);text-decoration:none} a:hover{color:var(--primary-hover);text-decoration:underline}
h1,h2,h3,h4,p{margin:0}
.h1{font-size:26px;line-height:32px;font-weight:600;letter-spacing:-.01em}
.h2{font-size:20px;line-height:28px;font-weight:600}
.h3{font-size:16px;line-height:24px;font-weight:600}
.small{font-size:13px;line-height:20px} .meta{font-size:12px;line-height:16px;color:var(--text-3)}
.muted{color:var(--text-2)} .muted3{color:var(--text-3)} .num{font-variant-numeric:tabular-nums}
.mono{font-family:'IBM Plex Mono','SF Mono',Menlo,monospace;font-size:13px}
:focus-visible{outline:2px solid var(--focus);outline-offset:2px;border-radius:4px}

/* shell */
.masthead{height:28px;background:#1B2430;color:#C5CBD3;font-size:12px;display:flex;align-items:center;padding:0 24px;gap:8px;flex-shrink:0} .masthead b{color:#fff;font-weight:600} .masthead .mr{margin-left:auto;display:flex;gap:16px}
.root{background:var(--bg);display:flex;flex-direction:column;overflow:hidden}
.topbar{height:56px;background:var(--surface);border-bottom:1px solid var(--line);display:flex;align-items:center;padding:0 24px;gap:24px;flex-shrink:0}
.brand{display:flex;align-items:center;gap:10px;color:var(--text)!important;text-decoration:none!important}
.brand-mark{width:28px;height:28px;border-radius:6px;background:var(--primary);display:flex;align-items:center;justify-content:center;color:#fff;font-weight:700;font-size:14px}
.brand-name{font-weight:700;font-size:16px;letter-spacing:-.01em}
.brand-sub{font-size:12px;color:var(--text-3);border-left:1px solid var(--line);padding-left:10px;margin-left:2px}
.top-right{margin-left:auto;display:flex;align-items:center;gap:8px}
.iconbtn{position:relative;width:40px;height:40px;border:1px solid transparent;background:transparent;border-radius:var(--radius);display:inline-flex;align-items:center;justify-content:center;color:var(--text-2);cursor:pointer;transition:background .15s}
.iconbtn:hover{background:var(--neutral-soft);color:var(--text)}
.dotcount{position:absolute;top:6px;right:6px;min-width:16px;height:16px;padding:0 4px;border-radius:8px;background:var(--primary);color:#fff;font-size:10px;line-height:16px;font-weight:700;text-align:center}
.userchip{display:flex;align-items:center;gap:10px;padding:4px 8px 4px 4px;border-radius:var(--radius);border:1px solid transparent}
.userchip:hover{background:var(--neutral-soft)}
.avatar{width:32px;height:32px;border-radius:50%;background:#E4E7EC;color:var(--text-2);display:flex;align-items:center;justify-content:center;font-weight:600;font-size:12px}
.body{display:flex;flex:1;min-height:0}
.sidenav{width:232px;background:var(--surface);border-right:1px solid var(--line);padding:16px 12px;display:flex;flex-direction:column;gap:2px;flex-shrink:0}
.navlabel{font-size:11px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--text-3);padding:8px 12px 4px}
.navitem{display:flex;align-items:center;gap:10px;padding:9px 12px;border-radius:var(--radius);color:var(--text-2);font-weight:500;font-size:14px;line-height:20px;transition:background .15s,color .15s}
.navitem:hover{background:var(--neutral-soft);color:var(--text);text-decoration:none}
.navitem.active{background:var(--neutral-soft);color:var(--text);font-weight:600;box-shadow:inset 3px 0 0 var(--primary)}
.navitem .cnt{margin-left:auto;font-size:12px;background:var(--neutral-soft);color:var(--text-2);padding:0 6px;border-radius:10px;line-height:18px}
.navitem.active .cnt{background:#fff;color:var(--text)}
.navfoot{margin-top:auto;padding:12px;font-size:12px;color:var(--text-3);line-height:18px;border-top:1px solid var(--line)} .navfoot a{color:var(--text-2)}
.main{flex:1;min-width:0;padding:24px 32px 40px;overflow:hidden}
.crumbs{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--text-3);margin-bottom:12px}
.crumbs a{color:var(--text-2)} .crumbs .sep{color:var(--line-strong)}
.pagehead{display:flex;align-items:flex-start;justify-content:space-between;gap:24px;margin-bottom:20px} .pagehead > div:first-child{min-width:0} .pagehead .h1{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pagehead .sub{color:var(--text-2);margin-top:4px}
.actions{display:flex;gap:8px;align-items:center;flex-shrink:0}

/* buttons */
.btn{display:inline-flex;align-items:center;justify-content:center;gap:8px;height:40px;padding:0 16px;border-radius:var(--radius);font:inherit;font-size:14px;font-weight:600;line-height:20px;border:1px solid transparent;cursor:pointer;text-decoration:none!important;transition:background .15s,border-color .15s,box-shadow .15s;white-space:nowrap}
.btn.sm{height:32px;padding:0 12px;font-size:13px}
.btn.primary{background:var(--primary);color:#fff} .btn.primary:hover{background:var(--primary-hover);color:#fff}
.btn.secondary{background:var(--surface);color:var(--text);border-color:var(--line-strong);box-shadow:var(--shadow-1)} .btn.secondary:hover{background:var(--surface-2);color:var(--text)}
.btn.ghost{background:transparent;color:var(--text-2)} .btn.ghost:hover{background:var(--neutral-soft);color:var(--text)}
.btn.danger{background:var(--surface);color:var(--text-2);border-color:var(--line-strong)} .btn.danger:hover{background:var(--error-soft);color:var(--error);border-color:var(--error-line)}
.btn.link{background:transparent;color:var(--primary);padding:0;height:auto;font-weight:600}
.btn[disabled],.btn.disabled{background:var(--neutral-soft)!important;color:var(--text-3)!important;border-color:var(--line)!important;box-shadow:none;cursor:not-allowed;pointer-events:none}

/* badges */
.badge{display:inline-flex;align-items:center;gap:6px;height:24px;padding:0 8px 0 7px;border-radius:12px;font-size:12px;font-weight:600;line-height:16px;border:1px solid;white-space:nowrap}
.badge .dot{width:7px;height:7px;border-radius:50%;background:currentColor;flex-shrink:0}
.badge.neutral{color:var(--neutral);background:var(--neutral-soft);border-color:var(--neutral-line)}
.badge.info{color:var(--info);background:var(--info-soft);border-color:var(--info-line)}
.badge.warning{color:var(--warning);background:var(--warning-soft);border-color:var(--warning-line)}
.badge.success{color:var(--success);background:var(--success-soft);border-color:var(--success-line)}
.badge.error{color:var(--error);background:var(--error-soft);border-color:var(--error-line)}
.badge.primary{color:var(--primary);background:var(--primary-soft);border-color:var(--primary-line)}
.badge.lg{height:28px;font-size:13px;padding:0 10px 0 9px}
.tag{display:inline-flex;align-items:center;gap:4px;white-space:nowrap;height:22px;padding:0 8px;border-radius:4px;background:var(--neutral-soft);color:var(--text-2);font-size:12px;font-weight:500;border:1px solid var(--neutral-line)}
.tag.changed{background:var(--info-soft);color:var(--info);border-color:var(--info-line)}
.tag.editable{background:var(--warning-soft);color:var(--warning);border-color:var(--warning-line)}
.tag.readonly{background:var(--neutral-soft);color:var(--text-3)}

/* cards & layout */
.card{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius-lg);box-shadow:var(--shadow-1)}
.card-h{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:14px 20px;border-bottom:1px solid var(--line)}
.card-b{padding:20px}
.card-f{padding:12px 20px;border-top:1px solid var(--line);display:flex;justify-content:flex-end;gap:8px;background:var(--surface-2);border-radius:0 0 var(--radius-lg) var(--radius-lg)}
.grid2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px}
.grid3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}
.split{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:24px;align-items:start}
.split-l{display:grid;grid-template-columns:240px minmax(0,1fr);gap:24px;align-items:start}
.stack{display:flex;flex-direction:column;gap:16px} .stack-s{display:flex;flex-direction:column;gap:8px}
.row{display:flex;align-items:center;gap:12px} .row-b{display:flex;align-items:center;justify-content:space-between;gap:12px}
.divider{height:1px;background:var(--line)}
.kv{display:grid;grid-template-columns:180px minmax(0,1fr);gap:8px 16px;font-size:14px}
.kv dt{color:var(--text-3);margin:0} .kv dd{margin:0;font-weight:500}

/* status header */
.steps{display:flex;align-items:center;justify-content:space-between;padding:10px 20px;border:1px solid var(--line);border-top:0;border-radius:0 0 var(--radius-lg) var(--radius-lg);background:var(--surface-2);margin-top:-6px;margin-bottom:20px}
.facts{display:flex;gap:32px;padding:14px 20px;background:var(--surface);border:1px solid var(--line);border-radius:var(--radius-lg)} .facts > div{display:flex;flex-direction:column;gap:2px} .facts .fk{font-size:12px;color:var(--text-3)} .facts .fv{font-size:14px;font-weight:500}
.statusbar{display:flex;align-items:center;gap:16px;padding:14px 20px;background:var(--surface);border:1px solid var(--line);border-radius:var(--radius-lg);box-shadow:var(--shadow-1);position:relative;z-index:1}
.statusbar.has-steps{border-radius:var(--radius-lg) var(--radius-lg) 0 0;margin-bottom:0}
.statusbar .expl{color:var(--text-2);font-size:14px}
.stepper{display:flex;align-items:center;gap:0}
.step{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--text-3);font-weight:500}
.step .n{width:24px;height:24px;border-radius:50%;border:1.5px solid var(--line-strong);display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:600;background:#fff}
.step.done{color:var(--text-2)} .step.done .n{background:var(--success);border-color:var(--success);color:#fff}
.step.current{color:var(--primary);font-weight:600} .step.current .n{background:var(--primary);border-color:var(--primary);color:#fff}
.step{white-space:nowrap} .step-line{width:28px;height:1.5px;background:var(--line-strong);margin:0 8px} .step-line.done{background:var(--success)}

/* tables */
.table{width:100%;border-collapse:collapse;font-size:14px;table-layout:fixed} .table th{white-space:nowrap} .split > *{min-width:0}
.table th{text-align:left;font-size:12px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;color:var(--text-3);padding:10px 16px;border-bottom:1px solid var(--line);background:var(--surface-2)}
.table td{padding:14px 16px;border-bottom:1px solid var(--line);vertical-align:middle}
.table tr:last-child td{border-bottom:0}
.table tr.rowlink:hover td{background:var(--surface-2)}
.table .ref{font-weight:600;white-space:nowrap;color:var(--text);font-family:'IBM Plex Mono',Menlo,monospace;font-size:13px} .table .ref:hover{color:var(--primary)} .table .r{text-align:right} .table td.num{white-space:nowrap}

/* forms */
.field{display:flex;flex-direction:column;gap:6px}
.label{font-size:13px;line-height:18px;font-weight:600;color:var(--text)} .label .req{color:var(--error);margin-left:2px}
.help{font-size:13px;color:var(--text-3)} .errtext{font-size:13px;color:var(--error);display:flex;align-items:center;gap:6px;font-weight:500}
.input{height:40px;padding:0 12px;border:1px solid var(--line-strong);border-radius:var(--radius);background:#fff;font:inherit;font-size:15px;color:var(--text);width:100%;transition:border-color .15s,box-shadow .15s}
.input:hover{border-color:#8F98A6} .input:focus{border-color:var(--focus);box-shadow:0 0 0 3px rgba(23,92,211,.18);outline:none}
.input.invalid{border-color:var(--error);box-shadow:0 0 0 3px rgba(180,35,24,.14)}
.input.ro{background:var(--surface-2);color:var(--text-2);border-color:var(--line)}
textarea.input{height:auto;min-height:96px;padding:10px 12px;resize:vertical}
.select{appearance:none;background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23465060' stroke-width='2'><path d='m6 9 6 6 6-6'/></svg>");background-repeat:no-repeat;background-position:right 10px center;padding-right:36px}
.check{display:flex;gap:10px;align-items:flex-start;font-size:14px;white-space:nowrap} .check input{width:18px;height:18px;margin:2px 0 0;accent-color:var(--primary)}
.fgrid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px 20px}
.fsec{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius-lg);box-shadow:var(--shadow-1)}
.fsec-h{display:flex;align-items:center;gap:12px;padding:16px 20px;border-bottom:1px solid var(--line)}
.fsec-h .h3{flex:1}
.fsec-b{padding:20px}
.fsec.flagged{border-color:var(--warning-line);box-shadow:0 0 0 3px var(--warning-soft)}
.fsec.locked .fsec-b{background:var(--surface-2)}
.secnav{background:var(--surface);border:1px solid var(--line);border-radius:var(--radius-lg);padding:8px;position:sticky;top:0}
.secnav a{display:flex;align-items:center;gap:10px;padding:9px 10px;border-radius:var(--radius);color:var(--text-2);font-size:14px;font-weight:500}
.secnav a:hover{background:var(--neutral-soft);text-decoration:none}
.secnav a.active{background:var(--neutral-soft);color:var(--text);font-weight:600;box-shadow:inset 3px 0 0 var(--primary)}
.secnav .st{margin-left:auto;width:18px;height:18px;border-radius:50%;display:flex;align-items:center;justify-content:center}
.st.ok{background:var(--success);color:#fff} .st.todo{border:1.5px solid var(--line-strong);background:#fff} .st.err{background:var(--error);color:#fff} .st.warn{background:var(--warning);color:#fff}
.progress{height:8px;background:var(--neutral-soft);border-radius:4px;overflow:hidden}
.progress > i{display:block;height:100%;background:var(--success);border-radius:4px;transition:width .4s ease}
.progress.p > i{background:var(--primary)}

/* alerts */
.alert{display:flex;gap:12px;padding:12px 16px;border-radius:var(--radius);border:1px solid;font-size:14px;line-height:20px}
.alert .ai{flex-shrink:0;margin-top:1px} .alert b{font-weight:600}
.alert.info{background:var(--info-soft);border-color:var(--info-line);color:#0F3E8A} .alert.info .ai{color:var(--info)}
.alert.warning{background:var(--warning-soft);border-color:var(--warning-line);color:#6E3500} .alert.warning .ai{color:var(--warning)}
.alert.error{background:var(--error-soft);border-color:var(--error-line);color:#7A1A12} .alert.error .ai{color:var(--error)}
.alert.success{background:var(--success-soft);border-color:var(--success-line);color:#04532F} .alert.success .ai{color:var(--success)}
.alert.neutral{background:var(--surface-2);border-color:var(--line);color:var(--text-2)}

/* documents & verification */
.doc{border:1px solid var(--line);border-radius:var(--radius-lg);background:var(--surface);overflow:hidden}
.doc-h{display:flex;align-items:center;gap:12px;padding:12px 16px}
.doc-ic{width:36px;height:36px;border-radius:6px;background:var(--neutral-soft);display:flex;align-items:center;justify-content:center;color:var(--text-2);flex-shrink:0}
.doc-t{flex:1;min-width:0} .doc-t .name{font-weight:600;font-size:14px;overflow-wrap:anywhere} .doc-t .meta{margin-top:2px}
.doc-f{display:flex;align-items:center;gap:8px;padding:8px 16px;border-top:1px solid var(--line);background:var(--surface-2)}
.ver{border-top:1px solid var(--line);padding:12px 16px;display:flex;gap:12px;align-items:flex-start}
.ver .vi{width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.ver .vt{flex:1;min-width:0}
.ver .vh{display:flex;align-items:center;gap:8px;font-weight:600;font-size:14px}
.ver .vd{font-size:13px;color:var(--text-2);margin-top:2px}
.ver.pending .vi{background:var(--neutral-soft);color:var(--text-2)}
.ver.running .vi{background:var(--info-soft);color:var(--info)}
.ver.verified .vi{background:var(--success-soft);color:var(--success)}
.ver.issues .vi{background:var(--error-soft);color:var(--error)}
.ver.review .vi{background:var(--warning-soft);color:var(--warning)}
.ver.unreadable .vi,.ver.unavailable .vi{background:var(--neutral-soft);color:var(--text-2)}
.ver.failed .vi{background:var(--error-soft);color:var(--error)}
.issue{display:flex;gap:10px;padding:10px 12px;border:1px solid var(--line);border-radius:var(--radius);background:var(--surface-2);font-size:13px;line-height:19px}
.issue .sev{font-size:11px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;padding:1px 6px;border-radius:4px;height:18px;line-height:16px;flex-shrink:0;margin-top:1px}
.sev.high{background:var(--error-soft);color:var(--error);border:1px solid var(--error-line)} .sev.medium{background:var(--warning-soft);color:var(--warning);border:1px solid var(--warning-line)} .sev.low{background:var(--neutral-soft);color:var(--text-2);border:1px solid var(--neutral-line)}
.issue .ev{color:var(--text-3);font-style:italic}
.conf{display:inline-flex;align-items:center;gap:6px;font-size:12px;color:var(--text-3)}
.conf i{display:inline-block;width:48px;height:5px;background:var(--neutral-soft);border-radius:3px;overflow:hidden;vertical-align:middle}
.conf i b{display:block;height:100%;background:var(--text-3)}
.aiband{display:flex;align-items:center;gap:8px;font-size:12px;color:var(--text-3);padding:8px 16px;border-top:1px dashed var(--line);background:#fff}
.spin{width:16px;height:16px;border:2px solid var(--info-line);border-top-color:var(--info);border-radius:50%;animation:spin .9s linear infinite}
.vprog{height:4px;background:var(--info-soft);border-radius:2px;overflow:hidden;margin-top:8px}
.vprog i{display:block;height:100%;width:40%;background:var(--info);border-radius:2px;animation:slide 1.6s ease-in-out infinite}
@keyframes spin{to{transform:rotate(360deg)}} @keyframes slide{0%{transform:translateX(-100%)}100%{transform:translateX(260%)}}
.drop{border:1.5px dashed var(--line-strong);border-radius:var(--radius-lg);padding:28px;text-align:center;background:var(--surface);transition:border-color .15s,background .15s}
.drop:hover{border-color:var(--text-3)} .drop.over{border-color:var(--primary);background:var(--primary-soft);border-style:solid}
.drop .di{width:44px;height:44px;border-radius:50%;background:var(--neutral-soft);display:inline-flex;align-items:center;justify-content:center;color:var(--text-2);margin-bottom:10px}
.upl{display:flex;flex-direction:column;gap:6px;padding:12px 16px;border-top:1px solid var(--line)}
.upl .pb{height:6px;background:var(--neutral-soft);border-radius:3px;overflow:hidden} .upl .pb i{display:block;height:100%;background:var(--primary);width:62%;border-radius:3px}

/* feedback */
.fb{border:1px solid var(--line);border-radius:var(--radius-lg);background:var(--surface);overflow:hidden}
.fb-h{display:flex;align-items:center;gap:10px;padding:12px 16px;border-bottom:1px solid var(--line);background:var(--surface-2)}
.fbi{display:flex;gap:12px;padding:14px 16px;border-bottom:1px solid var(--line)} .fbi:last-child{border-bottom:0}
.fbi .fbn{width:26px;height:26px;border-radius:50%;background:var(--warning-soft);color:var(--warning);border:1px solid var(--warning-line);display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;flex-shrink:0}
.fbi.addressed .fbn{background:var(--info-soft);color:var(--info);border-color:var(--info-line)}
.fbi.resolved .fbn{background:var(--success-soft);color:var(--success);border-color:var(--success-line)}
.fbi .fbt{flex:1;min-width:0}
.fbi .fbtarget{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:4px}
.fbi .fbmsg{font-size:14px;line-height:21px;color:var(--text)} .fbi .fbmeta{margin-top:6px;display:flex;gap:12px;flex-wrap:wrap}
.fbi.resolved .fbmsg{color:var(--text-3)}
.anchor{display:inline-flex;align-items:center;gap:6px;color:var(--primary);font-size:13px;font-weight:600} .anchor:hover{text-decoration:underline}
.inline-fb{display:flex;gap:10px;padding:10px 12px;background:var(--warning-soft);border:1px solid var(--warning-line);border-radius:var(--radius);font-size:13px;line-height:19px;color:#6E3500;margin-bottom:16px}
.inline-fb b{font-weight:600}
.tmpl{display:flex;flex-wrap:wrap;gap:6px} .tmpl button{font:inherit;font-size:13px;height:30px;padding:0 10px;border-radius:15px;border:1px solid var(--line-strong);background:#fff;color:var(--text-2);cursor:pointer} .tmpl button:hover{border-color:var(--text-3);color:var(--text)}

/* diff */
.diff{border:1px solid var(--line);border-radius:var(--radius-lg);overflow:hidden;background:var(--surface)}
.diff-h{display:grid;grid-template-columns:200px minmax(0,1fr) minmax(0,1fr);gap:0;background:var(--surface-2);border-bottom:1px solid var(--line);font-size:12px;font-weight:600;letter-spacing:.04em;text-transform:uppercase;color:var(--text-3)}
.diff-h > div{padding:10px 16px}
.diff-r{display:grid;grid-template-columns:200px minmax(0,1fr) minmax(0,1fr);border-bottom:1px solid var(--line);font-size:14px}
.diff-r:last-child{border-bottom:0} .diff-r > div{padding:12px 16px}
.diff-r .k{color:var(--text-3)} .diff-r.same{color:var(--text-3)} .diff-r.same .k{color:var(--text-3)}
.diff-r.chg .old{text-decoration:line-through;text-decoration-color:var(--line-strong);color:var(--text-3);word-break:break-word}
.diff-r.chg .new{font-weight:600;word-break:break-word}
.diff-r > div{overflow-wrap:anywhere}
.diff-r .cm{font-size:11px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;margin-right:8px;padding:1px 6px;border-radius:4px}
.cm.chg{background:var(--info-soft);color:var(--info)} .cm.add{background:var(--success-soft);color:var(--success)} .cm.rep{background:var(--warning-soft);color:var(--warning)}

/* timeline */
.tl{display:flex;flex-direction:column}
.tli{display:grid;grid-template-columns:24px minmax(0,1fr);gap:12px;padding-bottom:20px;position:relative}
.tli:before{content:"";position:absolute;left:11px;top:24px;bottom:0;width:1.5px;background:var(--line)}
.tli:last-child:before{display:none}
.tli .tdot{width:24px;height:24px;border-radius:50%;background:var(--surface);border:1.5px solid var(--line-strong);display:flex;align-items:center;justify-content:center;color:var(--text-2)}
.tli .tdot.p{background:var(--primary);border-color:var(--primary);color:#fff} .tli .tdot.s{background:var(--success);border-color:var(--success);color:#fff} .tli .tdot.w{background:var(--warning);border-color:var(--warning);color:#fff} .tli .tdot.i{background:var(--info);border-color:var(--info);color:#fff}
.tli .tt{font-size:14px;font-weight:600} .tli .td{font-size:13px;color:var(--text-2);margin-top:2px} .tli .tm{margin-top:4px}
.rev{display:grid;grid-template-columns:auto minmax(0,1fr) auto;align-items:center;gap:12px;padding:12px 16px;border:1px solid var(--line);border-radius:var(--radius);background:var(--surface)} .rev .rmid{display:flex;align-items:center;gap:8px;flex-wrap:wrap;min-width:0} .rev .racts{display:flex;gap:6px;white-space:nowrap}
.rev.current{border-color:var(--info-line);background:var(--info-soft)}
.rev .rn{font-weight:700;font-size:14px;white-space:nowrap} .rev .rmid .small{white-space:nowrap}

/* states */
.empty{text-align:center;padding:40px 24px;color:var(--text-2)}
.empty .ei{width:48px;height:48px;border-radius:50%;background:var(--neutral-soft);display:inline-flex;align-items:center;justify-content:center;color:var(--text-3);margin-bottom:12px}
.empty .et{font-weight:600;color:var(--text);font-size:15px} .empty .ed{font-size:14px;margin-top:4px}
.skel{background:linear-gradient(90deg,#EEF0F3 25%,#F6F7F9 50%,#EEF0F3 75%);background-size:200% 100%;animation:shimmer 1.4s infinite;border-radius:4px;height:14px}
@keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}
.toast{display:flex;gap:12px;align-items:flex-start;padding:12px 14px;background:#1B2430;color:#fff;border-radius:var(--radius-lg);box-shadow:var(--shadow-2);width:360px;font-size:14px;line-height:20px}
.toast .ti{color:#6EE7A0;flex-shrink:0;margin-top:1px} .toast .tt{font-weight:600} .toast .tb{color:#C5CBD3;font-size:13px}
.dialog-bg{position:absolute;inset:0;background:rgba(16,24,40,.45);display:flex;align-items:center;justify-content:center;z-index:5}
.dialog{width:520px;background:#fff;border-radius:var(--radius-lg);box-shadow:0 20px 48px rgba(16,24,40,.28);overflow:hidden}
.dialog-h{padding:20px 24px 8px} .dialog-b{padding:8px 24px 20px;color:var(--text-2);font-size:14px;line-height:21px} .dialog-f{padding:12px 24px;background:var(--surface-2);border-top:1px solid var(--line);display:flex;justify-content:flex-end;gap:8px}
.notif{position:absolute;right:24px;top:56px;width:380px;background:#fff;border:1px solid var(--line);border-radius:var(--radius-lg);box-shadow:var(--shadow-2);z-index:4;overflow:hidden}
.ni{display:flex;gap:12px;padding:12px 16px;border-bottom:1px solid var(--line)} .ni:last-child{border-bottom:0} .ni.unread{background:var(--info-soft)}
.ni .nd{width:8px;height:8px;border-radius:50%;background:var(--info);margin-top:7px;flex-shrink:0} .ni .nt{font-size:14px;font-weight:600} .ni .nb,.ni .nt{overflow-wrap:anywhere} .ni .nb{font-size:13px;color:var(--text-2)}
.kpi{padding:16px 20px} .kpi .kn{font-size:28px;font-weight:600;line-height:34px;letter-spacing:-.01em} .kpi .kl{font-size:13px;color:var(--text-2);margin-top:2px}
.tabs{display:flex;gap:4px;border-bottom:1px solid var(--line);margin-bottom:20px}
.tab{white-space:nowrap;padding:10px 14px;font-size:14px;font-weight:500;color:var(--text-2);border-bottom:2px solid transparent;margin-bottom:-1px}
.tab.active{color:var(--primary);border-bottom-color:var(--primary);font-weight:600} .tab:hover{color:var(--text);text-decoration:none}
.tab .cnt{margin-left:6px;font-size:12px;background:var(--neutral-soft);padding:0 6px;border-radius:9px;color:var(--text-2)}
.chk{display:flex;align-items:center;gap:10px;padding:10px 0;border-bottom:1px solid var(--line);font-size:14px} .chk:last-child{border-bottom:0}
.chk .st{width:20px;height:20px;border-radius:50%;display:flex;align-items:center;justify-content:center;flex-shrink:0}
.demo{border:1px dashed var(--line-strong);border-radius:var(--radius);padding:10px 12px;display:flex;align-items:center;gap:12px;background:var(--surface);color:var(--text)}
.demo:hover{background:var(--surface-2);text-decoration:none}
.demo .dr{font-size:12px;color:var(--text-3)}
.fade{animation:fade .35s ease-out} @keyframes fade{from{opacity:0;transform:translateY(4px)}to{opacity:1;transform:none}}
.hl{animation:hl 1.6s ease-out} @keyframes hl{0%{box-shadow:0 0 0 4px var(--warning-soft),0 0 0 6px var(--warning-line)}100%{box-shadow:0 0 0 3px var(--warning-soft)}}
@media (prefers-reduced-motion:reduce){*{animation-duration:.001s!important;animation-iteration-count:1!important;transition-duration:.001s!important}}
"""
CSS += r"""
.sbar{display:flex;height:10px;border-radius:5px;overflow:hidden;background:var(--neutral-soft)} .sbar i{display:block;height:100%} .legend{display:flex;gap:20px;flex-wrap:wrap;font-size:13px;color:var(--text-2)} .legend.v{flex-direction:column;gap:6px} .legend span{display:inline-flex;align-items:center;gap:6px} .legend i{width:10px;height:10px;border-radius:2px;display:inline-block}
/* stat strip (replaces KPI card rows) */
.strip{display:flex;align-items:stretch;background:var(--surface);border:1px solid var(--line);border-radius:var(--radius-lg);box-shadow:var(--shadow-1);overflow:hidden}
.strip > a,.strip > div{flex:1;padding:14px 20px 12px;display:flex;flex-direction:column;gap:1px;color:inherit;border-right:1px solid var(--line);text-decoration:none!important;transition:background .15s}
.strip > a:hover{background:var(--surface-2)}
.strip > :last-child{border-right:0}
.strip .sn{font-size:26px;line-height:32px;font-weight:600;letter-spacing:-.01em}
.strip .sk{font-size:12px;font-weight:600;color:var(--text-3);letter-spacing:.06em;text-transform:uppercase}
.strip .sl{font-size:13px;color:var(--text-2)}
.strip .hot .sk{color:var(--primary)}
.eyebrow{font-size:12px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--text-3)}
.eyebrow.p{color:var(--primary)}
"""

CSS += r"""
.sidenav.collapsed{width:64px;padding:16px 8px;align-items:center}
.sidenav.collapsed .navlabel,.sidenav.collapsed .navitem span,.sidenav.collapsed .navfoot{display:none}
.sidenav.collapsed .navitem{width:44px;height:44px;justify-content:center;padding:0}
.sidenav.collapsed .navitem .cnt{display:none}
.tablet .sidenav{display:none} .tablet .root{width:1024px} .tablet .split,.tablet .split-l{grid-template-columns:minmax(0,1fr)} .tablet .main{padding:20px 24px 32px} .tablet .pagehead{flex-direction:column;align-items:stretch} .tablet .actions{justify-content:flex-start}
.qgroup{display:flex;align-items:center;gap:10px;padding:10px 16px;background:var(--surface-2);border-bottom:1px solid var(--line);font-size:13px;font-weight:600;color:var(--text-2)}
.qgroup .cnt{font-size:12px;background:#fff;border:1px solid var(--line);padding:0 6px;border-radius:9px;color:var(--text-2)}
.table tr.hot td{background:#FFFBF2}
.drawer-bg{position:absolute;inset:84px 0 0 0;background:rgba(16,24,40,.35);z-index:5;display:flex;justify-content:flex-end}
.drawer{width:420px;background:#fff;border-left:1px solid var(--line);box-shadow:-8px 0 24px rgba(16,24,40,.12);display:flex;flex-direction:column;height:auto;align-self:flex-start;border-radius:0 0 0 10px}
.drawer-h{padding:18px 24px;border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:space-between}
.drawer-b{padding:20px 24px;display:flex;flex-direction:column;gap:16px;flex:1}
.drawer-f{padding:14px 24px;border-top:1px solid var(--line);display:flex;justify-content:flex-end;gap:8px;background:var(--surface-2)}
.radio{display:flex;gap:10px;align-items:flex-start;padding:10px 12px;border:1px solid var(--line);border-radius:var(--radius)} .radio input{margin:3px 0 0;accent-color:var(--primary)} .radio.on{border-color:var(--info-line);background:var(--info-soft)}
.role{display:inline-flex;align-items:center;height:22px;padding:0 8px;border-radius:4px;font-size:12px;font-weight:600;border:1px solid}
.role.operator{color:var(--text-2);background:var(--neutral-soft);border-color:var(--neutral-line)} .role.officer{color:var(--info);background:var(--info-soft);border-color:var(--info-line)} .role.admin{color:var(--text);background:var(--neutral-soft);border-color:var(--line-strong)}
.datefield{position:relative} .datefield .input{padding-right:40px} .datefield svg{position:absolute;right:12px;top:11px;color:var(--text-3);pointer-events:none}
.root{max-width:100%}
/* landing */
.land{background:#fff;color:var(--text)}
.land .wrap{max-width:1080px;margin:0 auto;padding:0 32px}
.land-hero{padding:72px 0 56px;border-bottom:1px solid var(--line)}
.land h1{font-size:40px;line-height:48px;font-weight:600;letter-spacing:-.015em;max-width:720px}
.land .lead{font-size:18px;line-height:28px;color:var(--text-2);max-width:640px;margin-top:16px}
.land-sec{padding:56px 0;border-bottom:1px solid var(--line)}
.land h2{font-size:24px;line-height:32px;font-weight:600;margin-bottom:24px}
.hiw{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:32px}
.hiw .n{font-family:'IBM Plex Mono',monospace;font-size:13px;color:var(--primary);font-weight:500;margin-bottom:10px}
.hiw .t{font-weight:600;font-size:16px;margin-bottom:6px} .hiw .d{font-size:14px;line-height:21px;color:var(--text-2)}
.need{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px 32px}
.need > div{display:flex;gap:12px;align-items:flex-start;font-size:15px;line-height:22px;padding:12px 0;border-bottom:1px solid var(--line)} .need > div > div{display:block}
.land-foot{padding:32px 0;font-size:13px;color:var(--text-3);display:flex;gap:24px;flex-wrap:wrap}
.land-foot a{color:var(--text-2)}
"""

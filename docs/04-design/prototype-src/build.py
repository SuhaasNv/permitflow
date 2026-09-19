import json, os, re, datetime
import screens_operator as so, screens_officer as sf, screens_misc as sm
from lib import CSS, FONT

ROWS = [
 ('Foundations — tokens, type, components, states', [('DesignSystem.dc.html', sm.design_system, 1440, 2520, False)]),
 ('Operator — apply and submit (UC1-A)', [
   ('Landing.dc.html', sm.landing, 1280, 1720, True),
   ('Main.dc.html', so.login, 1280, 760, True),
   ('OperatorDashboard.dc.html', so.op_dashboard, 1280, 1160, True),
   ('ApplicationForm.dc.html', so.app_form, 1280, 1420, True),
   ('Documents.dc.html', so.documents, 1280, 1560, True),
   ('TabletDocuments.dc.html', sm.tablet_documents, 1024, 1700, True),
   ('ReviewSubmit.dc.html', so.review_submit, 1280, 1460, True),
   ('Submitted.dc.html', so.submitted, 1280, 900, True)]),
 ('Operator — respond to feedback and resubmit (UC1-B, UC1-C)', [
   ('OperatorApplication.dc.html', so.op_application, 1280, 2560, True),
   ('OperatorHistory.dc.html', so.op_history, 1280, 1160, True),
   ('MobileDashboard.dc.html', sm.mobile_dashboard, 390, 844, True),
   ('MobileApplication.dc.html', sm.mobile_application, 390, 844, True)]),
 ('Officer — review, feedback, resubmission, compare, audit (UC2)', [
   ('OfficerQueue.dc.html', sf.queue, 1280, 1120, True),
   ('NotificationsPanel.dc.html', sf.notifications_panel, 420, 480, False),
   ('OfficerReview.dc.html', sf.review, 1280, 2440, True),
   ('DialogRequestResubmission.dc.html', sf.dialog_request, 640, 560, False),
   ('OfficerResubmission.dc.html', sf.resubmission, 1280, 1480, True),
   ('OfficerCompare.dc.html', sf.compare, 1280, 1180, True),
   ('OfficerCompareNavCollapsed.dc.html', sf.compare_collapsed, 1280, 1180, True),
   ('OfficerHistory.dc.html', sf.audit, 1280, 2000, True)]),
 ('Admin — oversight and user management (E4)', [('AdminOverview.dc.html', sm.admin, 1280, 1160, True),('AdminUsers.dc.html', sm.admin_users, 1280, 1000, True)]),
]
TITLES = {'Main.dc.html':'Login','OperatorDashboard.dc.html':'Operator dashboard','ApplicationForm.dc.html':'Application form (draft)','Documents.dc.html':'Documents & AI checks','ReviewSubmit.dc.html':'Review & submit','Submitted.dc.html':'Submitted','OperatorApplication.dc.html':'Respond to feedback (resubmission)','OperatorHistory.dc.html':'History (operator)','MobileDashboard.dc.html':'Phone · dashboard','MobileApplication.dc.html':'Phone · respond','OfficerQueue.dc.html':'Review queue','OfficerReview.dc.html':'Review workspace (Under Review)','OfficerResubmission.dc.html':'Resubmission review (Rev 2, Under Review)','OfficerCompare.dc.html':'Compare revisions','OfficerHistory.dc.html':'History & audit','AdminOverview.dc.html':'Admin overview','DesignSystem.dc.html':'Design system','NotificationsPanel.dc.html':'Notifications panel','DialogRequestResubmission.dc.html':'Dialog · request resubmission','Landing.dc.html':'Landing page (public)','TabletDocuments.dc.html':'Tablet 1024 · documents','OfficerCompareNavCollapsed.dc.html':'Compare · navigation collapsed','AdminUsers.dc.html':'Admin users (add, change role, deactivate)'}

os.makedirs('project', exist_ok=True); os.makedirs('static', exist_ok=True)
MEASURED = json.load(open('heights.json')) if os.path.exists('heights.json') else {}
boards, order, notes = {}, [], {}
y = 0
for ri,(title, screens) in enumerate(ROWS):
    x = 0; maxh = 0
    notes[f'row{ri}'] = {'x':0,'y':y-260,'text':title,'kind':'title1','maxW':max(2000, sum(w+80 for _,_,w,_,_ in screens))}
    for name, fn, w, h, inter in screens:
        html = fn()
        html = html.replace(' — ',' · ').replace('—',' · ')
        if name in MEASURED and not name.startswith('Mobile'):
            mh = MEASURED[name]
            html = re.sub(r'height: \d+px; position: relative;', f'height: {mh}px; position: relative;', html, count=1)
            html = re.sub(r'"height":\d+\}', f'"height":{mh}}}', html, count=1)
            h = mh
        open(f'project/{name}','w').write(html)
        # static variant for screenshots
        helmet = re.search(r'<helmet>(.*?)</helmet>', html, re.S).group(1)
        inner = re.search(r'</helmet>(.*?)</x-dc>', html, re.S).group(1)
        inner = re.sub(r'href="([A-Za-z]+)\.dc\.html"', r'href="\1.html"', inner)
        measure = os.environ.get('MEASURE')=='1' and not name.startswith('Mobile')
        sinner = re.sub(r'height: \d+px; position: relative;', 'height:auto; min-height:0; position: relative;', inner, count=1) if measure else inner
        static = f'<!doctype html><html lang="en"><head><meta charset="utf-8"><title>{TITLES[name]}</title>{helmet}<style>html,body{{background:#E9EBEE}} .root{{min-height:100%}}</style></head><body style="padding:0">{sinner}</body></html>'
        open(f'static/{name.replace(".dc.html",".html")}','w').write(static)
        boards[name] = {'x':x,'y':y,'w':w,'h':h,'title':TITLES[name]}
        if inter: boards[name]['is_interactive'] = True
        order.append(name)
        x += w + 80; maxh = max(maxh, h)
    y += maxh + 120 + 300
# Main first in order
order.remove('Main.dc.html'); order.insert(0,'Main.dc.html')
# canvas row titles: no em dashes
for n in notes.values(): n['text']=n['text'].replace(' — ',': ')
canvas = {'v':3,'createdOnFiles':{'v':1,'at':datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')},'title':'PermitFlow Design','launch':{'view':'canvas'},'pages':[],'boards':boards,'order':order,'notes':notes,'designSystems':[]}
json.dump(canvas, open('project/canvas.json','w'), indent=1)
print(len(boards),'boards')

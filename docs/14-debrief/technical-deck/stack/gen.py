"""Writes stack.html from the icon files. Logos: Simple Icons (simple-icons@16.33.0), for identification only.
Render: node ../story/shoot.cjs stack.html stack.png "THE STACK" "NN / TT" (from this folder)."""
import os, re
here = os.path.dirname(os.path.abspath(__file__))
COL = {'react':'#149ECA','typescript':'#3178C6','vite':'#646CFF','tailwindcss':'#06B6D4','reactquery':'#FF4154',
       'reacthookform':'#EC5990','zod':'#3E67B1','python':'#3776AB','fastapi':'#009688','pydantic':'#E92063',
       'sqlalchemy':'#D71F00','postgresql':'#4169E1','openai':'#1B2430','langchain':'#1C3C3C','pytest':'#0A9EDC',
       'vitest':'#729B1B','playwright':'#2EAD33','github':'#181717','githubactions':'#2088FF','docker':'#2496ED',
       'railway':'#0B0D0E','prometheus':'#E6522C','grafana':'#F46800','telegram':'#26A5E4','jsonwebtokens':'#1B2430'}
def icon(slug):
    svg = open(os.path.join(here, 'icons', slug + '.svg')).read()
    svg = re.sub(r'<title>.*?</title>', '', svg)
    return svg.replace('<svg ', f'<svg fill="{COL[slug]}" ', 1)
GROUPS = [
 ('01 · FRONTEND', [('react','React 19'),('typescript','TypeScript'),('vite','Vite'),('tailwindcss','Tailwind CSS'),('reactquery','TanStack Query'),('reacthookform','React Hook Form'),('zod','Zod')], [], 'Live status, typed end to end.'),
 ('02 · BACKEND', [('python','Python 3.12'),('fastapi','FastAPI'),('pydantic','Pydantic v2'),('sqlalchemy','SQLAlchemy 2')], ['Alembic'], 'Validates requests and AI output.'),
 ('03 · DATA', [('postgresql','PostgreSQL')], [], 'One transaction, full audit.'),
 ('04 · AI', [('openai','OpenAI gpt-4.1-mini'),('langchain','LangSmith')], ['Mock provider'], 'Advisory, swappable, traced.'),
 ('05 · TESTING', [('pytest','pytest'),('vitest','Vitest'),('playwright','Playwright')], ['axe'], 'Every layer, a real browser.'),
 ('06 · DELIVERY', [('github','GitHub'),('githubactions','GitHub Actions'),('docker','Docker'),('railway','Railway')], ['GHCR'], 'Build once, approve to ship.'),
 ('07 · OBSERVABILITY', [('prometheus','Prometheus'),('grafana','Grafana'),('telegram','Telegram')], [], 'Health, cost, alerts.'),
 ('08 · SECURITY', [('jsonwebtokens','JWT')], ['Argon2id','gitleaks'], 'Checked on every request.'),
]
cells = []
for label, logos, extras, why in GROUPS:
    chips = ''.join(f'<span class="t"><span class="lg">{icon(s)}</span>{n}</span>' for s, n in logos)
    chips += ''.join(f'<span class="t x">{e}</span>' for e in extras)
    cells.append(f'<div class="g"><div class="lab">{label}</div><div class="chips">{chips}</div><div class="why">{why}</div></div>')
html = f'''<!doctype html><html><head><meta charset="utf-8"><style>
@font-face {{ font-family:'Public Sans'; font-weight:400 700; src:url('../../../../frontend/public/fonts/public-sans-normal-400-latin.woff2') format('woff2'); }}
@font-face {{ font-family:'Instrument Serif'; src:url('../../../../frontend/public/fonts/instrument-serif-normal-400-latin.woff2') format('woff2'); }}
@font-face {{ font-family:'IBM Plex Mono'; src:url('../../../../frontend/public/fonts/ibm-plex-mono-normal-400-latin.woff2') format('woff2'); }}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:1920px;height:1080px;background:#F4F5F7;font-family:'Public Sans',sans-serif;color:#1B2430;overflow:hidden;position:relative}}
.kicker{{position:absolute;left:120px;top:88px;font-size:22px;font-weight:700;letter-spacing:.09em;color:#616C7A}}
.page{{position:absolute;right:120px;top:90px;font-family:'IBM Plex Mono',monospace;font-size:20px;color:#616C7A}}
.head{{position:absolute;left:120px;top:136px;width:1620px;font-family:'Instrument Serif',serif;font-size:58px;line-height:1.08}}
.grid{{position:absolute;left:120px;top:290px;width:1680px;display:grid;grid-template-columns:repeat(4,1fr);column-gap:44px;row-gap:48px}}
.g{{border-top:2px solid #1B2430;padding-top:16px;display:flex;flex-direction:column;min-height:280px}}
.lab{{font-family:'IBM Plex Mono',monospace;font-size:16px;letter-spacing:.09em;color:#616C7A}}
.chips{{margin-top:16px;display:flex;flex-wrap:wrap;gap:10px}}
.t{{display:inline-flex;align-items:center;gap:9px;background:#fff;border:1.5px solid #D9DEE5;border-radius:10px;padding:7px 12px 7px 8px;font-size:18px;font-weight:600}}
.t.x{{padding:7px 12px;font-weight:500;color:#465060;border-style:dashed}}
.lg{{width:28px;height:28px;display:inline-flex;align-items:center;justify-content:center}}
.lg svg{{width:24px;height:24px}}
.why{{margin-top:auto;padding-top:16px;font-size:22px;font-weight:600;color:#1B2430}}
.foot{{position:absolute;left:120px;bottom:52px;font-size:17px;color:#616C7A}}
</style></head><body>
<div class="kicker">KICKER</div><div class="page">PAGE</div>
<div class="head">The stack, grouped by job.</div>
<div class="grid">{''.join(cells)}</div>
<div class="foot">ADR-009 (stack and delivery) · pyproject.toml, package.json · logos from Simple Icons, for identification only</div>
</body></html>'''
open(os.path.join(here, 'stack.html'), 'w').write(html)

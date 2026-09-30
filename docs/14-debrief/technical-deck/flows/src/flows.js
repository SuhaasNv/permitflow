/* Flowchart renderer for the PermitFlow technical deck. One spec per slide, drawn at 1920 x 1080. */

// The product's own font files, relative to this folder (docs/14-debrief/technical-deck/flows/src).
const FONT_DIR = '../../../../../frontend/public/fonts/'

const ACTORS = {
  browser: { label: 'Browser', c: '#175cd3', soft: '#eef4ff', line: '#b2ccfa' },
  api: { label: 'API', c: '#a8192a', soft: '#fbedee', line: '#efb8be' },
  db: { label: 'Database', c: '#067647', soft: '#ecfdf3', line: '#a6e9c4' },
  storage: { label: 'File storage', c: '#0e7490', soft: '#ecfeff', line: '#a5e7f3' },
  task: { label: 'Background task', c: '#475467', soft: '#f2f4f7', line: '#d0d5dd' },
  rules: { label: 'Our rules (code)', c: '#9a4a00', soft: '#fff6e5', line: '#f5cf86' },
  openai: { label: 'OpenAI', c: '#6941c6', soft: '#f4f0ff', line: '#d6c9fb' },
  officer: { label: 'Officer', c: '#1b2430', soft: '#f2f4f7', line: '#aeb6c2' },
}

// Grid: six columns, two rows.
const COL_X = (i) => 70 + i * 304
const NODE_W = 262
const NODE_H = 190
const ROW = {
  A: { head: 146, top: 196 },
  B: { head: 526, top: 576 },
}
const PILL_GAP = 40

const esc = (s) =>
  String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

function css() {
  return `
  @font-face { font-family: 'Public Sans'; font-weight: 400 700; src: url('${FONT_DIR}public-sans-normal-400-latin.woff2') format('woff2'); }
  @font-face { font-family: 'IBM Plex Mono'; font-weight: 400; src: url('${FONT_DIR}ibm-plex-mono-normal-400-latin.woff2') format('woff2'); }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { width: 1920px; height: 1080px; background: #ffffff; }
  body { font-family: 'Public Sans', system-ui, sans-serif; color: #1b2430; position: relative; overflow: hidden; }
  .title { position: absolute; left: 70px; top: 42px; font-size: 46px; font-weight: 700; letter-spacing: -0.02em; }
  .title .brand { color: #a8192a; }
  .sub { position: absolute; left: 70px; top: 104px; font-size: 21px; color: #465060; }
  .legend { position: absolute; right: 68px; top: 46px; width: 760px; display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 10px 22px; font-size: 15.5px; color: #465060; }
  .legend .item { display: flex; align-items: center; gap: 8px; }
  .legend .sw { width: 14px; height: 14px; border-radius: 4px; }
  .legend .stop { border: 1.5px solid #f4b7b1; background: #fef3f2; color: #b42318; font-weight: 700; border-radius: 6px; padding: 1px 8px; font-size: 13.5px; }
  .legend .diam { width: 12px; height: 12px; transform: rotate(45deg); border: 2px solid #465060; }
  .phase { position: absolute; left: 70px; height: 34px; display: flex; align-items: center; gap: 14px; }
  .phase .n { width: 34px; height: 34px; border-radius: 50%; background: #1b2430; color: #fff; font-weight: 700; font-size: 18px; display: flex; align-items: center; justify-content: center; flex: none; }
  .phase .t { font-size: 25px; font-weight: 700; line-height: 34px; }
  .phase .s { font-size: 17px; line-height: 34px; color: #616c7a; font-family: 'IBM Plex Mono', monospace; }
  .node { position: absolute; width: ${NODE_W}px; height: ${NODE_H}px; background: #fff; border: 1.5px solid; border-top-width: 6px; border-radius: 12px; padding: 12px 15px 10px; display: flex; flex-direction: column; overflow: hidden; }
  .node.check { border-width: 2px; border-top-width: 6px; }
  .node.done { background: #ecfdf3; border-color: #067647; }
  .tag { font-size: 12.5px; font-weight: 700; letter-spacing: 0.09em; text-transform: uppercase; display: flex; align-items: center; gap: 7px; }
  .tag .d { width: 9px; height: 9px; transform: rotate(45deg); border: 2px solid currentColor; }
  .ntitle { font-size: 20px; font-weight: 650; line-height: 1.22; margin-top: 5px; letter-spacing: -0.01em; }
  .detail { font-size: 15px; line-height: 1.36; color: #465060; margin-top: 5px; }
  .file { margin-top: auto; font-family: 'IBM Plex Mono', monospace; font-size: 12.5px; color: #616c7a; padding-top: 4px; }
  .pill { position: absolute; width: ${NODE_W}px; border: 1.5px solid; border-radius: 10px; padding: 8px 13px; font-size: 14.5px; line-height: 1.32; }
  .pill.err { background: #fef3f2; border-color: #f4b7b1; color: #912018; }
  .pill.err b { color: #b42318; }
  .pill.status { background: #f2f4f7; border-color: #d0d5dd; color: #344054; }
  .pill.info { background: #eef4ff; border-color: #b2ccfa; color: #1849a9; }
  .pill.store { background: #ecfdf3; border-color: #a6e9c4; color: #05603a; }
  .pill b { font-weight: 700; font-size: 16px; margin-right: 6px; }
  .banner { position: absolute; left: 70px; top: 900px; width: 1780px; height: 96px; background: #f8f9fb; border: 1.5px solid #dde1e7; border-radius: 12px; display: flex; }
  .banner .f { flex: 1; padding: 14px 22px; border-left: 1.5px solid #dde1e7; }
  .banner .f:first-child { border-left: 0; }
  .banner .k { font-size: 13px; font-weight: 700; letter-spacing: 0.09em; text-transform: uppercase; color: #a8192a; }
  .banner .v { font-size: 16px; line-height: 1.35; margin-top: 4px; color: #1b2430; }
  .footer { position: absolute; left: 70px; right: 70px; top: 1036px; display: flex; justify-content: space-between; font-size: 15px; color: #616c7a; }
  svg.edges { position: absolute; left: 0; top: 0; }
  .elabel { font-size: 13.5px; font-weight: 700; paint-order: stroke; stroke: #fff; stroke-width: 5px; }
  `
}

function nodeBox(n) {
  const x = COL_X(n.col)
  const y = ROW[n.row].top
  return { x, y, w: NODE_W, h: NODE_H }
}

function anchor(b, side) {
  if (side === 'r') return { x: b.x + b.w, y: b.y + b.h / 2 }
  if (side === 'l') return { x: b.x, y: b.y + b.h / 2 }
  if (side === 'b') return { x: b.x + b.w / 2, y: b.y + b.h }
  return { x: b.x + b.w / 2, y: b.y }
}

function render(spec) {
  const boxes = {}
  let html = `<style>${css()}</style>`
  html += `<div class="title"><span class="brand">PermitFlow:</span> ${esc(spec.title)}</div>`
  html += `<div class="sub">${esc(spec.sub)}</div>`

  // Legend
  html += '<div class="legend">'
  for (const a of spec.actors) {
    const A = ACTORS[a]
    html += `<div class="item"><span class="sw" style="background:${A.c}"></span>${esc(A.label)}</div>`
  }
  html += `<div class="item"><span class="diam"></span>Check: yes continues</div>`
  html += `<div class="item"><span class="stop">4xx</span>request stops here</div>`
  html += '</div>'

  for (const [key, p] of Object.entries(spec.phases)) {
    html += `<div class="phase" style="top:${ROW[key].head}px"><span class="n">${p.n}</span><span class="t">${esc(p.t)}</span><span class="s">${esc(p.s)}</span></div>`
  }

  const edges = []
  const pills = []
  for (const n of spec.nodes) {
    const b = nodeBox(n)
    boxes[n.id] = b
    const A = ACTORS[n.actor]
    const cls = ['node', n.check ? 'check' : '', n.done ? 'done' : ''].join(' ')
    const bg = n.check ? A.soft : n.done ? '#ecfdf3' : '#fff'
    const border = n.check ? A.c : n.done ? '#067647' : A.line
    html += `<div class="${cls}" data-id="${n.id}" style="left:${b.x}px;top:${b.y}px;background:${bg};border-color:${border};border-top-color:${n.done ? '#067647' : A.c}">`
    html += `<div class="tag" style="color:${n.done ? '#067647' : A.c}">${n.check ? '<span class="d"></span>' : ''}${esc(n.step)} · ${esc(n.tagLabel || A.label)}</div>`
    html += `<div class="ntitle">${esc(n.title)}</div>`
    if (n.detail) html += `<div class="detail">${esc(n.detail).replace(/\n/g, '<br>')}</div>`
    if (n.file) html += `<div class="file">${esc(n.file)}</div>`
    html += '</div>'
    if (n.pill) pills.push({ node: n, b })
  }

  for (const { node, b } of pills) {
    const p = node.pill
    const y = b.y + b.h + PILL_GAP
    const code = p.code ? `<b>${esc(p.code)}</b>` : ''
    html += `<div class="pill ${p.kind || 'err'}" style="left:${b.x}px;top:${y}px">${code}${esc(p.text)}</div>`
    const color = (p.kind || 'err') === 'err' ? '#b42318' : p.kind === 'store' ? '#067647' : '#616c7a'
    edges.push({
      pts: [
        { x: b.x + b.w / 2, y: b.y + b.h },
        { x: b.x + b.w / 2, y: y },
      ],
      color,
      dashed: p.kind === 'store',
      label: p.label ?? (node.check ? 'no' : ''),
      labelAt: 'mid-right',
      head: p.kind !== 'store',
    })
  }

  for (const e of spec.edges) {
    const a = boxes[e.from]
    const b = boxes[e.to]
    const p0 = anchor(a, e.fs || 'r')
    const p1 = anchor(b, e.ts || 'l')
    let pts
    if (e.via) pts = [p0, ...e.via(p0, p1), p1]
    else pts = [p0, p1]
    edges.push({ pts, color: '#465060', label: e.label || '', labelAt: 'mid-top', head: true })
  }

  let svg = `<svg class="edges" width="1920" height="1080" viewBox="0 0 1920 1080">
    <defs>
      <marker id="h-465060" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#465060"/></marker>
      <marker id="h-b42318" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#b42318"/></marker>
      <marker id="h-616c7a" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#616c7a"/></marker>
    </defs>`
  for (const e of edges) {
    const d = e.pts.map((p, i) => `${i ? 'L' : 'M'}${p.x},${p.y}`).join(' ')
    const marker = e.head ? `marker-end="url(#h-${e.color.slice(1)})"` : ''
    svg += `<path d="${d}" fill="none" stroke="${e.color}" stroke-width="2.4" ${e.dashed ? 'stroke-dasharray="6 5"' : ''} ${marker} stroke-linejoin="round"/>`
    if (e.label) {
      const [p, q] = e.pts.length === 2 ? e.pts : [e.pts[e.pts.length - 2], e.pts[e.pts.length - 1]]
      let lx = (p.x + q.x) / 2
      let ly = (p.y + q.y) / 2
      let anchorAttr = 'middle'
      if (e.labelAt === 'mid-right') {
        lx += 10
        ly += 5
        anchorAttr = 'start'
      } else {
        ly -= 9
      }
      svg += `<text class="elabel" x="${lx}" y="${ly}" text-anchor="${anchorAttr}" fill="${e.color}">${esc(e.label)}</text>`
    }
  }
  svg += '</svg>'

  // Edges under the nodes so arrowheads meet the borders cleanly.
  html = html.replace('<div class="legend">', `${svg}<div class="legend">`)

  html += '<div class="banner">'
  for (const f of spec.banner) html += `<div class="f"><div class="k">${esc(f.k)}</div><div class="v">${esc(f.v)}</div></div>`
  html += '</div>'
  html += `<div class="footer"><span>PermitFlow · How it works · ${esc(spec.part)}</span><span>Code on main (v0.3.0) · file paths under backend/app and frontend/src</span></div>`
  document.body.innerHTML = html
}

// Connector helpers
const RETURN = (p0, p1) => [
  { x: 1888, y: p0.y },
  { x: 1888, y: 512 },
  { x: 36, y: 512 },
  { x: 36, y: p1.y },
]

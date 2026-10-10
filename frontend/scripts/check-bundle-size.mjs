// The JavaScript a first visit loads must stay under 250 KB gzipped (US-087, NFR-013). The officer and administrator
// screens are lazy chunks (app/router.tsx), so the budget measures what the first paint needs: the entry chunk and
// every chunk it imports statically, found through dist/.vite/manifest.json. Chunks loaded later by a dynamic
// import are not in that figure; the total of every chunk is printed for information only. CSS is not counted.
// Run after `vite build`; exits non-zero when the first load is over the limit.
import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { gzipSync } from 'node:zlib'

const LIMIT = 250 * 1024
const dist = join(process.cwd(), 'dist')
let manifest
try {
  manifest = JSON.parse(readFileSync(join(dist, '.vite', 'manifest.json'), 'utf8'))
} catch {
  console.error('no dist/.vite/manifest.json; run the build first (build.manifest is on in vite.config.ts)')
  process.exit(2)
}

const gzipped = (file) => gzipSync(readFileSync(join(dist, file)), { level: 9 }).length
const kb = (n) => `${(n / 1024).toFixed(0)} KB`

const entryKey = Object.keys(manifest).find((key) => manifest[key].isEntry)
if (!entryKey) {
  console.error('no entry chunk in the manifest')
  process.exit(2)
}

// The entry and everything it imports statically, each file once.
const firstLoad = new Set()
const visit = (key) => {
  const chunk = manifest[key]
  if (!chunk || firstLoad.has(chunk.file)) return
  firstLoad.add(chunk.file)
  for (const next of chunk.imports ?? []) visit(next)
}
visit(entryKey)

const all = new Set(
  Object.values(manifest)
    .map((chunk) => chunk.file)
    .filter((file) => file.endsWith('.js')),
)
let first = 0
for (const file of firstLoad) {
  const gz = gzipped(file)
  first += gz
  console.log(`${file}: ${kb(gz)} gzipped (first load)`)
}
let total = 0
for (const file of all) total += gzipped(file)
console.log(`first load ${kb(first)} gzipped against a ${LIMIT / 1024} KB limit; all ${all.size} chunks together ${kb(total)} gzipped (not limited)`)
if (first > LIMIT) {
  console.error(`the first load is ${kb(first - LIMIT)} over the limit`)
  process.exit(1)
}

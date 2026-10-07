// The JavaScript the respond page loads must stay under 250 KB gzipped (US-087, NFR-013). The app ships
// one bundle, so the check sums every JS file in dist/assets; a route split would need only the entry
// and its chunks listed here. Run after `vite build`; exits non-zero over the limit.
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join } from 'node:path'
import { gzipSync } from 'node:zlib'

const LIMIT = 250 * 1024
const dir = join(process.cwd(), 'dist', 'assets')
const files = readdirSync(dir).filter((f) => f.endsWith('.js'))
if (files.length === 0) {
  console.error('no JavaScript in dist/assets; run the build first')
  process.exit(2)
}
let total = 0
for (const f of files) {
  const raw = statSync(join(dir, f)).size
  const gz = gzipSync(readFileSync(join(dir, f)), { level: 9 }).length
  total += gz
  console.log(`${f}: ${(raw / 1024).toFixed(0)} KB raw, ${(gz / 1024).toFixed(0)} KB gzipped`)
}
console.log(`total ${(total / 1024).toFixed(0)} KB gzipped against a ${LIMIT / 1024} KB limit`)
if (total > LIMIT) {
  console.error(`the JavaScript is ${((total - LIMIT) / 1024).toFixed(0)} KB over the limit`)
  process.exit(1)
}

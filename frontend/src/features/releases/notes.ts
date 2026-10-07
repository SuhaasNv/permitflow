/**
 * The release notes as data (US-094). The source is the repository's RELEASE_NOTES.md, read at build time,
 * so the What's new page can never drift from the notes: this parser reads the format documented at the
 * top of that file and the tests parse the real file. No markdown library: four line shapes and three
 * inline marks are all the notes use.
 *
 *   ## Coming next                                  the paragraphs until the next release heading
 *   ## vX.Y.Z, D Month YYYY[ (note)]: title         one release, newest first
 *   **Heading** [trailing note]                     an audience block inside a release
 *   - item                                          a bullet in the current block
 *   any other line                                  a paragraph (of the release before its first block)
 *   ---                                             ignored
 */

export type Audience = 'operator' | 'officer' | 'admin' | 'everyone'

export interface NoteBlock {
  heading: string
  /** The text after the bold heading on the same line, if any ("(full list in ...)"). */
  note: string | null
  audience: Audience
  paragraphs: string[]
  items: string[]
}

export interface Release {
  version: string
  date: string
  /** The parenthesised note in the heading, if any ("release candidate v0.4.0-rc.2 on the development environment"). */
  note: string | null
  title: string
  intro: string[]
  blocks: NoteBlock[]
}

export interface ReleaseNotes {
  comingNext: string[]
  releases: Release[]
}

const RELEASE_HEADING = /^## (v\d+\.\d+\.\d+), (\d{1,2} [A-Z][a-z]+ \d{4})(?: \(([^)]*)\))?: (.+)$/
const COMING_NEXT_HEADING = /^## Coming next\s*$/
const BLOCK_HEADING = /^\*\*([^*]+)\*\*\s*(.*)$/
const BULLET = /^- (.+)$/

/** The audience a block is written for, from its heading: operators, officers, the office, or everyone. */
export function audienceOf(heading: string): Audience {
  const h = heading.toLowerCase()
  if (h.includes('operator')) return 'operator'
  if (h.includes('officer')) return 'officer'
  if (h.includes('administrator') || h.includes('licensing office')) return 'admin'
  return 'everyone'
}

export class ReleaseNotesFormatError extends Error {
  constructor(line: number, problem: string) {
    super(`RELEASE_NOTES.md line ${line}: ${problem}`)
    this.name = 'ReleaseNotesFormatError'
  }
}

export function parseReleaseNotes(raw: string): ReleaseNotes {
  const comingNext: string[] = []
  const releases: Release[] = []
  let section: 'preamble' | 'coming' | 'release' = 'preamble'
  let release: Release | null = null
  let block: NoteBlock | null = null

  raw.split(/\r?\n/).forEach((rawLine, index) => {
    const line = rawLine.trimEnd()
    const at = index + 1
    if (line === '' || line === '---') return
    if (line.startsWith('## ')) {
      block = null
      if (COMING_NEXT_HEADING.test(line)) {
        section = 'coming'
        release = null
        return
      }
      const m = RELEASE_HEADING.exec(line)
      if (!m) throw new ReleaseNotesFormatError(at, `a release heading must read "## vX.Y.Z, D Month YYYY[ (note)]: title", got "${line}"`)
      release = { version: m[1], date: m[2], note: m[3] ?? null, title: m[4].trim(), intro: [], blocks: [] }
      releases.push(release)
      section = 'release'
      return
    }
    if (section === 'preamble') return
    if (section === 'coming') {
      comingNext.push(line)
      return
    }
    if (!release) throw new ReleaseNotesFormatError(at, 'text before the first release heading')
    const heading = BLOCK_HEADING.exec(line)
    if (heading) {
      block = { heading: heading[1].trim(), note: heading[2].trim() || null, audience: audienceOf(heading[1]), paragraphs: [], items: [] }
      release.blocks.push(block)
      return
    }
    const bullet = BULLET.exec(line)
    if (bullet) {
      if (!block) throw new ReleaseNotesFormatError(at, 'a bullet outside a **block**')
      block.items.push(bullet[1].trim())
      return
    }
    if (block) block.paragraphs.push(line)
    else release.intro.push(line)
  })

  if (releases.length === 0) throw new ReleaseNotesFormatError(0, 'no release heading found')
  releases.forEach((r) => {
    if (r.blocks.length === 0 && r.intro.length === 0) throw new ReleaseNotesFormatError(0, `${r.version} has no content`)
  })
  return { comingNext, releases }
}

/** The notes for one version: the exact version, or the release an rc belongs to (`v0.4.0-rc.2` reads `v0.4.0`). */
export function releaseFor(notes: ReleaseNotes, version: string): Release | undefined {
  const wanted = version.startsWith('v') ? version : `v${version}`
  const base = wanted.replace(/-.*$/, '')
  return notes.releases.find((r) => r.version === wanted) ?? notes.releases.find((r) => r.version === base)
}

/** The reader's own block first, the rest in file order; `everyone` blocks are never folded. */
export function orderBlocks(blocks: NoteBlock[], reader: Audience | null): { own: NoteBlock[]; others: NoteBlock[]; shared: NoteBlock[] } {
  const shared = blocks.filter((b) => b.audience === 'everyone')
  const addressed = blocks.filter((b) => b.audience !== 'everyone')
  if (!reader || reader === 'admin') return { own: addressed, others: [], shared }
  return { own: addressed.filter((b) => b.audience === reader), others: addressed.filter((b) => b.audience !== reader), shared }
}

export type InlineToken = { kind: 'text' | 'code' | 'strong'; text: string } | { kind: 'link'; text: string; href: string }

/** `code`, **strong** and bare https links; everything else is text. */
export function tokenizeInline(text: string): InlineToken[] {
  const out: InlineToken[] = []
  const re = /`([^`]+)`|\*\*([^*]+)\*\*|(https?:\/\/[^\s),]+)/g
  let last = 0
  for (let m = re.exec(text); m !== null; m = re.exec(text)) {
    if (m.index > last) out.push({ kind: 'text', text: text.slice(last, m.index) })
    if (m[1] !== undefined) out.push({ kind: 'code', text: m[1] })
    else if (m[2] !== undefined) out.push({ kind: 'strong', text: m[2] })
    else out.push({ kind: 'link', text: m[3], href: m[3] })
    last = m.index + m[0].length
  }
  if (last < text.length) out.push({ kind: 'text', text: text.slice(last) })
  return out
}

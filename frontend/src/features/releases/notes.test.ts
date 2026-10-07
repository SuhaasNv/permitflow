import raw from 'virtual:release-notes'

import { ReleaseNotesFormatError, audienceOf, orderBlocks, parseReleaseNotes, releaseFor, tokenizeInline } from './notes'

const SAMPLE = `# Release notes

Preamble, ignored.

---

## Coming next

**v9.0.0** is planned.

## v0.4.0, 21 September 2026 (release candidate v0.4.0-rc.2 on the development environment): the site visit

An introduction line.

**New for licensing officers**
- Arrange the site visit.

**New for operators**
- Answer the flagged items.

**New for the licensing office (administrators)**
- An operations overview.

**Also**
- Reviewed twice.

---

## v0.3.0, 19 September 2026: production

**New**
- Live on a custom domain.

**Known limitations** (full list in \`docs/x.md\`)
- No email.
`

describe('parseReleaseNotes', () => {
  it('reads the documented shapes', () => {
    const notes = parseReleaseNotes(SAMPLE)
    expect(notes.comingNext).toEqual(['**v9.0.0** is planned.'])
    expect(notes.releases.map((r) => r.version)).toEqual(['v0.4.0', 'v0.3.0'])
    const [rc, prod] = notes.releases
    expect(rc.date).toBe('21 September 2026')
    expect(rc.note).toBe('release candidate v0.4.0-rc.2 on the development environment')
    expect(rc.title).toBe('the site visit')
    expect(rc.intro).toEqual(['An introduction line.'])
    expect(rc.blocks.map((b) => [b.heading, b.audience, b.items.length])).toEqual([
      ['New for licensing officers', 'officer', 1],
      ['New for operators', 'operator', 1],
      ['New for the licensing office (administrators)', 'admin', 1],
      ['Also', 'everyone', 1],
    ])
    expect(prod.note).toBeNull()
    expect(prod.blocks[1].note).toBe('(full list in `docs/x.md`)')
  })

  it('refuses a heading of another shape, naming the line', () => {
    expect(() => parseReleaseNotes('## v0.4.0 (rc): title\n- x')).toThrow(ReleaseNotesFormatError)
    expect(() => parseReleaseNotes('## v0.4.0 (rc): title\n- x')).toThrow(/line 1/)
    expect(() => parseReleaseNotes('## v1.0.0, 1 January 2027: t\n- a bullet before any block')).toThrow(/outside a \*\*block\*\*/)
    expect(() => parseReleaseNotes('nothing here')).toThrow(/no release heading/)
  })

  it('parses the real RELEASE_NOTES.md, served by the build-time module', () => {
    expect(raw.startsWith('# Release notes')).toBe(true)
    const notes = parseReleaseNotes(raw)
    expect(notes.releases.length).toBeGreaterThanOrEqual(4)
    expect(notes.comingNext.length).toBeGreaterThan(0)
    for (const r of notes.releases) {
      expect(r.version).toMatch(/^v\d+\.\d+\.\d+$/)
      expect(r.date).toMatch(/^\d{1,2} [A-Z][a-z]+ \d{4}$/)
      expect(r.title.length).toBeGreaterThan(0)
      expect(r.blocks.length).toBeGreaterThan(0)
      for (const b of r.blocks) expect(b.items.length + b.paragraphs.length).toBeGreaterThan(0)
    }
    // The running build has notes: the rc reads the release it belongs to.
    expect(releaseFor(notes, __APP_VERSION__)?.version).toBe(`v${__APP_VERSION__.replace(/-.*$/, '')}`)
  })

  it('never hands an operator an internal status code', () => {
    const notes = parseReleaseNotes(raw)
    const operatorText = notes.releases
      .flatMap((r) => r.blocks.filter((b) => b.audience === 'operator'))
      .flatMap((b) => [...b.items, ...b.paragraphs])
      .join('\n')
    expect(operatorText).not.toMatch(/\b[a-z]+_[a-z_]+\b/)
    expect(operatorText).not.toMatch(/PENDING_|SITE_VISIT_|RESUBMISSION/)
  })
})

describe('audienceOf, releaseFor, orderBlocks, tokenizeInline', () => {
  it('maps headings to audiences', () => {
    expect(audienceOf('New for operators')).toBe('operator')
    expect(audienceOf('New for licensing officers')).toBe('officer')
    expect(audienceOf('New for the licensing office (administrators)')).toBe('admin')
    expect(audienceOf('Behind the scenes')).toBe('everyone')
  })

  it('finds the release for a version, an rc reading its release', () => {
    const notes = parseReleaseNotes(SAMPLE)
    expect(releaseFor(notes, 'v0.3.0')?.version).toBe('v0.3.0')
    expect(releaseFor(notes, '0.4.0-rc.2')?.version).toBe('v0.4.0')
    expect(releaseFor(notes, 'v9.9.9')).toBeUndefined()
  })

  it('puts the reader first and folds the rest; admins and visitors see everything open', () => {
    const { blocks } = parseReleaseNotes(SAMPLE).releases[0]
    const operator = orderBlocks(blocks, 'operator')
    expect(operator.own.map((b) => b.audience)).toEqual(['operator'])
    expect(operator.others.map((b) => b.audience)).toEqual(['officer', 'admin'])
    expect(operator.shared.map((b) => b.heading)).toEqual(['Also'])
    const officer = orderBlocks(blocks, 'officer')
    expect(officer.own.map((b) => b.audience)).toEqual(['officer'])
    expect(officer.others.map((b) => b.audience)).toEqual(['operator', 'admin'])
    for (const reader of ['admin', null] as const) {
      const all = orderBlocks(blocks, reader)
      expect(all.own.map((b) => b.audience)).toEqual(['officer', 'operator', 'admin'])
      expect(all.others).toEqual([])
    }
  })

  it('tokenizes code, bold and bare links', () => {
    expect(tokenizeInline('Live at https://permitflow.space, with `CHANGELOG.md` and **bold** text.')).toEqual([
      { kind: 'text', text: 'Live at ' },
      { kind: 'link', text: 'https://permitflow.space', href: 'https://permitflow.space' },
      { kind: 'text', text: ', with ' },
      { kind: 'code', text: 'CHANGELOG.md' },
      { kind: 'text', text: ' and ' },
      { kind: 'strong', text: 'bold' },
      { kind: 'text', text: ' text.' },
    ])
    expect(tokenizeInline('plain')).toEqual([{ kind: 'text', text: 'plain' }])
  })
})

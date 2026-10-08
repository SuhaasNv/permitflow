import raw from 'virtual:release-notes'

import { ReleaseNotesFormatError, audienceOf, orderBlocks, parseReleaseNotes, releaseFor, tokenizeInline, visibleNotes } from './notes'

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
      expect(r.version).toMatch(/^v\d+\.\d+\.\d+(-rc\.\d+)?$/)
      expect(r.candidate).toBe(r.version.includes('-rc.'))
      expect(r.date).toMatch(/^\d{1,2} [A-Z][a-z]+ \d{4}$/)
      expect(r.title.length).toBeGreaterThan(0)
      expect(r.blocks.length).toBeGreaterThan(0)
      for (const b of r.blocks) expect(b.items.length + b.paragraphs.length).toBeGreaterThan(0)
    }
    // The running build has notes: a candidate build has its own section, a release its release section.
    expect(releaseFor(notes, __APP_VERSION__)?.version).toBe(`v${__APP_VERSION__}`)
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

const WITH_CANDIDATES = `# Release notes

## Coming next

**v0.6.0** is planned.

## v0.5.0, 20 October 2026: safe intake

**New**
- Files are checked.

---

## v0.5.0-rc.2, 18 October 2026 (the second look): safe intake, again

**New**
- The check also covers photos.

## v0.5.0-rc.1, 15 October 2026: safe intake

An introduction line.

**New**
- Files are checked.

## v0.4.0, 8 October 2026: the site visit

**New**
- The site visit.
`

describe('release candidates (US-110)', () => {
  it('reads -rc.N headings, with or without a note, keeping the file order', () => {
    const notes = parseReleaseNotes(WITH_CANDIDATES)
    expect(notes.releases.map((r) => [r.version, r.candidate])).toEqual([
      ['v0.5.0', false],
      ['v0.5.0-rc.2', true],
      ['v0.5.0-rc.1', true],
      ['v0.4.0', false],
    ])
    expect(notes.releases[1].note).toBe('the second look')
    expect(notes.releases[1].title).toBe('safe intake, again')
    expect(notes.releases[2].note).toBeNull()
    expect(notes.releases[2].intro).toEqual(['An introduction line.'])
    expect(notes.releases[2].blocks[0].items).toEqual(['Files are checked.'])
  })

  it.each([
    '## v0.5.0-rc, 15 October 2026: title',
    '## v0.5.0-rc.x, 15 October 2026: title',
    '## v0.5.0-beta.1, 15 October 2026: title',
    '## v0.5.0-rc.1.2, 15 October 2026: title',
    '## v0.5-rc.1, 15 October 2026: title',
    '## v0.5.0 rc.1, 15 October 2026: title',
    '## v0.5.0-rc.1 (15 October 2026): title',
    '## v0.5.0-rc.1, 15 October 2026 title',
  ])('still refuses %s, naming the line', (heading) => {
    expect(() => parseReleaseNotes(`${heading}\n**New**\n- x`)).toThrow(ReleaseNotesFormatError)
    expect(() => parseReleaseNotes(`${heading}\n**New**\n- x`)).toThrow(/line 1/)
  })

  it('shows candidates only when asked; production keeps releases and Coming next, in order', () => {
    const notes = parseReleaseNotes(WITH_CANDIDATES)
    expect(visibleNotes(notes, true)).toBe(notes)
    const production = visibleNotes(notes, false)
    expect(production.releases.map((r) => r.version)).toEqual(['v0.5.0', 'v0.4.0'])
    expect(production.releases.some((r) => r.candidate)).toBe(false)
    expect(production.comingNext).toEqual(notes.comingNext)
    expect(notes.releases).toHaveLength(4)
  })

  it('finds a candidate by its exact version and falls back to its release when it is hidden', () => {
    const notes = parseReleaseNotes(WITH_CANDIDATES)
    expect(releaseFor(notes, '0.5.0-rc.2')?.version).toBe('v0.5.0-rc.2')
    expect(releaseFor(notes, 'v0.5.0-rc.1')?.candidate).toBe(true)
    expect(releaseFor(visibleNotes(notes, false), '0.5.0-rc.2')?.version).toBe('v0.5.0')
  })

  it('the real file: candidates are listed, and no release mentions a candidate', () => {
    const notes = parseReleaseNotes(raw)
    const candidates = notes.releases.filter((r) => r.candidate)
    expect(candidates.map((r) => r.version)).toEqual(expect.arrayContaining(['v0.4.0-rc.2', 'v0.4.0-rc.1']))
    for (const r of notes.releases.filter((x) => !x.candidate)) {
      const text = [r.title, r.note ?? '', ...r.intro, ...r.blocks.flatMap((b) => [b.heading, b.note ?? '', ...b.paragraphs, ...b.items])].join('\n')
      expect(text, r.version).not.toMatch(/candidate|-rc\.|\brc\d/i)
    }
    // What production would show: no candidate anywhere.
    expect(visibleNotes(notes, false).releases.every((r) => !r.candidate)).toBe(true)
  })
})

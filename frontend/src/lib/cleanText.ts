/**
 * Mirror of `backend/app/domain/text_clean.py` (US-108): the same cleaning, held to the same examples
 * (`backend/tests/fixtures/form_rules.json`). The server stores its own result; the client cleans only to
 * check what the server will see.
 */

// Zero-width, bidi controls and the Unicode Tag block: invisible to a reader, readable by a model.
const HIDDEN = /[\u200b-\u200d\u2060\ufeff\u202a-\u202e\u2066-\u2069\u{e0000}-\u{e007f}]/gu
// eslint-disable-next-line no-control-regex
const CONTROL = /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f-\u009f]/g
const SPACES = /[^\S\n]+/g
const LINE_EDGES = / ?\n ?/g
const BLANK_RUNS = /\n{3,}/g

export function cleanText(value: string, multiline = false): string {
  let text = value.normalize('NFC').replace(HIDDEN, '')
  text = text
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
    .replace(/[\u2028\u2029]/g, '\n')
    .replace(CONTROL, '')
  if (!multiline) text = text.replace(/\n/g, ' ')
  text = text.replace(SPACES, ' ')
  if (multiline) text = text.replace(LINE_EDGES, '\n').replace(BLANK_RUNS, '\n\n')
  return text.trim()
}

/** Length as the server counts it: code points, so an emoji is one character, not two. */
export function lengthOf(value: string): number {
  return Array.from(value).length
}

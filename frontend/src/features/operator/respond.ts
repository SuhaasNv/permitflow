export type RespondTarget = { kind: 'section'; key: string } | { kind: 'documents' } | { kind: 'resubmit' }

/**
 * Where "Save and continue" goes while responding to feedback (US-041): the next flagged section after the
 * current one, then the documents page if a document was flagged, then the application page where Resubmit lives.
 * Locked sections are never a destination.
 */
export function nextRespondTarget(input: {
  sectionKeys: string[]
  activeKey: string
  flaggedSections: string[]
  docsFlagged: boolean
}): RespondTarget {
  const { sectionKeys, activeKey, flaggedSections, docsFlagged } = input
  const start = sectionKeys.indexOf(activeKey)
  for (let i = start + 1; i < sectionKeys.length; i += 1) {
    const key = sectionKeys[i]
    if (key !== undefined && flaggedSections.includes(key)) return { kind: 'section', key }
  }
  if (docsFlagged) return { kind: 'documents' }
  return { kind: 'resubmit' }
}

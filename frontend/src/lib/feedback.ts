/** Feedback items that still ask the operator for a change (US-083): one rule for the operator's notice,
 * the section form and the officer's case markers. */
export interface HasResolution {
  resolution: string
  section_key?: string | null
  document_type?: string | null
}

export function openItems<T extends HasResolution>(items: T[]): T[] {
  return items.filter((f) => f.resolution === 'open')
}

/** The open items aimed at one section or one document type. */
export function openFor<T extends HasResolution>(items: T[], type: 'section' | 'document', key: string): T[] {
  return openItems(items).filter((f) => (type === 'section' ? f.section_key === key : f.document_type === key))
}

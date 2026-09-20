/**
 * Shared fixtures for behaviour tests: a two-section form schema and an operator application view
 * that can be shaped per test with overrides. Values follow the demo application (Kopi & Kaya).
 */
import type { ApplicationView, DocumentSlotView, SectionView } from '@/api/applications'
import type { FieldDef, FormSchema, SectionDef } from '@/api/formSchema'
import type { OfficerApplication } from '@/api/officer'

const field = (key: string, label: string, over: Partial<FieldDef> = {}): FieldDef => ({
  key,
  label,
  kind: 'text',
  required: true,
  max_length: 120,
  pattern: null,
  pattern_message: null,
  options: [],
  min_value: null,
  max_value: null,
  help: null,
  must_be_true: false,
  ...over,
})

export const businessSection: SectionDef = {
  key: 'business',
  title: 'Business details',
  description: 'The registered business applying for the licence',
  fields: [
    field('business_name', 'Business name'),
    field('uen', 'UEN', { pattern: '^[0-9]{8,9}[A-Z]$', pattern_message: 'Enter a valid UEN.' }),
  ],
}

export const premisesSection: SectionDef = {
  key: 'premises',
  title: 'Premises',
  description: 'Where the food will be prepared and sold',
  fields: [
    field('address_line_1', 'Premises address'),
    field('postal_code', 'Postal code', { pattern: '^[0-9]{6}$', pattern_message: 'Six digits.' }),
  ],
}

export const formSchema: FormSchema = {
  licence_type: 'food_establishment',
  licence_title: 'Food Establishment Licence',
  sections: [businessSection, premisesSection],
  required_documents: [
    { type: 'business_profile', label: 'Business profile (ACRA)' },
    { type: 'floor_plan', label: 'Floor plan' },
  ],
}

export function sectionView(key: string, over: Partial<SectionView> = {}): SectionView {
  const def = formSchema.sections.find((s) => s.key === key)
  return {
    key,
    title: def?.title ?? key,
    description: def?.description ?? '',
    data:
      key === 'business'
        ? { business_name: 'Kopi & Kaya Toast House Pte. Ltd.', uen: '202355555E' }
        : { address_line_1: '10 Jalan Besar #01-12', postal_code: '208787' },
    complete: true,
    started: true,
    errors: {},
    editable: false,
    ...over,
  }
}

export function slotView(type: string, over: Partial<DocumentSlotView> = {}): DocumentSlotView {
  return {
    type,
    label: formSchema.required_documents.find((d) => d.type === type)?.label ?? type,
    present: true,
    editable: false,
    document: {
      id: `doc-${type}`,
      document_type: type,
      original_filename: `${type}.pdf`,
      content_type: 'application/pdf',
      size_bytes: 1000,
      uploaded_at: '2026-09-19T01:00:00Z',
      replaces_filename: null,
      verification: {
        status: 'verified',
        summary: 'Matches the form.',
        issues: [],
        missing_information: [],
        error_reason: null,
        requested_at: '2026-09-19T01:00:00Z',
        finished_at: '2026-09-19T01:00:10Z',
      },
    },
    ...over,
  }
}

/** A submitted application, waiting on the licensing office. */
export function applicationView(over: Partial<ApplicationView> = {}): ApplicationView {
  return {
    id: 'app-1',
    reference_no: 'PF-2026-001000',
    licence_title: 'Food Establishment Licence',
    status_label: 'Submitted',
    status_tone: 'info',
    status_explanation: 'Received by the licensing office.',
    can_edit: false,
    can_submit: false,
    sections: [sectionView('business'), sectionView('premises')],
    document_slots: [slotView('business_profile'), slotView('floor_plan')],
    completeness: {
      percent: 100,
      is_complete: true,
      sections_complete: 2,
      sections_total: 2,
      documents_present: 2,
      documents_total: 2,
      missing: [],
    },
    revision_count: 1,
    needs_operator_action: false,
    feedback: [],
    resubmit: null,
    revisions: [{ number: 1, submitted_at: '2026-09-19T01:10:00Z' }],
    decision_note: null,
    can_withdraw: true,
    can_delete: false,
    withdrawal_reason: null,
    licence: null,
    site_visit: null,
    clarification: null,
    created_at: '2026-09-19T00:50:00Z',
    updated_at: '2026-09-19T01:10:00Z',
    ...over,
  }
}

/** The same application while the operator responds to feedback on the premises section only. */
export function respondingView(over: Partial<ApplicationView> = {}): ApplicationView {
  return applicationView({
    status_label: 'Pending Pre-Site Resubmission',
    status_tone: 'warning',
    status_explanation: 'The licensing office has asked for changes.',
    can_edit: true,
    needs_operator_action: true,
    sections: [sectionView('business'), sectionView('premises', { editable: true })],
    feedback: [
      {
        id: 'fb-1',
        target_type: 'section',
        section_key: 'premises',
        document_type: null,
        target_label: 'Premises',
        message: 'The floor area does not match the tenancy agreement.',
        resolution: 'open',
        round: 1,
        released_at: '2026-09-19T02:00:00Z',
        addressed_in_revision: null,
      },
    ],
    resubmit: {
      can_resubmit: false,
      changed_sections: [],
      changed_document_types: [],
      untouched_targets: ['Premises'],
      reason: 'Change at least one flagged section or document before resubmitting.',
    },
    ...over,
  })
}

/** The officer's view of the same application after one resubmission (two revisions). */
export function officerView(over: Partial<OfficerApplication> = {}): OfficerApplication {
  return {
    id: 'app-1',
    reference_no: 'PF-2026-001000',
    licence_title: 'Food Establishment Licence',
    status: 'pre_site_resubmitted',
    status_label: 'Pre-Site Resubmitted',
    status_tone: 'info',
    applicant: { id: 'u1', full_name: 'Tan Wei Ling', email: 'operator@permitflow.example.sg' },
    business_name: 'Kopi & Kaya Toast House Pte. Ltd.',
    premises_summary: '10 Jalan Besar #01-12',
    sections: [
      {
        key: 'business',
        title: 'Business details',
        description: '',
        data: { business_name: 'Kopi & Kaya Toast House Pte. Ltd.', uen: '202355555E' },
        complete: true,
      },
      {
        key: 'premises',
        title: 'Premises',
        description: '',
        data: { address_line_1: '10 Jalan Besar #01-12', postal_code: '208788' },
        complete: true,
      },
    ],
    documents: [
      {
        id: 'doc-floor_plan',
        document_type: 'floor_plan',
        label: 'Floor plan',
        original_filename: 'new.pdf',
        content_type: 'application/pdf',
        size_bytes: 1024,
        uploaded_at: '2026-09-19T02:50:00Z',
        in_current_revision: true,
        verification: {
          status: 'verified',
          summary: 'Matches the form.',
          confidence: 0.95,
          issues: [],
          missing_information: [],
          error_reason: null,
          provider: 'mock',
          model: 'mock-1',
          requested_at: '2026-09-19T02:50:00Z',
          finished_at: '2026-09-19T02:50:10Z',
        },
      },
    ],
    missing_document_types: [],
    verification_summary: { total: 1, verified: 1, issues_found: 0, needs_review: 0, checking: 0, other: 0 },
    revisions: [
      { id: 'r1', number: 1, submitted_at: '2026-09-19T01:10:00Z', submitted_by: 'Tan Wei Ling' },
      { id: 'r2', number: 2, submitted_at: '2026-09-19T03:00:00Z', submitted_by: 'Tan Wei Ling' },
    ],
    current_revision_number: 2,
    previous_revision_number: 1,
    changed_sections: ['premises'],
    changed_document_types: ['floor_plan'],
    addressed_unresolved_count: 1,
    feedback: [],
    open_feedback_count: 0,
    feedback_editable: false,
    feedback_locked_reason: 'Start the review to add feedback.',
    actions: [
      { target: 'under_review', label: 'Start review', enabled: true, reason: null, requires_note: false },
      { target: 'rejected', label: 'Reject', enabled: true, reason: null, requires_note: true },
    ],
    decision_note: null,
    withdrawal_reason: null,
    licence: null,
    site_visit: null,
    checklist: null,
    version: 5,
    created_at: '2026-09-19T00:50:00Z',
    updated_at: '2026-09-19T03:00:00Z',
    ...over,
  }
}

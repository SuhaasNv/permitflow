import { request } from './client'

export type FieldKind = 'text' | 'email' | 'tel' | 'number' | 'integer' | 'date' | 'select' | 'textarea' | 'checkbox' | 'hours'

export interface FieldDef {
  key: string
  label: string
  kind: FieldKind
  required: boolean
  max_length: number | null
  pattern: string | null
  pattern_message: string | null
  options: { value: string; label: string }[]
  min_value: number | null
  max_value: number | null
  help: string | null
  must_be_true: boolean
  /** US-108. Optional so a definition written before them still type-checks; the server always sends them. */
  min_length?: number | null
  /** Named Singapore rule (sg_phone, uen, business_name, person_name, sg_postal, sg_address). */
  rule?: string | null
  max_decimals?: number | null
  min_months_ahead?: number | null
  max_years_ahead?: number | null
  /** hours: the time lists run in steps of this many minutes. */
  step_minutes?: number | null
}

export interface SectionDef {
  key: string
  title: string
  description: string
  fields: FieldDef[]
}

export interface FormSchema {
  licence_type: string
  licence_title: string
  sections: SectionDef[]
  required_documents: { type: string; label: string }[]
}

export function getFormSchema(): Promise<FormSchema> {
  return request<FormSchema>('/form-schema')
}

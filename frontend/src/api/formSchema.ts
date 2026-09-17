import { request } from './client'

export type FieldKind = 'text' | 'email' | 'tel' | 'number' | 'integer' | 'date' | 'select' | 'textarea' | 'checkbox'

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

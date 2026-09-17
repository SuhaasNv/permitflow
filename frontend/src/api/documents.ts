import type { ApplicationView } from './applications'
import { API_URL, AppError, request } from './client'
import type { ApiErrorBody } from './client'

export interface VerificationView {
  status: 'pending' | 'running' | 'verified' | 'issues_found' | 'needs_review' | 'unreadable' | 'failed' | 'unavailable'
  summary: string | null
  issues: {
    code: string
    severity: 'low' | 'medium' | 'high'
    message: string
  }[]
  missing_information: string[]
  error_reason: string | null
  finished_at: string | null
}

export interface DocumentView {
  id: string
  document_type: string
  original_filename: string
  content_type: string
  size_bytes: number
  uploaded_at: string
  replaces_filename: string | null
  verification: VerificationView | null
}

export interface UploadResult {
  application: ApplicationView
  document: DocumentView
  unchanged: boolean
}

export const ALLOWED_EXTENSIONS = ['.pdf', '.png', '.jpg', '.jpeg', '.txt']
export const MAX_UPLOAD_BYTES = 10 * 1024 * 1024

/** Client-side pre-check mirroring the server rules (SEC-005); the server remains authoritative. */
export function validateFile(file: File): string | null {
  const ext = file.name.includes('.') ? `.${file.name.split('.').pop()?.toLowerCase() ?? ''}` : ''
  if (!ALLOWED_EXTENSIONS.includes(ext)) return `${file.name} was not accepted. Only PDF, PNG, JPG or TXT files are supported.`
  if (file.size > MAX_UPLOAD_BYTES) return `${file.name} is larger than 10 MB.`
  if (file.size === 0) return `${file.name} is empty.`
  return null
}

let tokenGetter: () => string | null = () => null
export function setUploadTokenProvider(fn: () => string | null): void {
  tokenGetter = fn
}

/** XMLHttpRequest so the card can show real upload progress. */
export function uploadDocument(
  applicationId: string,
  documentType: string,
  file: File,
  onProgress: (fraction: number) => void,
): Promise<UploadResult> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${API_URL}/applications/${applicationId}/documents`)
    const token = tokenGetter()
    if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)
    xhr.upload.onprogress = (e) => {
      if (e.lengthComputable) onProgress(e.loaded / e.total)
    }
    xhr.onerror = () =>
      reject(
        new AppError(0, {
          code: 'network_error',
          message: 'Upload failed. Check your connection and try again.',
        }),
      )
    xhr.onload = () => {
      let parsed: unknown = null
      try {
        parsed = JSON.parse(xhr.responseText)
      } catch {
        parsed = null
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(parsed as UploadResult)
        return
      }
      const body = parsed as ApiErrorBody | null
      const requestId = xhr.getResponseHeader('X-Request-ID') ?? undefined
      reject(
        new AppError(
          xhr.status,
          body?.error ?? {
            code: 'http_error',
            message: `Upload failed (${xhr.status})`,
          },
          requestId,
        ),
      )
    }
    const form = new FormData()
    form.append('document_type', documentType)
    form.append('file', file)
    xhr.send(form)
  })
}

export function deleteDocument(applicationId: string, documentId: string): Promise<ApplicationView> {
  return request<ApplicationView>(`/applications/${applicationId}/documents/${documentId}`, { method: 'DELETE' })
}

export async function downloadDocument(applicationId: string, documentId: string, filename: string): Promise<void> {
  const token = tokenGetter()
  const res = await fetch(`${API_URL}/applications/${applicationId}/documents/${documentId}/download`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  if (!res.ok)
    throw new AppError(res.status, {
      code: 'http_error',
      message: 'Could not download this file.',
    })
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

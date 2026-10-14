import type { ApplicationView } from './applications'
import { API_URL, AppError, authInit, authXhr, notifyUnauthorized, refreshCsrf, request } from './client'
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
  /** When this run was requested (upload or re-run): staleness is measured from here. */
  requested_at: string
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
  /** US-099: null (stored with the scan off), scanning, clean or infected. Only null and clean can be opened. */
  scan_state?: ScanState
  /** When the verdict (clean or infected) landed; null while scanning or when the scan never ran. */
  scanned_at?: string | null
}

export type ScanState = 'scanning' | 'clean' | 'infected' | null

export const BLOCKED_MESSAGE = 'This file was blocked by the security check. Upload a different copy.'

/** One wording per scan error code (US-099). file_infected on a download is worded by the server for the reader's role. */
const SCAN_MESSAGES: Record<string, string> = {
  file_infected: BLOCKED_MESSAGE,
  file_scanning: 'This file is still being scanned. Try again in a moment.',
  scanner_unavailable: 'The security check is not available right now. Try again in a moment.',
  documents_not_clear: 'Review and submit opens when no document is blocked or being scanned.',
}

/** The clear message for a scan error code, or null when the error is not one of them. */
export function scanMessage(error: unknown): string | null {
  return error instanceof AppError ? (SCAN_MESSAGES[error.code] ?? null) : null
}

/** The failure of a direct download: the server's code decides the wording, the status is the fallback. */
export async function downloadError(res: Response, fallback: string): Promise<AppError> {
  let body: ApiErrorBody['error'] | undefined
  try {
    body = ((await res.json()) as ApiErrorBody).error
  } catch {
    body = undefined
  }
  const code = body?.code ?? 'http_error'
  const message = code === 'file_infected' && body ? body.message : (SCAN_MESSAGES[code] ?? fallback)
  return new AppError(res.status, { code, message })
}

export interface UploadResult {
  application: ApplicationView
  document: DocumentView
  unchanged: boolean
}

const ALLOWED_EXTENSIONS = ['.pdf', '.png', '.jpg', '.jpeg', '.txt']
const MAX_UPLOAD_BYTES = 10 * 1024 * 1024

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
/** The bearer for direct fetches outside the JSON client (downloads, US-065 attachments); null in cookie mode. */
export function uploadToken(): string | null {
  return tokenGetter()
}

/** XMLHttpRequest so the card can show real upload progress. */
export function uploadDocument(
  applicationId: string,
  documentType: string,
  file: File,
  onProgress: (fraction: number) => void,
): Promise<UploadResult> {
  const form = new FormData()
  form.append('document_type', documentType)
  form.append('file', file)
  return uploadWithProgress<UploadResult>(`/applications/${applicationId}/documents`, form, onProgress)
}

/** One multipart upload over XMLHttpRequest with a progress callback (documents and evidence, US-087). */
export function uploadWithProgress<T>(
  path: string,
  form: FormData,
  onProgress: (fraction: number) => void,
  retried = false,
): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${API_URL}${path}`)
    authXhr(xhr, tokenGetter()) // bearer, or in cookie mode withCredentials plus the CSRF header (US-104)
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
        resolve(parsed as T)
        return
      }
      const body = parsed as ApiErrorBody | null
      const requestId = xhr.getResponseHeader('X-Request-ID') ?? undefined
      const failure = new AppError(
        xhr.status,
        body?.error ?? {
          code: 'http_error',
          message: `Upload failed (${xhr.status})`,
        },
        requestId,
      )
      if (xhr.status === 403 && !retried && failure.code === 'csrf_failed') {
        // A stale CSRF value (US-104): read it again and send the upload once more.
        refreshCsrf()
          .then((fresh) => (fresh ? uploadWithProgress<T>(path, form, onProgress, true).then(resolve, reject) : reject(failure)))
          .catch(() => reject(failure))
        return
      }
      if (xhr.status === 401) notifyUnauthorized()
      reject(failure)
    }
    xhr.send(form)
  })
}

export function deleteDocument(applicationId: string, documentId: string): Promise<ApplicationView> {
  return request<ApplicationView>(`/applications/${applicationId}/documents/${documentId}`, { method: 'DELETE' })
}

/** Saves a blob under its filename. Some browsers start the download after click() returns, so revoke once it has begun. */
export function saveBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 1500)
}

/** Only inert types open in a tab: a blob URL shares the app's origin, so anything that could run script stays a download. */
const OPENABLE_TYPES = ['application/pdf', 'image/png', 'image/jpeg', 'text/plain']
const BLOB_URL_LIFETIME_MS = 60_000

/**
 * Opens a file in a new tab. The tab is opened first, in the click's own turn, so popup blockers allow it; `load`
 * fetches the file with the session; a failure closes the tab and rethrows. A blocked popup or a type outside the
 * allowlist falls back to a download. The blob is rebuilt with the allowlisted type, never the server's raw header.
 */
export async function openBlobInTab(load: () => Promise<Blob>, filename: string): Promise<void> {
  const tab = window.open('', '_blank')
  if (!tab) {
    saveBlob(await load(), filename)
    return
  }
  tab.opener = null
  let blob: Blob
  try {
    blob = await load()
  } catch (error) {
    tab.close()
    throw error
  }
  const type = blob.type.split(';')[0]?.trim().toLowerCase() ?? ''
  if (!OPENABLE_TYPES.includes(type)) {
    tab.close()
    saveBlob(blob, filename)
    return
  }
  const url = URL.createObjectURL(new Blob([blob], { type: type === 'text/plain' ? 'text/plain;charset=utf-8' : type }))
  tab.location.href = url
  setTimeout(() => URL.revokeObjectURL(url), BLOB_URL_LIFETIME_MS)
}

async function fetchDocumentBlob(applicationId: string, documentId: string): Promise<Blob> {
  const res = await fetch(`${API_URL}/applications/${applicationId}/documents/${documentId}/download`, authInit(tokenGetter()))
  if (!res.ok) {
    if (res.status === 401) notifyUnauthorized()
    throw await downloadError(res, res.status === 404 ? 'This file is no longer available.' : 'Could not download this file.')
  }
  return res.blob()
}

export async function downloadDocument(applicationId: string, documentId: string, filename: string): Promise<void> {
  saveBlob(await fetchDocumentBlob(applicationId, documentId), filename)
}

export function openDocument(applicationId: string, documentId: string, filename: string): Promise<void> {
  return openBlobInTab(() => fetchDocumentBlob(applicationId, documentId), filename)
}

async function fetchPdf(path: string): Promise<Blob> {
  const res = await fetch(`${API_URL}${path}`, authInit(tokenGetter()))
  if (!res.ok) {
    if (res.status === 401) notifyUnauthorized()
    throw new AppError(res.status, {
      code: 'http_error',
      message:
        res.status === 404
          ? 'This file is not available.'
          : res.status === 409
            ? 'Not available in this state.'
            : 'Could not fetch this file.',
    })
  }
  return res.blob()
}

/** The issued licence certificate (US-051), saved as <licence_no>.pdf. */
export async function downloadLicence(applicationId: string, licenceNo: string): Promise<void> {
  saveBlob(await fetchPdf(`/applications/${applicationId}/licence`), `${licenceNo}.pdf`)
}

/** The issued licence certificate in a new tab. */
export function openLicence(applicationId: string, licenceNo: string): Promise<void> {
  return openBlobInTab(() => fetchPdf(`/applications/${applicationId}/licence`), `${licenceNo}.pdf`)
}

/** Officer preview of the certificate before approving (US-051): the watermarked PDF as a blob, nothing stored. */
export function fetchLicencePreview(applicationId: string): Promise<Blob> {
  return fetchPdf(`/officer/applications/${applicationId}/licence/preview`)
}

export function rerunVerification(applicationId: string, documentId: string): Promise<UploadResult> {
  return request<UploadResult>(`/applications/${applicationId}/documents/${documentId}/verify`, { method: 'POST' })
}

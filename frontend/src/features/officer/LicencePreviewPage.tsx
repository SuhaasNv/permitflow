import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { AppError } from '@/api/client'
import { fetchLicencePreview } from '@/api/documents'
import { buttonClasses } from '@/features/shared/Button'
import { PageHeader } from '@/features/shared/PageHeader'
import { ErrorPanel, Skeleton } from '@/features/shared/states'

/** What the licence certificate will say if the officer approves now (US-051). Watermarked; nothing is stored. */
export function LicencePreviewPage() {
  const { id = '' } = useParams()
  const [url, setUrl] = useState<string | null>(null)
  const [error, setError] = useState<Error | null>(null)
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    let objectUrl: string | null = null
    let cancelled = false
    fetchLicencePreview(id)
      .then((blob) => {
        if (cancelled) return
        objectUrl = URL.createObjectURL(blob)
        setUrl(objectUrl)
      })
      .catch((e: unknown) => {
        if (!cancelled) setError(e instanceof Error ? e : new AppError(0, { code: 'unknown', message: 'Could not load the preview.' }))
      })
    return () => {
      cancelled = true
      if (objectUrl) URL.revokeObjectURL(objectUrl)
    }
  }, [id, attempt])

  const back = `/officer/applications/${id}`
  return (
    <>
      <PageHeader
        eyebrow="Licensing officer"
        title="Licence preview"
        subtitle="This is what the certificate will say if you approve now. It is watermarked and nothing has been issued."
        actions={
          <Link to={back} className={buttonClasses('secondary')}>
            Back to the case
          </Link>
        }
      />
      {error ? (
        <ErrorPanel
          error={error}
          onRetry={() => {
            setError(null)
            setAttempt((n) => n + 1)
          }}
        />
      ) : url ? (
        <div className="pf-surface overflow-hidden">
          <object
            data={url}
            type="application/pdf"
            className="block h-[calc(100vh-260px)] min-h-[560px] w-full"
            aria-label="Licence certificate preview"
          >
            <p className="p-6 text-sm text-text-2">
              Your browser cannot display PDFs inline.{' '}
              <a href={url} download="licence-preview.pdf" className="font-semibold">
                Download the preview
              </a>
              .
            </p>
          </object>
        </div>
      ) : (
        <Skeleton className="h-[560px]" />
      )}
    </>
  )
}

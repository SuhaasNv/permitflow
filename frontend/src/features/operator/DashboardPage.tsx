import { Link, useNavigate } from "react-router-dom";

import type { ApplicationSummary } from "@/api/applications";
import { useAuth } from "@/features/auth/AuthContext";
import { Button } from "@/features/shared/Button";
import { PageHeader } from "@/features/shared/PageHeader";
import { StatusBadge } from "@/features/shared/StatusBadge";
import { EmptyPanel, ErrorPanel, Skeleton } from "@/features/shared/states";
import { formatDateTime } from "@/lib/format";
import { useApplications, useCreateApplication } from "./queries";

function rowAction(app: ApplicationSummary): string {
  if (app.status_label === "Draft") return "Continue";
  if (app.status_tone === "warning") return "Respond";
  return "View";
}

function ApplicationsTable({ apps }: { apps: ApplicationSummary[] }) {
  return (
    <div className="overflow-hidden rounded-lg border border-line bg-surface shadow-[var(--shadow-1)]">
      <div className="flex items-center justify-between border-b border-line px-5 py-3.5">
        <h2 className="text-base font-semibold">My applications</h2>
        <span className="text-xs text-text-3">
          {apps.length} {apps.length === 1 ? "application" : "applications"} ·
          sorted by last update
        </span>
      </div>
      <table className="w-full table-fixed border-collapse text-sm">
        <colgroup>
          <col className="w-[170px]" />
          <col />
          <col className="hidden w-[240px] md:table-column" />
          <col className="hidden w-[130px] md:table-column" />
          <col className="w-[110px]" />
        </colgroup>
        <thead>
          <tr className="bg-surface-2 text-left text-xs font-semibold uppercase tracking-[0.04em] text-text-3">
            <th className="border-b border-line px-4 py-2.5">Reference</th>
            <th className="border-b border-line px-4 py-2.5">Business</th>
            <th className="hidden border-b border-line px-4 py-2.5 md:table-cell">
              Status
            </th>
            <th className="hidden border-b border-line px-4 py-2.5 md:table-cell">
              Updated
            </th>
            <th className="border-b border-line px-4 py-2.5" />
          </tr>
        </thead>
        <tbody>
          {apps.map((app) => (
            <tr key={app.id} className="hover:bg-surface-2">
              <td className="border-b border-line px-4 py-3.5 align-middle">
                <Link
                  to={`/app/applications/${app.id}`}
                  className="font-mono text-[13px] font-semibold text-text hover:text-primary"
                >
                  {app.reference_no}
                </Link>
                <div className="text-xs text-text-3">
                  {app.revision_count > 0
                    ? `Revision ${app.revision_count}`
                    : `${app.percent}% complete`}
                </div>
                <div className="mt-1 md:hidden">
                  <StatusBadge
                    label={app.status_label}
                    tone={app.status_tone}
                  />
                </div>
              </td>
              <td className="border-b border-line px-4 py-3.5 align-middle">
                <div className="font-medium">
                  {app.business_name ?? "Business name not entered yet"}
                </div>
                <div className="truncate text-xs text-text-3">
                  {app.premises_summary ?? app.licence_title}
                </div>
              </td>
              <td className="hidden border-b border-line px-4 py-3.5 align-middle md:table-cell">
                <StatusBadge label={app.status_label} tone={app.status_tone} />
              </td>
              <td className="hidden border-b border-line px-4 py-3.5 align-middle tabular-nums md:table-cell">
                {formatDateTime(app.updated_at)}
              </td>
              <td className="border-b border-line px-4 py-3.5 text-right align-middle">
                <Link
                  to={`/app/applications/${app.id}`}
                  className="inline-flex h-8 items-center rounded-md border border-line-strong bg-surface px-3 text-[13px] font-semibold text-text no-underline hover:bg-surface-2"
                >
                  {rowAction(app)}
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function OperatorDashboardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const apps = useApplications();
  const create = useCreateApplication();
  const firstName = user?.full_name.split(" ").slice(-2).join(" ") ?? "";

  const newApplication = (
    <Button
      loading={create.isPending}
      onClick={() =>
        create.mutate(undefined, {
          onSuccess: (view) => navigate(`/app/applications/${view.id}`),
        })
      }
    >
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        aria-hidden="true"
      >
        <path d="M12 5v14M5 12h14" />
      </svg>
      New application
    </Button>
  );

  return (
    <>
      <PageHeader
        title={`Good day, ${firstName}`}
        subtitle="Here is what needs your attention today."
        actions={newApplication}
      />
      {create.isError ? (
        <div className="mb-4">
          <ErrorPanel error={create.error} onRetry={() => create.reset()} />
        </div>
      ) : null}
      {apps.isPending ? (
        <div
          className="flex flex-col gap-3 rounded-lg border border-line bg-surface p-5"
          aria-busy="true"
          aria-label="Loading applications"
        >
          <Skeleton className="h-4 w-1/3" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-4/5" />
        </div>
      ) : apps.isError ? (
        <ErrorPanel error={apps.error} onRetry={() => void apps.refetch()} />
      ) : apps.data.length === 0 ? (
        <EmptyPanel
          title="No applications yet"
          description="Start a new application to apply for a Food Establishment Licence."
          action={newApplication}
        />
      ) : (
        <ApplicationsTable apps={apps.data} />
      )}
    </>
  );
}

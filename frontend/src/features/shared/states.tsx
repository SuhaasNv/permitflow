import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { AppError } from "@/api/client";
import { Button } from "./Button";

interface PanelProps {
  icon: ReactNode;
  title: string;
  description: string;
  action?: ReactNode;
  tone?: "neutral" | "error";
}

function Panel({
  icon,
  title,
  description,
  action,
  tone = "neutral",
}: PanelProps) {
  return (
    <div
      className="rounded-lg border border-line bg-surface px-6 py-10 text-center text-text-2"
      role="status"
    >
      <div
        className={
          tone === "error"
            ? "mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-error-soft text-error"
            : "mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-neutral-soft text-text-3"
        }
      >
        {icon}
      </div>
      <div className="text-[15px] font-semibold text-text">{title}</div>
      <div className="mt-1 text-sm">{description}</div>
      {action ? <div className="mt-4 flex justify-center">{action}</div> : null}
    </div>
  );
}

const LockIcon = (
  <svg
    width="22"
    height="22"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    aria-hidden="true"
  >
    <rect x="3" y="11" width="18" height="11" rx="2" />
    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
  </svg>
);
const XIcon = (
  <svg
    width="22"
    height="22"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    aria-hidden="true"
  >
    <path d="M18 6 6 18M6 6l12 12" />
  </svg>
);
const SearchIcon = (
  <svg
    width="22"
    height="22"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    aria-hidden="true"
  >
    <circle cx="11" cy="11" r="8" />
    <path d="m21 21-4.3-4.3" />
  </svg>
);
const FolderIcon = (
  <svg
    width="22"
    height="22"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    aria-hidden="true"
  >
    <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z" />
  </svg>
);

export function NotAvailableForRole() {
  return (
    <div className="mx-auto max-w-lg px-4 py-10">
      <Panel
        icon={LockIcon}
        title="Not available for your role"
        description="This page is for a different type of account. If you think this is a mistake, contact your administrator."
        action={
          <Link to="/" className="text-sm font-semibold">
            Go to my workspace
          </Link>
        }
      />
    </div>
  );
}

export function NotFoundPanel({
  backTo,
  backLabel,
}: {
  backTo: string;
  backLabel: string;
}) {
  return (
    <Panel
      icon={SearchIcon}
      title="Application not found"
      description="It may have been removed, or the link is incorrect."
      action={
        <Link to={backTo} className="text-sm font-semibold">
          {backLabel}
        </Link>
      }
    />
  );
}

export function ErrorPanel({
  error,
  onRetry,
}: {
  error: unknown;
  onRetry?: () => void;
}) {
  const requestId = error instanceof AppError ? error.requestId : undefined;
  const message =
    error instanceof Error ? error.message : "Something went wrong.";
  return (
    <Panel
      icon={XIcon}
      tone="error"
      title="Could not load this page"
      description={requestId ? `${message} Request ID ${requestId}.` : message}
      action={
        onRetry ? (
          <Button variant="secondary" size="sm" onClick={onRetry}>
            Retry
          </Button>
        ) : undefined
      }
    />
  );
}

export function EmptyPanel({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <Panel
      icon={FolderIcon}
      title={title}
      description={description}
      action={action}
    />
  );
}

export function Skeleton({ className = "" }: { className?: string }) {
  return (
    <div
      className={`animate-pulse rounded bg-neutral-soft ${className}`}
      aria-hidden="true"
    />
  );
}

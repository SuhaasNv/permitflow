import type { InputHTMLAttributes, ReactNode } from "react";
import { forwardRef, useId } from "react";

import { cn } from "@/lib/cn";

export interface FieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  help?: string;
  error?: string;
  required?: boolean;
  trailing?: ReactNode;
}

export const inputClasses = (invalid = false, readOnly = false): string =>
  cn(
    "h-10 w-full rounded-md border bg-surface px-3 text-[15px] text-text transition-[border-color,box-shadow]",
    "focus:border-focus focus:shadow-[0_0_0_3px_rgba(23,92,211,0.18)] focus:outline-none",
    invalid
      ? "border-error shadow-[0_0_0_3px_rgba(180,35,24,0.14)]"
      : "border-line-strong hover:border-[#8f98a6]",
    readOnly && "border-line bg-surface-2 text-text-2",
  );

/** Label + control + help/error. The error is announced (role="alert") and linked via aria-describedby (UX-003). */
export const Field = forwardRef<HTMLInputElement, FieldProps>(function Field(
  { label, help, error, required, trailing, id, className, ...rest },
  ref,
) {
  const autoId = useId();
  const inputId = id ?? autoId;
  const describedBy = error
    ? `${inputId}-error`
    : help
      ? `${inputId}-help`
      : undefined;
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <label
        htmlFor={inputId}
        className="text-[13px] font-semibold leading-[18px]"
      >
        {label}
        {required ? (
          <span className="ml-0.5 text-error" aria-hidden="true">
            *
          </span>
        ) : null}
      </label>
      <div className="relative">
        <input
          ref={ref}
          id={inputId}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          aria-required={required || undefined}
          className={inputClasses(Boolean(error), rest.readOnly)}
          {...rest}
        />
        {trailing ? (
          <span className="pointer-events-none absolute right-3 top-2.5 text-text-3">
            {trailing}
          </span>
        ) : null}
      </div>
      {error ? (
        <div
          id={`${inputId}-error`}
          role="alert"
          className="flex items-center gap-1.5 text-[13px] font-medium text-error"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <path d="m10.3 3.9-8.5 14.6A2 2 0 0 0 3.5 21.5h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
            <path d="M12 9v4M12 17h.01" />
          </svg>
          {error}
        </div>
      ) : help ? (
        <div id={`${inputId}-help`} className="text-[13px] text-text-3">
          {help}
        </div>
      ) : null}
    </div>
  );
});

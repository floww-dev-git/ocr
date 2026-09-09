import { useEffect, useRef, useState } from "react";

import type { Application } from "@/api/contracts";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface NewScrutinyDialogProps {
  /** The applications not already taken up on the rail. */
  available: Application[];
  onStart: (applicationId: string) => void;
  onCancel: () => void;
}

/**
 * The prototype's "New scrutiny" dialog: pick an application out of the queue and
 * take it up. The rail lists only what an officer has actually started, so this is
 * how an application gets onto it.
 *
 * The prototype also offers a blank application to fill in by hand. DI has no
 * create-application endpoint, so that option is left out rather than shown as a
 * choice that cannot be carried through.
 */
export function NewScrutinyDialog({
  available,
  onStart,
  onCancel,
}: NewScrutinyDialogProps) {
  const [chosen, setChosen] = useState<string | null>(
    available[0]?.applicationId ?? null,
  );
  const dialog = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Escape closes, as in the prototype.
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onCancel();
      }
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [onCancel]);

  useEffect(() => {
    // The prototype opens with "Start scrutiny" focused, so Enter takes up the
    // first application without any pointing.
    dialog.current
      ?.querySelector<HTMLButtonElement>('[data-dialog-confirm="true"]')
      ?.focus();
  }, []);

  return (
    <>
      <div
        aria-hidden="true"
        onClick={onCancel}
        className="fixed inset-0 z-40 bg-[var(--scrim)]"
      />
      <div
        ref={dialog}
        role="dialog"
        aria-modal="true"
        aria-label="New scrutiny"
        className={cn(
          "fixed top-1/2 left-1/2 z-45 flex w-[440px] max-w-[calc(100vw-32px)]",
          "-translate-x-1/2 -translate-y-1/2 flex-col gap-3 rounded-[var(--radius-l)]",
          "border border-[color-mix(in_srgb,var(--ai-a)_18%,var(--line))] bg-surface p-5",
          "shadow-(--shadow-float)",
        )}
      >
        <h3 className="text-[16px] font-semibold text-ink">New scrutiny</h3>
        <p className="text-[13px] text-ink-2">
          Pick an application from the queue to take up.
        </p>

        {available.length === 0 ? (
          <p className="text-[13px] text-ink-3">
            Every application in the queue is already on your list.
          </p>
        ) : (
          <ul
            role="list"
            aria-label="Applications in the queue"
            className="flex max-h-[50vh] flex-col gap-1.5 overflow-y-auto"
          >
            {available.map((application) => {
              const on = application.applicationId === chosen;
              return (
                <li key={application.applicationId}>
                  <button
                    type="button"
                    aria-pressed={on}
                    onClick={() => setChosen(application.applicationId)}
                    className={cn(
                      "grid w-full grid-cols-[18px_1fr] items-start gap-2.5 rounded-[var(--radius-m)]",
                      "border p-2.5 text-left transition-colors",
                      on
                        ? "border-ai bg-ai-soft shadow-[0_0_0_3px_color-mix(in_srgb,var(--ai-a)_14%,transparent)]"
                        : "border-line hover:border-line-strong",
                    )}
                  >
                    <span
                      aria-hidden="true"
                      className={cn(
                        "mt-0.5 size-4 rounded-full border-2",
                        on
                          ? "border-ai bg-[radial-gradient(circle,var(--ai-a)_40%,transparent_45%)]"
                          : "border-line-strong",
                      )}
                    />
                    <span className="min-w-0">
                      <span className="id block font-medium text-ink">
                        {application.applicationId}
                      </span>
                      <span className="block text-[12px] text-ink-2">
                        {describeApplication(application)}
                      </span>
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}

        <div className="mt-1 flex justify-end gap-2">
          <Button variant="secondary" onClick={onCancel}>
            Cancel
          </Button>
          <Button
            data-dialog-confirm="true"
            variant="primary"
            disabled={chosen === null}
            onClick={() => {
              if (chosen !== null) {
                onStart(chosen);
              }
            }}
          >
            Start scrutiny
          </Button>
        </div>
      </div>
    </>
  );
}

/** The one-line summary the prototype shows beneath each application id. */
function describeApplication(application: Application): string {
  const fields = application.fieldValues;
  return [
    fields.applicantName,
    fields.proposedUse?.toLowerCase(),
    fields.floors,
    fields.heightM ? `${fields.heightM} m` : null,
    fields.village,
  ]
    .filter((part): part is string => Boolean(part))
    .join(", ");
}

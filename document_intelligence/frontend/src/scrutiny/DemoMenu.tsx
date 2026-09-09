import { FlaskConical } from "lucide-react";
import { useEffect, useRef, useState } from "react";

import type { AadhaarSpecimenScenario } from "@/api/contracts";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const ISSUER_SERVICE_ID = "itd_pan";

/** What the mocked Income Tax service can be told to answer. */
const OUTCOMES: { override: string; label: string }[] = [
  { override: "auto", label: "Answer normally" },
  { override: "pass", label: "Always confirm" },
  { override: "fail", label: "Always disagree" },
  { override: "timeout", label: "Never respond" },
  { override: "server_error", label: "Fail at their end" },
];

interface DemoMenuProps {
  current: string;
  onChoose: (serviceOverrides: Record<string, string>) => void;
  disabled: boolean;
  /** The Aadhaar showcase scenarios, empty when none are available. */
  aadhaarScenarios?: AadhaarSpecimenScenario[];
  /** Load a scenario's specimen and run it. */
  onRunScenario?: (scenario: AadhaarSpecimenScenario) => void;
}

export function DemoMenu({
  current,
  onChoose,
  disabled,
  aadhaarScenarios = [],
  onRunScenario,
}: DemoMenuProps) {
  const [open, setOpen] = useState(false);
  const container = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    const closeOnOutside = (event: MouseEvent) => {
      if (!container.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", closeOnOutside);
    return () => document.removeEventListener("mousedown", closeOnOutside);
  }, [open]);

  return (
    <div ref={container} className="relative">
      <Button
        variant="ghost"
        size="sm"
        aria-haspopup="menu"
        aria-expanded={open}
        disabled={disabled}
        onClick={() => setOpen((shown) => !shown)}
      >
        <FlaskConical />
        Demo
      </Button>

      {open ? (
        <div
          role="menu"
          aria-label="Force an answer from the department"
          className="absolute right-0 z-10 mt-1 w-56 rounded-[var(--radius-m)] border border-line bg-surface p-1 shadow-(--shadow-float)"
        >
          {aadhaarScenarios.length > 0 && onRunScenario ? (
            <>
              <p className="px-2 py-1 text-[12px] font-medium text-ink-3">
                Aadhaar scenarios
              </p>
              {aadhaarScenarios.map((scenario) => (
                <button
                  key={scenario.id}
                  type="button"
                  role="menuitem"
                  title={scenario.demonstrates}
                  onClick={() => {
                    setOpen(false);
                    onRunScenario(scenario);
                  }}
                  className="block w-full rounded-[var(--radius-s)] px-2 py-1.5 text-left text-[13px] text-ink transition-colors hover:bg-surface-3"
                >
                  {scenario.label}
                </button>
              ))}
              <div className="my-1 border-t border-line" />
            </>
          ) : null}
          <p className="px-2 py-1 text-[12px] text-ink-3">
            Force the Income Tax service to answer a certain way, then run the
            analysis again.
          </p>
          {OUTCOMES.map((outcome) => {
            const active =
              current === outcome.override ||
              (outcome.override === "auto" && current.length === 0);
            return (
              <button
                key={outcome.override}
                type="button"
                role="menuitemradio"
                aria-checked={active}
                onClick={() => {
                  setOpen(false);
                  onChoose(
                    outcome.override === "auto"
                      ? {}
                      : { [ISSUER_SERVICE_ID]: outcome.override },
                  );
                }}
                className={cn(
                  "block w-full rounded-[var(--radius-s)] px-2 py-1.5 text-left text-[13px] transition-colors",
                  active ? "bg-ai-soft text-ai-text" : "text-ink hover:bg-surface-3",
                )}
              >
                {outcome.label}
              </button>
            );
          })}
        </div>
      ) : null}
    </div>
  );
}

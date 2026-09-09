import {
  CircleAlert,
  CircleCheck,
  CircleX,
  Clock,
  RefreshCw,
  TriangleAlert,
  Unplug,
} from "lucide-react";
import { useState } from "react";

import type {
  Check,
  CheckGroup,
  CheckResolution,
  CheckStatus,
  DocumentState,
} from "@/api/contracts";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/statusBadge";
import { cn } from "@/lib/utils";
import {
  findRetryableIssuerCheck,
  isOpenCheck,
  offersOnlyManualVerification,
} from "./documentDisplay";
import { readCheckStatus, type Tone } from "./statusVocabulary";

interface ChecksTabProps {
  document: DocumentState;
  busy: boolean;
  onResolveCheck: (checkId: string, action: CheckResolution) => void;
  onRetryVerification: () => void;
}

/**
 * The checks, grouped by the kind of question each one answers, as the prototype
 * groups them: what the document says against the application, what the template
 * expects to be on it, and what the issuing department holds. An officer reading
 * a failure needs to know which of those three it is before anything else.
 */
const GROUPS: { group: CheckGroup; heading: string }[] = [
  { group: "rule", heading: "Rule checks" },
  { group: "structure", heading: "Security features" },
  { group: "external", heading: "External verification" },
  { group: "cross", heading: "Cross-document" },
];

const STATUS_ICONS: Record<CheckStatus, typeof CircleCheck> = {
  pass: CircleCheck,
  warn: TriangleAlert,
  fail: CircleX,
  info: CircleAlert,
  pending: Clock,
  unavailable: Unplug,
};

const TONE_TEXT: Record<Tone, string> = {
  pass: "text-pass",
  warn: "text-warn",
  fail: "text-fail",
  info: "text-info",
  pending: "text-pending",
  unavailable: "text-info",
  neutral: "text-ink-3",
  ai: "text-ai-text",
};

export function ChecksTab({
  document,
  busy,
  onResolveCheck,
  onRetryVerification,
}: ChecksTabProps) {
  if (document.checks.length === 0) {
    return (
      <p className="text-[13px] text-ink-3">
        This document has not been checked yet.
      </p>
    );
  }

  const retryable = findRetryableIssuerCheck(document);

  return (
    <div className="flex flex-col gap-3">
      {GROUPS.map(({ group, heading }) => {
        const inGroup = document.checks.filter((check) => check.group === group);
        if (inGroup.length === 0) {
          return null;
        }
        return (
          <section key={group}>
            <h4 className="text-[12px] font-semibold text-ai-text">{heading}</h4>
            <ul role="list" aria-label={heading} className="mt-0.5 flex flex-col">
              {inGroup.map((check) => (
                <CheckRow
                  key={check.checkId}
                  check={check}
                  busy={busy}
                  onResolve={(action) => onResolveCheck(check.checkId, action)}
                />
              ))}
            </ul>
          </section>
        );
      })}

      {retryable !== null ? (
        <div>
          <Button
            variant="secondary"
            size="sm"
            onClick={onRetryVerification}
            disabled={busy}
          >
            <RefreshCw />
            Ask the department again
          </Button>
        </div>
      ) : null}
    </div>
  );
}

function CheckRow({
  check,
  busy,
  onResolve,
}: {
  check: Check;
  busy: boolean;
  onResolve: (action: CheckResolution) => void;
}) {
  const [showCall, setShowCall] = useState(false);
  // A check the officer verified by hand reads as settled, the way the prototype
  // shows it. The override is still stated in its own tag below, so the machine's
  // verdict is recorded rather than rewritten.
  const shown: CheckStatus = check.manual ? "pass" : check.status;
  const reading = readCheckStatus(shown);
  const machineReading = readCheckStatus(check.status);
  const Icon = STATUS_ICONS[shown] ?? CircleAlert;
  const open = isOpenCheck(check);
  const manualOnly = offersOnlyManualVerification(check);

  return (
    <li
      className={cn(
        "grid grid-cols-[16px_1fr] gap-x-2 py-2",
        check.acknowledged ? "opacity-70" : "",
      )}
    >
      <Icon
        aria-hidden="true"
        className={cn("mt-0.5 size-4 shrink-0", TONE_TEXT[reading.tone])}
      />

      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-1.5">
          <span className="text-[13px] font-medium text-ink">{check.title}</span>
          {/* The badge that used to carry the verdict is gone, so the wording it
              held is kept for anyone reading by ear. */}
          <span className="sr-only">{machineReading.label}</span>
          {check.acknowledged ? (
            <StatusBadge tone="neutral">accepted</StatusBadge>
          ) : null}
          {check.requested ? (
            <StatusBadge tone="neutral">requested from applicant</StatusBadge>
          ) : null}
          {check.manual ? (
            <StatusBadge tone="neutral">verified manually</StatusBadge>
          ) : null}
        </div>

        <p className="text-[13px] text-ink-2">{check.detail}</p>

        {check.issuerCall !== null ? (
          <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-ink-3">
            <span>{check.issuerCall.name}</span>
            <span>{(check.issuerCall.latencyMs / 1000).toFixed(1)} s</span>
            <StatusBadge tone="neutral">mock</StatusBadge>
            <button
              type="button"
              aria-expanded={showCall}
              onClick={() => setShowCall((shown) => !shown)}
              className="text-ai-text underline underline-offset-2 hover:brightness-110"
            >
              {showCall
                ? "Hide request and response"
                : "View request and response"}
            </button>
          </div>
        ) : null}

        {check.issuerCall !== null && showCall ? (
          <dl className="mt-1.5 rounded-[var(--radius-m)] bg-surface-2 p-2.5 text-[12px]">
            <dt className="text-ink-3">
              Sent to <span className="font-mono">{check.issuerCall.endpoint}</span>
            </dt>
            <dd>
              <pre className="mt-0.5 overflow-x-auto font-mono text-[11px] text-ink">
                {JSON.stringify(check.issuerCall.requestPayload, null, 2)}
              </pre>
            </dd>
            <dt className="mt-1.5 text-ink-3">Received</dt>
            <dd>
              <pre className="mt-0.5 overflow-x-auto font-mono text-[11px] text-ink">
                {check.issuerCall.responsePayload === null
                  ? "No answer"
                  : JSON.stringify(check.issuerCall.responsePayload, null, 2)}
              </pre>
            </dd>
          </dl>
        ) : null}

        <div className="mt-1 flex flex-wrap items-center gap-1.5">
          {open ? (
            <>
              <Button
                variant="ghost"
                size="sm"
                disabled={busy}
                onClick={() => onResolve("acknowledged")}
              >
                I have seen this
              </Button>
              <Button
                variant="ghost"
                size="sm"
                disabled={busy}
                onClick={() => onResolve("manual")}
              >
                Verified by hand
              </Button>
              <Button
                variant="ghost"
                size="sm"
                disabled={busy}
                onClick={() => onResolve("requested")}
              >
                Ask the applicant
              </Button>
            </>
          ) : null}

          {manualOnly ? (
            <Button
              variant="ghost"
              size="sm"
              disabled={busy}
              onClick={() => onResolve("manual")}
            >
              Verified by hand
            </Button>
          ) : null}
        </div>
      </div>
    </li>
  );
}

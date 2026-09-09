import { AlertTriangle, Check, Loader2 } from "lucide-react";

import type { AnalysisStep } from "@/api/contracts";
import { cn } from "@/lib/utils";
import {
  readStepsInOrder,
  type AnalysisRunState,
  type StepProgress,
} from "./analysisRunState";

const STEP_LABELS: Record<AnalysisStep, string> = {
  identify: "Identifying the document",
  extract: "Reading the details",
  checks: "Comparing against the application",
  verify: "Asking the issuing department",
};

const STEP_DONE_LABELS: Record<AnalysisStep, string> = {
  identify: "Identified the document",
  extract: "Read the details",
  checks: "Compared against the application",
  verify: "Asked the issuing department",
};

interface LiveActivityProps {
  run: AnalysisRunState;
}

export function LiveActivity({ run }: LiveActivityProps) {
  const steps = readStepsInOrder(run);
  if (!run.running && !run.finished) {
    return null;
  }

  return (
    <section
      aria-label="Analysis progress"
      className="rounded-[var(--radius-l)] border border-line bg-surface p-3"
    >
      <div className="mb-2 flex items-center gap-2">
        <span
          aria-hidden="true"
          className={cn(
            "ai-gradient size-5 rounded-full",
            run.running && "animate-pulse",
          )}
        />
        <h2 className="text-[13px] font-semibold text-ink">
          {run.running ? "Reading the documents" : "Finished reading"}
        </h2>
      </div>

      <ol role="list" className="flex flex-col gap-1.5">
        {steps.map((step) => (
          <StepRow key={step.step} step={step} />
        ))}
        {steps.length === 0 ? (
          <li className="text-[13px] text-ink-3">Starting…</li>
        ) : null}
      </ol>

      {run.problems.length > 0 ? (
        <ul role="list" className="mt-2.5 flex flex-col gap-1.5">
          {run.problems.map((problem, index) => (
            <li
              // Messages can legitimately repeat across documents, so position
              // is the only honest identity here.
              key={`${problem}-${index}`}
              className="flex items-start gap-2 rounded-[var(--radius-m)] bg-warn-soft px-2.5 py-2 text-[13px] text-warn"
            >
              <AlertTriangle aria-hidden="true" className="mt-0.5 size-4 shrink-0" />
              <span>{problem}</span>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

function StepRow({ step }: { step: StepProgress }) {
  const running = step.state === "running";
  return (
    <li className="flex items-center gap-2 text-[13px]">
      {running ? (
        <Loader2 aria-hidden="true" className="size-4 shrink-0 animate-spin text-ai" />
      ) : (
        <Check aria-hidden="true" className="size-4 shrink-0 text-pass" />
      )}
      <span className={running ? "text-ink" : "text-ink-2"}>
        {running ? STEP_LABELS[step.step] : STEP_DONE_LABELS[step.step]}
      </span>
      {step.checkCount !== null && step.state === "done" ? (
        <span className="text-ink-3">
          {step.checkCount} {step.checkCount === 1 ? "check" : "checks"}
        </span>
      ) : null}
      <span className="sr-only">{running ? "in progress" : "finished"}</span>
    </li>
  );
}

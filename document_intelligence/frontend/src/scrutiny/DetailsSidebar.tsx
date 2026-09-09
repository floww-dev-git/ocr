import { ChevronDown } from "lucide-react";
import { FileText } from "lucide-react";
import { useState } from "react";

import type {
  Application,
  DocumentState,
  ScrutinySummary,
  ThreadStatus,
} from "@/api/contracts";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/ui/statusBadge";
import { cn } from "@/lib/utils";
import {
  APPLICATION_FIELDS,
  APPLICATION_FIELD_GROUPS,
  readFieldDisplay,
} from "./applicationFields";
import {
  buildChecklist,
  checklistCounts,
  type ChecklistRow,
} from "./requiredDocuments";
import type { Tone } from "./statusVocabulary";

interface DetailsSidebarProps {
  application: Application | null;
  summary: ScrutinySummary | null;
  /** The documents read in the open thread, which settle rows of the checklist. */
  documents: DocumentState[];
  /** Something has been read, so a note can be drawn from it. */
  canWriteNote?: boolean;
  writingNote?: boolean;
  onWriteNote?: () => void;
}

/**
 * The right pane, in the prototype's two collapsible sections: the scrutiny
 * checklist of documents this application must carry on top, the application on
 * record below. Both sections match index.html's layout; the values are read-only,
 * because DI's application record is fixed reference data with nothing on the
 * server to save an edit against.
 */
export function DetailsSidebar({
  application,
  summary,
  documents,
  canWriteNote = false,
  writingNote = false,
  onWriteNote,
}: DetailsSidebarProps) {
  return (
    <aside
      aria-label="Application details"
      className="flex h-full w-(--sidebar-w) shrink-0 flex-col overflow-hidden border-l border-line bg-surface"
    >
      <DocumentsSection application={application} documents={documents} />
      <ApplicationSection
        application={application}
        summary={summary}
        canWriteNote={canWriteNote}
        writingNote={writingNote}
        onWriteNote={onWriteNote}
      />
    </aside>
  );
}

interface SectionProps {
  title: string;
  meta: string | null;
  head?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
}

function Section({ title, meta, head, children, className }: SectionProps) {
  const [collapsed, setCollapsed] = useState(false);
  return (
    <section
      className={cn("flex min-h-0 flex-col border-b border-line last:border-b-0", className)}
    >
      <button
        type="button"
        aria-expanded={!collapsed}
        aria-label={`${collapsed ? "Expand" : "Collapse"} the ${title} list`}
        onClick={() => setCollapsed((current) => !current)}
        className="flex shrink-0 items-center gap-2 border-b border-line bg-surface px-3.5 py-3 text-left"
      >
        <h2 className="text-[13px] font-semibold text-ink">{title}</h2>
        {meta ? <span className="text-[12px] text-ink-3">{meta}</span> : null}
        <ChevronDown
          aria-hidden="true"
          className={cn(
            "ml-auto size-4 text-ink-3 transition-transform",
            collapsed ? "-rotate-90" : "",
          )}
        />
      </button>
      {collapsed ? null : (
        <div className="min-h-0 flex-1 overflow-y-auto p-2.5">
          {head}
          {children}
        </div>
      )}
    </section>
  );
}

// The dot colour for each checklist row, matching the prototype's palette.
const CHECKLIST_DOT_CLASS: Record<Tone, string> = {
  pass: "bg-pass",
  warn: "bg-warn",
  fail: "bg-fail",
  info: "bg-info",
  pending: "bg-pending",
  unavailable: "bg-pending",
  neutral: "bg-pending",
  ai: "bg-ai",
};

function checklistStatusText(row: ChecklistRow): string {
  switch (row.status) {
    case "provided":
      return "Provided";
    case "review":
      return `${row.reviewCount} to review`;
    case "missing":
      return "Missing";
    case "optional":
      return "Optional";
  }
}

// The status text tone, so "Missing" reads red, "N to review" warn/red, "Provided"
// plain and "Optional" muted — as in the prototype.
function checklistStatusToneClass(row: ChecklistRow): string {
  if (row.status === "review") {
    return row.tone === "fail" ? "text-fail" : "text-warn";
  }
  if (row.status === "missing") {
    return "text-fail";
  }
  return "text-ink-3";
}

/**
 * The scrutiny checklist: every document this application is expected to carry,
 * required or optional, each row settling as its document is read. Before an
 * application is picked there is nothing to require, so a short prompt stands in.
 */
function DocumentsSection({
  application,
  documents,
}: {
  application: Application | null;
  documents: DocumentState[];
}) {
  if (application === null) {
    return (
      <Section title="Documents" meta={null} className="max-h-[62%]">
        <p className="px-1 py-1 text-[13px] text-ink-3">
          Pick an application to see the documents it needs.
        </p>
      </Section>
    );
  }

  const rows = buildChecklist(application.fieldValues, documents);
  const { requiredCount, providedRequiredCount } = checklistCounts(
    application.fieldValues,
    documents,
  );

  return (
    <Section
      title="Documents"
      meta={`${providedRequiredCount} of ${requiredCount} required`}
      className="max-h-[62%]"
    >
      <ul
        role="list"
        aria-label="Documents under scrutiny"
        className="flex flex-col gap-0.5"
      >
        {rows.map((row) => (
          <li
            key={row.typeId}
            title={row.reason}
            className="flex items-center gap-2 rounded-[var(--radius-s)] px-1.5 py-1 text-[13px]"
          >
            <span
              aria-hidden="true"
              className={cn("size-2 shrink-0 rounded-full", CHECKLIST_DOT_CLASS[row.tone])}
            />
            <span className="min-w-0 flex-1 truncate text-ink">{row.label}</span>
            <span className={cn("shrink-0 text-[12px]", checklistStatusToneClass(row))}>
              {checklistStatusText(row)}
            </span>
          </li>
        ))}
      </ul>
    </Section>
  );
}

const STATUS_PILL: Record<ThreadStatus, { tone: "pass" | "warn" | "neutral"; label: string }> =
  {
    clear: { tone: "pass", label: "Clear" },
    attention: { tone: "warn", label: "Needs attention" },
    running: { tone: "neutral", label: "Analyzing" },
    new: { tone: "neutral", label: "Under scrutiny" },
  };

/**
 * The check tally, as the prototype states it: how many agreed, how many want a
 * look, how many disagreed, and how many are only there to be noted. Four plain
 * counts, because that is the question an officer asks of a whole application.
 */
function ChecksTally({ summary }: { summary: ScrutinySummary }) {
  const counts: { label: string; value: number; tone: string }[] = [
    { label: "passed", value: summary.statusCounts.pass ?? 0, tone: "text-pass" },
    { label: "warnings", value: summary.statusCounts.warn ?? 0, tone: "text-warn" },
    { label: "failed", value: summary.statusCounts.fail ?? 0, tone: "text-fail" },
    { label: "to note", value: summary.statusCounts.info ?? 0, tone: "text-info" },
  ];
  return (
    <div>
      <p className="mx-1 mb-1 text-[11px] font-medium text-ink-3">Checks</p>
      <dl className="grid grid-cols-2 gap-x-2 gap-y-1 px-1">
        {counts.map((count) => (
          <div key={count.label} className="flex items-baseline gap-1.5">
            <dd className={cn("text-[20px] font-semibold", count.tone)}>
              {count.value}
            </dd>
            <dt className="text-[12px] text-ink-3">{count.label}</dt>
          </div>
        ))}
      </dl>
    </div>
  );
}

function ApplicationSection({
  application,
  summary,
  canWriteNote,
  writingNote,
  onWriteNote,
}: {
  application: Application | null;
  summary: ScrutinySummary | null;
  canWriteNote: boolean;
  writingNote: boolean;
  onWriteNote?: () => void;
}) {
  if (application === null) {
    return (
      <Section title="Application details" meta={null}>
        <p className="px-1 text-[13px] text-ink-3">No application selected.</p>
      </Section>
    );
  }
  const pill =
    summary !== null ? STATUS_PILL[summary.threadStatus] : STATUS_PILL.new;
  return (
    <Section
      title="Application details"
      meta={null}
      head={
        <>
          <div className="mb-2 flex items-center gap-2 px-1">
            <span className="id font-medium text-ink">
              {application.applicationId}
            </span>
            <StatusBadge tone={pill.tone}>{pill.label}</StatusBadge>
          </div>
          {summary !== null ? <ChecksTally summary={summary} /> : null}
          {canWriteNote && onWriteNote !== undefined ? (
            <Button
              variant="primary"
              className="mt-2 mb-1 w-full"
              onClick={onWriteNote}
              disabled={writingNote}
            >
              <FileText />
              {writingNote ? "Writing the note…" : "Write scrutiny note"}
            </Button>
          ) : null}
        </>
      }
    >
      <dl className="flex flex-col">
        {APPLICATION_FIELD_GROUPS.map((group) => (
          <div key={group}>
            <p className="mx-1.5 mt-2 mb-0.5 text-[11px] font-medium text-ink-3">
              {group}
            </p>
            {APPLICATION_FIELDS.filter((field) => field.group === group).map(
              (field) => {
                const shown = readFieldDisplay(
                  field,
                  application.fieldValues[field.key],
                );
                return (
                  <div
                    key={field.key}
                    className="grid grid-cols-[108px_1fr] items-start gap-2 rounded-[var(--radius-s)] px-1.5 py-1"
                  >
                    <dt className="pt-px text-[12px] text-ink-3">{field.label}</dt>
                    <dd
                      className={cn(
                        "min-h-5 text-[13px] break-words",
                        shown.empty ? "text-ink-3 italic" : "text-ink",
                        field.kind === "id" && !shown.empty ? "id" : "",
                      )}
                    >
                      {shown.text}
                    </dd>
                  </div>
                );
              },
            )}
          </div>
        ))}
      </dl>
    </Section>
  );
}

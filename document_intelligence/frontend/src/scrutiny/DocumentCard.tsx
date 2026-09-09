import type { CheckResolution, DocumentState } from "@/api/contracts";
import { StatusBadge } from "@/components/ui/statusBadge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ChecksTab } from "./ChecksTab";
import { FieldsTab } from "./FieldsTab";
import { PreviewTab } from "./PreviewTab";
import { DeedRecordPanel } from "./DeedRecordPanel";
import { cn } from "@/lib/utils";
import {
  countOpenChecks,
  formatConfidence,
  isBeingRead,
  readPageRange,
  readWorstOpenStatus,
} from "./documentDisplay";
import { readDocumentStatus, readStageLabel } from "./statusVocabulary";

/** How an outstanding count is coloured: red disagrees, amber wants a look. */
const OPEN_PILL_TONES: Record<string, string> = {
  fail: "bg-fail-soft text-fail",
  unavailable: "bg-info-soft text-info",
  warn: "bg-warn-soft text-warn",
  info: "bg-info-soft text-info",
};

export interface DocumentCardActions {
  onEditField: (documentId: string, fieldKey: string, value: string) => void;
  onConfirmFields: (documentId: string) => void;
  onResolveCheck: (checkId: string, action: CheckResolution) => void;
  onRetryVerification: (documentId: string) => void;
}

interface DocumentCardProps extends DocumentCardActions {
  document: DocumentState;
  busy: boolean;
}

export function DocumentCard({
  document,
  busy,
  onEditField,
  onConfirmFields,
  onResolveCheck,
  onRetryVerification,
}: DocumentCardProps) {
  const reading = readDocumentStatus(document.status);
  const open = countOpenChecks(document);
  const worstOpen = readWorstOpenStatus(document);
  const pageRange = readPageRange(document);
  // While the backend is reading, it refuses officer actions with 409, so the
  // controls are disabled rather than offered and then rejected.
  const locked = busy || isBeingRead(document);

  return (
    <article
      aria-label={document.filename}
      className="rounded-[var(--radius-l)] border border-line bg-surface p-3"
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="min-w-0 flex-1">
          <span className="block truncate text-[14px] font-semibold text-ink">
            {document.documentTypeId === null
              ? document.filename
              : document.documentTypeLabel}
          </span>
          <span className="block truncate font-mono text-[12px] text-ink-3">
            {document.filename}
            {pageRange ? (
              <span className="ml-1.5 text-ink-3">· {pageRange}</span>
            ) : null}
          </span>
        </span>

        {document.documentTypeId !== null && document.typeConfidence > 0 ? (
          <StatusBadge tone="neutral">
            Identified at {formatConfidence(document.typeConfidence)}
          </StatusBadge>
        ) : null}
        {document.confirmed ? (
          <StatusBadge tone="neutral">Signed off</StatusBadge>
        ) : null}
        <StatusBadge tone={reading.tone}>{reading.label}</StatusBadge>
      </div>

      {isBeingRead(document) ? (
        <p className="mt-1.5 text-[13px] text-ai-text">
          {readStageLabel(document.stage)}…
        </p>
      ) : null}

      {!document.implemented && document.documentTypeId !== null ? (
        <p className="mt-2 rounded-[var(--radius-m)] bg-warn-soft px-2.5 py-2 text-[13px] text-warn">
          This system does not yet read {document.documentTypeLabel}. It has been
          left for you to check by hand.
        </p>
      ) : null}

      {document.deedRecord !== null ? (
        <DeedRecordPanel deedRecord={document.deedRecord} />
      ) : null}

      <Tabs defaultValue="fields" className="mt-3">
        <TabsList>
          <TabsTrigger value="fields">
            Fields
            {document.fieldValues.length > 0 ? (
              <span className="text-ink-3">{document.fieldValues.length}</span>
            ) : null}
          </TabsTrigger>
          <TabsTrigger value="checks">
            Checks
            {/* Coloured by the gravest thing still waiting, so the count says how
                serious it is and not merely how much of it there is. */}
            {open > 0 ? (
              <span
                title={`${open} still to settle`}
                className={cn(
                  "rounded-full px-[7px] py-px text-[11px] font-semibold",
                  OPEN_PILL_TONES[worstOpen ?? "warn"],
                )}
              >
                {open}
              </span>
            ) : null}
          </TabsTrigger>
          <TabsTrigger value="preview">Preview</TabsTrigger>
        </TabsList>

        <TabsContent value="fields">
          <FieldsTab
            document={document}
            busy={locked}
            onEditField={(fieldKey, value) =>
              onEditField(document.documentId, fieldKey, value)
            }
            onConfirmFields={() => onConfirmFields(document.documentId)}
          />
        </TabsContent>

        <TabsContent value="checks">
          <ChecksTab
            document={document}
            busy={locked}
            onResolveCheck={onResolveCheck}
            onRetryVerification={() => onRetryVerification(document.documentId)}
          />
        </TabsContent>

        <TabsContent value="preview">
          <PreviewTab document={document} />
        </TabsContent>
      </Tabs>
    </article>
  );
}

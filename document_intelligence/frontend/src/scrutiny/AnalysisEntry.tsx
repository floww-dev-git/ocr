import type { DocumentState } from "@/api/contracts";
import { groupDocuments, type DocumentGroup } from "./analysisRunState";
import { DocumentCard, type DocumentCardActions } from "./DocumentCard";
import { LiveActivity } from "./LiveActivity";
import { OwnershipReportView } from "./OwnershipReportView";
import type { AnalysisEntry } from "./transcript";

interface AnalysisEntryProps extends DocumentCardActions {
  entry: AnalysisEntry;
  documentsById: Record<string, DocumentState>;
  busy: boolean;
}

/**
 * One run: the steps it took, then — for a thread of registered deeds — the chain
 * of title traced across them, then the documents that evidence it. Kept together
 * so the progress an officer is reading always belongs to the cards beneath it.
 *
 * The chain sits ABOVE the cards deliberately. It is the conclusion the run was
 * for; the per-deed cards are the working. Behind three deeds and thirty checks it
 * was being missed entirely.
 *
 * A bundled file shows its child deeds nested beneath it, because that is how the
 * officer attached them: one file that turned out to hold several documents.
 */
export function AnalysisEntryView({
  entry,
  documentsById,
  busy,
  ...actions
}: AnalysisEntryProps) {
  const documents = entry.documentIds
    .map((documentId) => documentsById[documentId])
    .filter((document): document is DocumentState => document !== undefined);
  const groups = groupDocuments(documents);

  return (
    <div className="flex flex-col gap-3">
      <LiveActivity run={entry.run} />
      {entry.run.ownershipReport !== null ? (
        <OwnershipReportView
          report={entry.run.ownershipReport}
          documentsById={documentsById}
        />
      ) : null}
      {groups.map((group) => (
        <DocumentGroupView
          key={group.document.documentId}
          group={group}
          busy={busy}
          {...actions}
        />
      ))}
    </div>
  );
}

interface DocumentGroupProps extends DocumentCardActions {
  group: DocumentGroup;
  busy: boolean;
}

function DocumentGroupView({ group, busy, ...actions }: DocumentGroupProps) {
  return (
    <div className="flex flex-col gap-3">
      <DocumentCard document={group.document} busy={busy} {...actions} />
      {group.children.length > 0 ? (
        <div className="flex flex-col gap-3 border-l-2 border-line pl-3">
          {group.children.map((child) => (
            <DocumentCard
              key={child.documentId}
              document={child}
              busy={busy}
              {...actions}
            />
          ))}
        </div>
      ) : null}
    </div>
  );
}

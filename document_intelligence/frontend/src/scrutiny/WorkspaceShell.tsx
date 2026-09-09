import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { ApiError } from "@/api/apiError";
import type {
  AadhaarSpecimenScenario,
  AnalysisEvent,
  Application,
  DocumentState,
  ScrutinySummary,
  ScrutinyThread,
} from "@/api/contracts";
import { scrutinyApi } from "@/api/scrutinyApi";

import { AnalysisEntryView } from "./AnalysisEntry";
import { AttachmentEntryView } from "./AttachmentEntry";
import { Composer } from "./Composer";
import { DetailsSidebar } from "./DetailsSidebar";
import { DropOverlay } from "./DropOverlay";
import { NewScrutinyDialog } from "./NewScrutinyDialog";
import { NoteEntryView } from "./NoteEntry";
import { Orb } from "./Orb";
import { ThreadRail, type RailThreadState } from "./ThreadRail";
import { TopBar } from "./TopBar";
import { readApplicationHeadline } from "./applicationSummary";
import { removeStaged, stageFiles, type StagedFile } from "./stagedFiles";
import {
  addProblemToAnalysis,
  appendAnalysis,
  appendAttachment,
  appendNote,
  applyEventToAnalysis,
  greetingEntry,
  mintEntryId,
  readGreeting,
  settleAnalysis,
  type TranscriptEntry,
} from "./transcript";
import { readUploadRejection } from "./uploadMessages";
import { useAnalysisStream } from "./useAnalysisStream";
import { useApplications } from "./useApplications";
import { useFileDrop } from "./useFileDrop";
import { useOfficerActions } from "./useOfficerActions";
import { useStickToBottom } from "./useStickToBottom";
import { useTheme } from "./useTheme";

export function WorkspaceShell() {
  const { theme, toggleTheme } = useTheme();
  const { applications, loading: loadingApplications, loadError } = useApplications();
  const [notice, setNotice] = useState<string | null>(null);
  const [thread, setThread] = useState<ScrutinyThread | null>(null);
  const [entries, setEntries] = useState<TranscriptEntry[]>([]);
  const [documentsById, setDocumentsById] = useState<Record<string, DocumentState>>(
    {},
  );
  const [summary, setSummary] = useState<ScrutinySummary | null>(null);
  const [staged, setStaged] = useState<StagedFile[]>([]);
  const [aadhaarScenarios, setAadhaarScenarios] = useState<
    AadhaarSpecimenScenario[]
  >([]);
  const [runningAnalysisId, setRunningAnalysisId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [writingNote, setWritingNote] = useState(false);
  const [railCollapsed, setRailCollapsed] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  // Per-application rail state the backend does not hold: when it was last opened
  // and an officer's rename. The prototype keeps the same in the browser; DI layers
  // it over the read-only application list.
  const [railState, setRailState] = useState<Record<string, RailThreadState>>({});
  // The rail lists only the applications an officer has taken up, in the order they
  // took them. Empty to begin with: the queue is not the officer's workload until
  // they choose from it.
  const [addedApplicationIds, setAddedApplicationIds] = useState<string[]>([]);
  const [pickerOpen, setPickerOpen] = useState(false);

  const threadId = thread?.threadId ?? null;
  // Read inside stream callbacks, which are created before the run exists.
  const activeAnalysis = useRef<string | null>(null);

  const takeDocument = useCallback((incoming: DocumentState) => {
    setDocumentsById((current) => ({ ...current, [incoming.documentId]: incoming }));
  }, []);

  const onEvent = useCallback(
    (event: AnalysisEvent) => {
      const id = activeAnalysis.current;
      if (id === null) {
        return;
      }
      if (event.type === "doc") {
        takeDocument(event.payload);
      }
      if (event.type === "summary") {
        setSummary(event.payload);
      }
      setEntries((current) => applyEventToAnalysis(current, id, event));
    },
    [takeDocument],
  );

  const { start, abort } = useAnalysisStream({
    threadId,
    onEvent,
    onFailure: useCallback((message: string) => {
      const id = activeAnalysis.current;
      if (id !== null) {
        setEntries((current) => addProblemToAnalysis(current, id, message));
      }
    }, []),
    onSettled: useCallback(() => {
      const id = activeAnalysis.current;
      if (id !== null) {
        setEntries((current) => settleAnalysis(current, id));
      }
      activeAnalysis.current = null;
      setRunningAnalysisId(null);
    }, []),
  });

  const actions = useOfficerActions({
    threadId,
    // Updates the document where it already sits: the card belongs to the run
    // that produced it, and moving it would falsify the order of events.
    onDocument: takeDocument,
    onSummary: setSummary,
  });

  const openThread = useCallback(
    async (applicationId: string) => {
      try {
        const opened = await scrutinyApi.createThread(applicationId);
        abort();
        activeAnalysis.current = null;
        setRunningAnalysisId(null);
        const applicantName =
          applications.find(
            (application) => application.applicationId === applicationId,
          )?.fieldValues.applicantName ?? null;
        // Opening a thread is never empty: it starts with the greeting, as the
        // prototype does, so the officer is told what to do next.
        setEntries([greetingEntry(readGreeting(applicationId, applicantName))]);
        setDocumentsById({});
        setSummary(null);
        setStaged([]);
        setNotice(null);
        setThread(opened);
        setRailState((current) => ({
          ...current,
          [applicationId]: {
            ...current[applicationId],
            status: current[applicationId]?.status ?? "new",
            openCount: current[applicationId]?.openCount ?? 0,
            openedAt: Date.now(),
            title: current[applicationId]?.title ?? null,
          },
        }));
      } catch (error: unknown) {
        setNotice("That scrutiny could not be opened.");
        reportUnexpected(error);
      }
    },
    [abort, applications],
  );

  const stage = useCallback((files: File[]) => {
    if (files.length === 0) {
      return;
    }
    setStaged((current) => stageFiles(current, files));
    setNotice(null);
  }, []);

  const verify = useCallback(async () => {
    if (threadId === null) {
      return;
    }
    setBusy(true);
    try {
      if (staged.length > 0) {
        const filenames = staged.map((item) => item.file.name);
        const attached = await scrutinyApi.addDocuments(
          threadId,
          staged.map((item) => item.file),
        );
        for (const document of attached) {
          takeDocument(document);
        }
        // Only cleared once the upload was accepted, so a rejected batch stays
        // on the tray for the officer to fix.
        setStaged([]);
        setEntries((current) => appendAttachment(current, filenames));
      }
      setNotice(null);
      // Minted first: the stream's callbacks read this ref, and the first frame
      // can arrive before a state updater would have run.
      const analysisId = mintEntryId("analysis");
      activeAnalysis.current = analysisId;
      setRunningAnalysisId(analysisId);
      setEntries((current) => appendAnalysis(current, analysisId));
      start();
    } catch (error: unknown) {
      setNotice(readUploadRejection(error));
      if (!(error instanceof ApiError)) {
        reportUnexpected(error);
      }
    } finally {
      setBusy(false);
    }
  }, [staged, start, takeDocument, threadId]);

  const runScenario = useCallback(
    async (scenario: AadhaarSpecimenScenario) => {
      if (threadId === null) {
        return;
      }
      setBusy(true);
      try {
        const file = await scrutinyApi.fetchAadhaarSpecimen(scenario.filename);
        const attached = await scrutinyApi.addDocuments(threadId, [file]);
        for (const document of attached) {
          takeDocument(document);
        }
        setEntries((current) => appendAttachment(current, [file.name]));
        setNotice(null);
        const analysisId = mintEntryId("analysis");
        activeAnalysis.current = analysisId;
        setRunningAnalysisId(analysisId);
        setEntries((current) => appendAnalysis(current, analysisId));
        start();
      } catch (error: unknown) {
        setNotice("That demo scenario could not be loaded.");
        reportUnexpected(error);
      } finally {
        setBusy(false);
      }
    },
    [start, takeDocument, threadId],
  );

  const writeNote = useCallback(async () => {
    if (threadId === null) {
      return;
    }
    setWritingNote(true);
    try {
      const note = await scrutinyApi.getNote(threadId);
      setEntries((current) => appendNote(current, note.text));
      setNotice(null);
    } catch (error: unknown) {
      setNotice("The scrutiny note could not be produced.");
      reportUnexpected(error);
    } finally {
      setWritingNote(false);
    }
  }, [threadId]);

  const chooseServiceOverride = useCallback(
    async (serviceOverrides: Record<string, string>) => {
      if (threadId === null) {
        return;
      }
      try {
        setThread(
          await scrutinyApi.updateServiceOverrides({ threadId, serviceOverrides }),
        );
        setNotice(null);
      } catch (error: unknown) {
        setNotice("That demo setting could not be applied.");
        reportUnexpected(error);
      }
    },
    [threadId],
  );

  const { dragging, handlers } = useFileDrop(stage);
  const { scroller, onScroll } = useStickToBottom(entries);

  // The demo scenarios are optional: when the specimens have not been generated the
  // endpoint returns none and the picker simply does not show.
  useEffect(() => {
    const controller = new AbortController();
    scrutinyApi
      .listAadhaarSpecimens(controller.signal)
      .then(setAadhaarScenarios)
      .catch(() => {
        // A demo convenience, not core: a failure here leaves the picker hidden.
      });
    return () => controller.abort();
  }, []);

  const selectedApplication = useMemo(
    () =>
      applications.find(
        (application) => application.applicationId === thread?.applicationId,
      ) ?? null,
    [applications, thread?.applicationId],
  );

  // Fold the open thread's live status and open-item count into its rail row, so
  // its dot and count pill track the analysis. Other rows stay at their last known
  // state (or "pending" until first opened), as the prototype shows them.
  const applicationId = thread?.applicationId ?? null;
  useEffect(() => {
    if (applicationId === null || summary === null) {
      return;
    }
    setRailState((current) => ({
      ...current,
      [applicationId]: {
        ...current[applicationId],
        status: summary.threadStatus,
        openCount: summary.openItems.length,
        openedAt: current[applicationId]?.openedAt ?? Date.now(),
        title: current[applicationId]?.title ?? null,
      },
    }));
  }, [applicationId, summary]);

  const renameThread = useCallback((id: string, title: string) => {
    setRailState((current) => ({
      ...current,
      [id]: {
        status: current[id]?.status ?? "new",
        openCount: current[id]?.openCount ?? 0,
        openedAt: current[id]?.openedAt ?? null,
        title,
      },
    }));
  }, []);

  const removeThread = useCallback(
    (id: string) => {
      setAddedApplicationIds((current) => current.filter((added) => added !== id));
      if (thread?.applicationId === id) {
        abort();
        setThread(null);
        setEntries([]);
        setDocumentsById({});
        setSummary(null);
      }
    },
    [abort, thread?.applicationId],
  );

  const takeUpApplication = useCallback(
    (applicationId: string) => {
      setAddedApplicationIds((current) =>
        current.includes(applicationId) ? current : [...current, applicationId],
      );
      setPickerOpen(false);
      void openThread(applicationId);
    },
    [openThread],
  );

  // Only what the officer took up, in the order they took it.
  const railApplications = useMemo(
    () =>
      addedApplicationIds
        .map((id) =>
          applications.find((application) => application.applicationId === id),
        )
        .filter((application): application is Application => application !== undefined),
    [addedApplicationIds, applications],
  );

  const availableApplications = useMemo(
    () =>
      applications.filter(
        (application) => !addedApplicationIds.includes(application.applicationId),
      ),
    [addedApplicationIds, applications],
  );

  const documents = Object.values(documentsById);
  const running = runningAnalysisId !== null;
  const unread = documents.some((document) => document.stage !== "done");
  const anythingRead = documents.some((document) => document.stage === "done");
  const alert = notice ?? loadError ?? actions.problem;

  return (
    <div className="flex h-full w-full overflow-hidden bg-canvas text-ink">
      {railCollapsed ? null : (
        <ThreadRail
          applications={railApplications}
          selectedApplicationId={thread?.applicationId ?? null}
          onSelectApplication={openThread}
          onCollapse={() => setRailCollapsed(true)}
          loading={loadingApplications}
          threadState={railState}
          onRename={renameThread}
          onDelete={removeThread}
          onNewScrutiny={() => setPickerOpen(true)}
        />
      )}

      <main
        className="relative flex min-w-0 flex-1 flex-col"
        {...(thread === null ? {} : handlers)}
      >
        <TopBar
          applicationId={thread?.applicationId ?? null}
          applicantName={
            selectedApplication
              ? readApplicationHeadline(selectedApplication).applicantName
              : null
          }
          summary={summary}
          theme={theme}
          onToggleTheme={toggleTheme}
          railCollapsed={railCollapsed}
          onOpenRail={() => setRailCollapsed(false)}
          onToggleSidebar={() => setSidebarOpen((open) => !open)}
          serviceOverride={thread?.serviceOverrides.itd_pan ?? ""}
          onChooseServiceOverride={chooseServiceOverride}
          aadhaarScenarios={aadhaarScenarios}
          onRunScenario={(scenario) => void runScenario(scenario)}
          demoDisabled={thread === null || running}
        />

        <section
          ref={scroller as React.RefObject<HTMLElement>}
          onScroll={onScroll}
          aria-label="Scrutiny record"
          className="min-h-0 flex-1 overflow-y-auto"
        >
          <div className="mx-auto flex w-full max-w-(--content-w) flex-col gap-4 px-4 py-6">
            {alert ? (
              <p
                role="alert"
                className="rounded-[var(--radius-m)] bg-fail-soft px-3 py-2 text-[13px] text-fail"
              >
                {alert}
              </p>
            ) : null}

            {thread === null ? <EmptyWorkspace /> : null}

            {entries.map((entry) => {
              if (entry.kind === "greeting") {
                return <GreetingView key={entry.id} text={entry.text} />;
              }
              if (entry.kind === "attachment") {
                return (
                  <AttachmentEntryView key={entry.id} filenames={entry.filenames} />
                );
              }
              if (entry.kind === "note") {
                return <NoteEntryView key={entry.id} text={entry.text} />;
              }
              return (
                <AnalysisEntryView
                  key={entry.id}
                  entry={entry}
                  documentsById={documentsById}
                  busy={actions.busy}
                  onEditField={actions.editField}
                  onConfirmFields={actions.confirmFields}
                  onResolveCheck={actions.resolveCheck}
                  onRetryVerification={actions.retryVerification}
                />
              );
            })}
          </div>
        </section>

        {thread === null ? null : (
          <>
            <Composer
              staged={staged}
              onStage={stage}
              onRemove={(id) => setStaged((current) => removeStaged(current, id))}
              onVerify={() => void verify()}
              busy={busy || running}
              canVerify={staged.length > 0 || unread}
              verifyLabel={running ? "Verifying…" : "Verify"}
            />
          </>
        )}

        <DropOverlay visible={dragging && thread !== null} />
      </main>

      {sidebarOpen ? (
        <DetailsSidebar
          application={selectedApplication}
          summary={summary}
          documents={documents}
          canWriteNote={anythingRead && !running}
          writingNote={writingNote}
          onWriteNote={() => void writeNote()}
        />
      ) : null}

      {pickerOpen ? (
        <NewScrutinyDialog
          available={availableApplications}
          onStart={takeUpApplication}
          onCancel={() => setPickerOpen(false)}
        />
      ) : null}
    </div>
  );
}

function EmptyWorkspace() {
  return (
    <div className="flex flex-col items-center gap-4 py-10 text-center">
      <Orb size={72} />
      <div className="max-w-[520px]">
        <h1 className="text-[20px] font-medium text-balance text-ink">
          Pick an application to begin
        </h1>
        <p className="mt-2 text-[16px] text-ink-2">
          Choose an application from the list. Attach the documents filed with it and
          this workspace reads them, compares them against what the applicant
          declared, and asks the issuing department to confirm what it holds.
        </p>
      </div>
    </div>
  );
}

/**
 * The opening message, centred with the large orb, exactly as the prototype's
 * `msg-greeting`. Its text comes from `readGreeting`, keyed on whether the
 * application is named yet.
 */
function GreetingView({ text }: { text: string }) {
  return (
    <div className="flex flex-col items-center gap-4 py-6 text-center">
      <Orb size={72} />
      <div className="max-w-[520px] text-[16px] whitespace-pre-line text-ink-2">
        {text.split("\n").map((line, index) =>
          index === 0 ? (
            <p key={index} className="text-[20px] font-medium text-balance text-ink">
              {line}
            </p>
          ) : (
            <p key={index} className="mt-2">
              {line}
            </p>
          ),
        )}
      </div>
    </div>
  );
}

function reportUnexpected(error: unknown): void {
  // The officer already has a plain sentence; this is for whoever debugs it.
  console.error(error);
}

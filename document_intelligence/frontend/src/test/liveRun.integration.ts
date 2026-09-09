/**
 * Drives the real frontend modules against a running backend: no fetch stub, no
 * fake stream. Proves the SSE reader, the reducer and the API client agree with
 * what Django actually emits, which unit tests with a scripted body cannot.
 *
 * Needs a backend in MOCK extraction mode. The script attaches a synthetic file,
 * which Gemini rightly refuses to read: against a gemini backend the run stops
 * after `identify` with an unreadable-document error, which is correct behaviour
 * and not what this script is checking.
 *
 *   EXTRACTION_MODE=mock DI_SERVER_PORT=8010 uv run uvicorn config.asgi:application --port 8010
 *   DI_LIVE_BASE=http://127.0.0.1:8010 npm run verify:live
 */
import { applyAnalysisEvent, readStepsInOrder, startRun } from "../scrutiny/analysisRunState";
import { streamAnalysis } from "../scrutiny/streamAnalysis";
import { scrutinyApi } from "../api/scrutinyApi";

const BASE = process.env.DI_LIVE_BASE ?? "http://127.0.0.1:8000";
const APPLICATION_ID = process.env.DI_LIVE_APPLICATION ?? "BN/2026/0377";
const CORRECTED_NAME = "MOHAMMED IRFAN SIDDIQUI";
// The seeded application the four scenario bundles are written over.
const BUNDLE_APPLICATION_ID = "BN/2026/0455";
const BUNDLE_ROW_COUNT = 4; // the file itself plus the three deeds inside it
const BUNDLE_DEED_COUNT = 3;

// The api client uses root-relative paths, as the browser does behind the Vite
// proxy. Here there is no proxy, so they are resolved against the backend.
const nativeFetch = globalThis.fetch;
globalThis.fetch = ((input: RequestInfo | URL, init?: RequestInit) =>
  nativeFetch(
    typeof input === "string" && input.startsWith("/") ? `${BASE}${input}` : input,
    init,
  )) as typeof fetch;

function report(step: string, detail: string) {
  process.stdout.write(`  ${step.padEnd(34)} ${detail}\n`);
}

function assert(condition: boolean, what: string): void {
  if (!condition) {
    throw new Error(`FAILED: ${what}`);
  }
  report("ok", what);
}

async function main() {
  process.stdout.write("\n== live run against the real backend ==\n");

  const applications = await scrutinyApi.getApplications();
  assert(applications.length > 0, "the application list loads");

  const thread = await scrutinyApi.createThread(APPLICATION_ID);
  report("thread", thread.threadId);

  const attached = await scrutinyApi.addDocuments(thread.threadId, [
    new File(["not a real scan"], "pan_card.jpg", { type: "image/jpeg" }),
  ]);
  assert(attached.length === 1, "a document attaches");
  const documentId = attached[0].documentId;

  let run = startRun();
  await streamAnalysis({
    url: scrutinyApi.analyzeUrl(thread.threadId),
    signal: new AbortController().signal,
    onEvent: (event) => {
      run = applyAnalysisEvent(run, event);
    },
  });

  const steps = readStepsInOrder(run).map((step) => step.step);
  assert(
    JSON.stringify(steps) === JSON.stringify(["identify", "extract", "checks", "verify"]),
    `all four steps arrive in order (${steps.join(" -> ")})`,
  );
  assert(run.finished && !run.running, "the run closes itself");
  assert(run.documents.length === 1, "the document is reported");
  assert(run.summary !== null, "a closing summary arrives");
  report("thread status", String(run.summary?.threadStatus));
  report("checks", JSON.stringify(run.summary?.statusCounts));
  assert(
    run.summary?.threadStatus === "attention",
    "the seeded mismatch needs attention",
  );
  assert(run.summary?.openItems.length === 2, "both open items are listed");
  // Five rule checks, three structural, one internal-consistency and the issuer's
  // answer. Pinned as a number so a check quietly disappearing is caught here.
  assert(run.documents[0].checks.length === 10, "ten checks are produced");

  const edit = await scrutinyApi.updateField({
    threadId: thread.threadId,
    documentId,
    fieldKey: "name",
    value: CORRECTED_NAME,
  });
  assert(
    edit.changedCheckIds.length === 1 && edit.changedCheckIds[0].endsWith(":name"),
    "correcting the name changes exactly the name check",
  );
  assert(
    edit.document.checks.find((check) => check.checkId.endsWith(":name"))?.status ===
      "pass",
    "the name check settles",
  );
  assert(
    edit.summary.threadStatus === "attention",
    "the thread stays in attention while the department disagrees",
  );

  const resolved = await scrutinyApi.resolveCheck({
    threadId: thread.threadId,
    checkId: `${documentId}:issuer`,
    action: "manual",
  });
  assert(resolved.check.status === "warn", "the department's verdict is preserved");
  assert(resolved.check.manual, "the officer's override is recorded separately");
  assert(resolved.summary.threadStatus === "clear", "the thread now reads clear");
  assert(
    resolved.document.status === "verified",
    "the document agrees with the thread",
  );

  const confirmed = await scrutinyApi.confirmFields({
    threadId: thread.threadId,
    documentId,
  });
  assert(confirmed.document.confirmed, "the officer can sign the document off");

  const note = await scrutinyApi.getNote(thread.threadId);
  assert(note.text.includes("Fit to proceed"), "the note turns favourable");
  assert(!note.text.includes("Open:"), "the note lists nothing open");

  process.stdout.write("\n== forced timeout path ==\n");
  const second = await scrutinyApi.createThread(APPLICATION_ID);
  await scrutinyApi.updateServiceOverrides({
    threadId: second.threadId,
    serviceOverrides: { itd_pan: "timeout" },
  });
  const secondDocs = await scrutinyApi.addDocuments(second.threadId, [
    new File(["not a real scan"], "pan_card.jpg", { type: "image/jpeg" }),
  ]);
  let timeoutRun = startRun();
  await streamAnalysis({
    url: scrutinyApi.analyzeUrl(second.threadId),
    signal: new AbortController().signal,
    onEvent: (event) => {
      timeoutRun = applyAnalysisEvent(timeoutRun, event);
    },
  });
  const issuer = timeoutRun.documents[0].checks.find(
    (check) => check.group === "external",
  );
  assert(issuer?.status === "unavailable", "an unreachable department reads unavailable");
  report("detail", String(issuer?.detail));
  assert(
    (issuer?.issuerCall?.latencyMs ?? 0) >= 3000,
    "the officer is told how long was waited",
  );

  await scrutinyApi.updateServiceOverrides({
    threadId: second.threadId,
    serviceOverrides: {},
  });
  await scrutinyApi.updateField({
    threadId: second.threadId,
    documentId: secondDocs[0].documentId,
    fieldKey: "name",
    value: CORRECTED_NAME,
  });
  const retried = await scrutinyApi.retryVerification({
    threadId: second.threadId,
    documentId: secondDocs[0].documentId,
  });
  assert(retried.check.status === "pass", "a retry can succeed");
  assert(retried.summary.threadStatus === "clear", "and clears the thread");

  process.stdout.write("\n== bundled deed, chain of title ==\n");
  // A file named as a shipped bundle is segmented by the mock extractor; the real
  // mock registrar answers over HTTP, so the chain is traced end to end with no
  // scripted body — the one thing a unit test with a canned stream cannot prove.
  const deedThread = await scrutinyApi.createThread(BUNDLE_APPLICATION_ID);
  report("thread", deedThread.threadId);
  const bundle = await scrutinyApi.addDocuments(deedThread.threadId, [
    new File(["not a real scan"], "01_clean_chain.pdf", { type: "application/pdf" }),
  ]);
  assert(bundle.length === 1, "one bundle file attaches");

  let deedRun = startRun();
  await streamAnalysis({
    url: scrutinyApi.analyzeUrl(deedThread.threadId),
    signal: new AbortController().signal,
    onEvent: (event) => {
      deedRun = applyAnalysisEvent(deedRun, event);
    },
  });

  assert(deedRun.finished && !deedRun.running, "the bundle run closes itself");
  // One upload becomes the file itself plus the three deeds inside it.
  assert(deedRun.documents.length === BUNDLE_ROW_COUNT, "the file and its deeds are reported");
  const deeds = deedRun.documents.filter((doc) => doc.parentDocumentId !== null);
  assert(deeds.length === BUNDLE_DEED_COUNT, "three registered deeds are segmented out");
  assert(
    deeds.every((deed) => deed.deedRecord !== null),
    "each deed carries the record read from it",
  );

  const report_ = deedRun.ownershipReport;
  assert(report_ !== null, "a chain frame arrives for a thread holding deeds");
  report("chain verdict", `${report_?.verdict.level} / ${report_?.chain.overall}`);
  assert(report_?.verdict.level === "clean", "the clean bundle reads clean");
  assert(report_?.chain.overall === "intact", "and its chain is intact");
  assert(
    report_?.stats.titleDeedCount === BUNDLE_DEED_COUNT,
    "the report counts the three title deeds",
  );
  const currentOwner = report_?.journey.find((entry) => entry.kind === "owner");
  assert(
    currentOwner?.party?.name === "Prakash Iyer",
    "the current owner is the applicant the chain hands title to",
  );

  process.stdout.write("\nALL LIVE CHECKS PASSED\n\n");
}

main().catch((error: unknown) => {
  process.stderr.write(`\n${String(error)}\n\n`);
  process.exit(1);
});

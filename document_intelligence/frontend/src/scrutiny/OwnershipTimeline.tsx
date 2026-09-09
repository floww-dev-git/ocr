import { AlertTriangle, ArrowRight, Check as CheckIcon, X } from "lucide-react";

import type {
  ChainLink,
  ChainOfTitle,
  DeedRecord,
  DocumentState,
} from "@/api/contracts";
import { cn } from "@/lib/utils";
import {
  RUPTURE_FALLBACK,
  SAME_PERSON_LINE,
  isRupture,
  readBannerWord,
  readJoinLabel,
  readLinkCheckQuestion,
  readLinkVerdictTone,
  readRuptureHeading,
} from "./chainVocabulary";
import { readPageRange, readPartyNames } from "./documentDisplay";

/** One deed in the chain, with everything needed to show it on a line. */
interface TimelineDeed {
  ordinal: number;
  documentId: string;
  record: DeedRecord;
  pageRange: string | null;
}

interface OwnershipTimelineProps {
  chain: ChainOfTitle;
  documentsById: Record<string, DocumentState>;
}

/**
 * The chain in the order it happened: oldest deed first, each numbered, with the
 * hand-over between consecutive deeds shown in the gap between them.
 *
 * Chronological rather than newest-first because the question is whether title
 * *travelled* — and a journey is far easier to follow forwards. Where it stopped
 * travelling is drawn in the gap where the hand-over should have been, which is
 * where the break actually lives.
 */
export function OwnershipTimeline({ chain, documentsById }: OwnershipTimelineProps) {
  const deeds = readTimelineDeeds(chain, documentsById);
  if (deeds.length === 0) {
    return null;
  }
  const ordinalsByDocumentId = new Map(
    deeds.map((deed) => [deed.documentId, deed.ordinal]),
  );
  return (
    <div>
      <h4 className="text-[13px] font-semibold text-ink">Ownership timeline</h4>
      <p className="mt-0.5 text-[12px] text-ink-3">
        Every registered deed in the order it was executed, and whether ownership
        carried over between them.
      </p>

      <BreakBanners chain={chain} ordinalsByDocumentId={ordinalsByDocumentId} />

      <ol aria-label="Ownership timeline" className="mt-2 flex flex-col">
        {deeds.map((deed, index) => (
          <li key={deed.documentId}>
            <DeedCard deed={deed} />
            {index < deeds.length - 1 ? (
              <ContinuityJoin
                link={chain.links[index] ?? null}
                fromDeed={deed}
                toDeed={deeds[index + 1]}
              />
            ) : null}
          </li>
        ))}
      </ol>
    </div>
  );
}

/**
 * The deeds the chain traced, in its own order, paired with what was read off
 * each. A deed the chain ordered but whose read never arrived is skipped rather
 * than shown as an empty card — a blank row in a title history invites the reader
 * to assume a missing deed that is really just a missing render.
 */
export function readTimelineDeeds(
  chain: ChainOfTitle,
  documentsById: Record<string, DocumentState>,
): TimelineDeed[] {
  const deeds: TimelineDeed[] = [];
  for (const documentId of chain.orderedDocumentIds) {
    const document = documentsById[documentId];
    if (document === undefined || document.deedRecord === null) {
      continue;
    }
    deeds.push({
      ordinal: deeds.length + 1,
      documentId,
      record: document.deedRecord,
      pageRange: readPageRange(document),
    });
  }
  return deeds;
}

/**
 * The breaks, named up front so the officer knows what they are looking for
 * before they start reading deeds.
 */
function BreakBanners({
  chain,
  ordinalsByDocumentId,
}: {
  chain: ChainOfTitle;
  ordinalsByDocumentId: Map<string, number>;
}) {
  const ruptures = chain.links.filter((link) => isRupture(link.verdict));
  if (ruptures.length === 0) {
    return null;
  }
  return (
    <ul role="list" className="mt-2 flex flex-col gap-1">
      {ruptures.map((link, index) => {
        const from = ordinalsByDocumentId.get(link.fromDocumentId);
        const to = ordinalsByDocumentId.get(link.toDocumentId);
        const tone = readLinkVerdictTone(link.verdict);
        return (
          <li
            key={`${link.fromDocumentId}-${link.toDocumentId}-${index}`}
            className={cn(
              "flex items-center gap-2 rounded-[var(--radius-m)] px-2.5 py-1.5 text-[12px] font-semibold",
              tone === "fail" ? "bg-fail-soft text-fail" : "bg-warn-soft text-warn",
            )}
          >
            <AlertTriangle aria-hidden="true" className="size-3.5 shrink-0" />
            {readBannerWord(link.verdict)}
            {from !== undefined && to !== undefined
              ? ` between Deed ${from} and Deed ${to}`
              : null}
          </li>
        );
      })}
    </ul>
  );
}

function DeedCard({ deed }: { deed: TimelineDeed }) {
  const { record } = deed;
  const sellers = readPartyNames(record.sellers);
  const buyers = readPartyNames(record.buyers);
  const meta = [record.docNo, record.registrationDate, record.considerationText]
    .filter((part): part is string => part !== null && part.length > 0)
    .join(" · ");
  return (
    <div className="flex gap-2.5 rounded-[var(--radius-m)] border border-line bg-surface-2 px-2.5 py-2">
      <span
        aria-hidden="true"
        className="flex size-5 shrink-0 items-center justify-center rounded-full bg-ai-soft text-[11px] font-bold text-ai-text"
      >
        {deed.ordinal}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-baseline gap-2">
          <span className="text-[13px] font-semibold text-ink">
            {record.deedType ?? "Deed"}
          </span>
          {deed.pageRange ? (
            <span className="text-[11px] text-ink-3">· {deed.pageRange}</span>
          ) : null}
        </div>
        <p className="mt-0.5 flex flex-wrap items-center gap-1.5 text-[12px] text-ink">
          <PartyNames named={sellers} />
          <ArrowRight aria-hidden="true" className="size-3.5 shrink-0 text-ink-3" />
          <PartyNames named={buyers} />
        </p>
        {meta ? <p className="mt-0.5 font-mono text-[11px] text-ink-3">{meta}</p> : null}
      </div>
    </div>
  );
}

function PartyNames({ named }: { named: ReturnType<typeof readPartyNames> }) {
  return (
    <span>
      {named.text}
      {named.othersCount > 0 ? (
        <span className="text-ink-3"> &amp; {named.othersCount} more</span>
      ) : null}
    </span>
  );
}

/**
 * The hand-over between two deeds. A healthy one says so; a failed one is stated
 * as a finding, in the gap where the hand-over should have been.
 */
function ContinuityJoin({
  link,
  fromDeed,
  toDeed,
}: {
  link: ChainLink | null;
  fromDeed: TimelineDeed;
  toDeed: TimelineDeed;
}) {
  if (link === null) {
    return <span aria-hidden="true" className="ml-2.5 block h-2 w-0.5 bg-line" />;
  }
  const tone = readLinkVerdictTone(link.verdict);
  if (!isRupture(link.verdict)) {
    return (
      <div className="ml-2.5 flex items-stretch gap-2">
        <span
          aria-hidden="true"
          data-testid={`join-rail-${tone}`}
          className={cn("w-0.5 shrink-0", tone === "pass" ? "bg-pass" : "bg-warn")}
        />
        <p className="py-1 text-[11px]">
          <span className={cn("font-semibold", tone === "pass" ? "text-pass" : "text-warn")}>
            {tone === "pass" ? (
              <CheckIcon aria-hidden="true" className="mr-1 inline size-3" />
            ) : (
              <AlertTriangle aria-hidden="true" className="mr-1 inline size-3" />
            )}
            {readJoinLabel(link.verdict)}
            {` · ${link.identityScore}/100`}
          </span>
          {link.notes.length > 0 ? (
            <span className="ml-1.5 text-ink-3">{link.notes.join(" ")}</span>
          ) : null}
        </p>
      </div>
    );
  }
  return (
    <div
      className={cn(
        "my-1 rounded-[var(--radius-m)] border px-2.5 py-2",
        tone === "fail" ? "border-fail bg-fail-soft" : "border-warn bg-warn-soft",
      )}
    >
      <div className="flex items-center gap-2">
        <AlertTriangle
          aria-hidden="true"
          className={cn("size-4 shrink-0", tone === "fail" ? "text-fail" : "text-warn")}
        />
        <span className="text-[13px] font-semibold text-ink">
          {readRuptureHeading(link.verdict)}
        </span>
        {link.verdict === "broken" ? (
          <span className="text-[11px] text-ink-3">
            name match {link.identityScore}/100
          </span>
        ) : null}
      </div>
      <p className="mt-1 text-[12px] text-ink-2">
        {link.notes.length > 0 ? link.notes.join(" ") : RUPTURE_FALLBACK}
      </p>
      {link.verdict === "broken" ? (
        <PartyMismatch link={link} fromDeed={fromDeed} toDeed={toDeed} />
      ) : null}
      <LinkEvidence link={link} />
    </div>
  );
}

/**
 * What was actually asked of this hand-over. Only the questions the deeds could
 * answer arrive, so an absent question is never shown as a failed one.
 */
function LinkEvidence({ link }: { link: ChainLink }) {
  const asked = Object.entries(link.checks);
  if (asked.length === 0) {
    return null;
  }
  return (
    <ul
      aria-label="What was checked"
      className="mt-1.5 flex flex-wrap gap-x-3 gap-y-0.5 text-[11px]"
    >
      {asked.map(([name, agreed]) => (
        <li
          key={name}
          className={cn(
            "flex items-center gap-1",
            agreed === true ? "text-ink-3" : "text-fail",
          )}
        >
          {agreed === true ? (
            <CheckIcon aria-hidden="true" className="size-3 shrink-0" />
          ) : (
            <X aria-hidden="true" className="size-3 shrink-0" />
          )}
          {readLinkCheckQuestion(name)}
        </li>
      ))}
    </ul>
  );
}

/**
 * Why a break is a break: the person who bought in the earlier deed set against
 * the person who sold in the later one. Naming both is what turns "broken" from a
 * verdict the officer has to take on trust into one they can see for themselves.
 */
function PartyMismatch({
  link,
  fromDeed,
  toDeed,
}: {
  link: ChainLink;
  fromDeed: TimelineDeed;
  toDeed: TimelineDeed;
}) {
  const boughtBy = readPartyNames(fromDeed.record.buyers);
  const soldBy = readPartyNames(toDeed.record.sellers);
  return (
    <div className="mt-1.5 flex flex-col gap-0.5 text-[11px] text-ink-2">
      <span>
        Buyer in {link.fromDocNo ?? `Deed ${fromDeed.ordinal}`}:{" "}
        <span className="font-semibold text-ink">{boughtBy.text}</span>
      </span>
      <span>
        Seller in {link.toDocNo ?? `Deed ${toDeed.ordinal}`}:{" "}
        <span className="font-semibold text-ink">{soldBy.text}</span>
      </span>
      <span className="flex items-center gap-1 font-semibold text-fail">
        <X aria-hidden="true" className="size-3 shrink-0" />
        {SAME_PERSON_LINE}
      </span>
    </div>
  );
}

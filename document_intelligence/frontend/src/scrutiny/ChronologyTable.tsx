import type { ChainOfTitle, DocumentState } from "@/api/contracts";
import { StatusBadge } from "@/components/ui/statusBadge";
import {
  ORIGIN_LABEL,
  readJoinLabel,
  readLinkVerdictTone,
  readRuptureHeading,
} from "./chainVocabulary";
import { readPartyNames } from "./documentDisplay";
import { readTimelineDeeds } from "./OwnershipTimeline";

const NOTHING_RECORDED = "—";

interface ChronologyTableProps {
  chain: ChainOfTitle;
  documentsById: Record<string, DocumentState>;
}

/**
 * The same chain as a ledger: one row per transaction in date order, with the
 * specifics an officer would otherwise have to open each deed to compare —
 * property, value, and whether title carried over into that row.
 *
 * The timeline above answers "does it hold"; this answers "what exactly happened",
 * which is the form a scrutiny note is written from.
 */
export function ChronologyTable({ chain, documentsById }: ChronologyTableProps) {
  const deeds = readTimelineDeeds(chain, documentsById);
  if (deeds.length === 0) {
    return null;
  }
  return (
    <div>
      <h4 className="text-[13px] font-semibold text-ink">Chronology of activity</h4>
      <div className="mt-1.5 overflow-x-auto">
        <table className="w-full border-collapse text-left text-[12px]">
          <caption className="sr-only">
            Every registered transaction in date order, with the property conveyed,
            the value, and whether title carried over.
          </caption>
          <thead>
            <tr className="border-b border-line text-[11px] uppercase text-ink-3">
              <Th>#</Th>
              <Th>Date</Th>
              <Th>Activity</Th>
              <Th>From → To</Th>
              <Th>Property</Th>
              <Th>Value</Th>
              <Th>Continuity</Th>
            </tr>
          </thead>
          <tbody>
            {deeds.map((deed, index) => {
              // Row one begins the chain, so nothing handed over into it. Every
              // later row is reached through the link that precedes it.
              const link = index === 0 ? null : (chain.links[index - 1] ?? null);
              const sellers = readPartyNames(deed.record.sellers);
              const buyers = readPartyNames(deed.record.buyers);
              const property = [
                deed.record.property.surveyNo
                  ? `Sy. ${deed.record.property.surveyNo}`
                  : null,
                deed.record.property.plotNo
                  ? `Plot ${deed.record.property.plotNo}`
                  : null,
              ]
                .filter((part): part is string => part !== null)
                .join(" ");
              return (
                <tr key={deed.documentId} className="border-b border-line align-top">
                  <Td>{deed.ordinal}</Td>
                  <Td>
                    {deed.record.registrationDate ??
                      deed.record.executionDate ??
                      NOTHING_RECORDED}
                  </Td>
                  <Td>
                    <span className="text-ink">
                      {deed.record.deedType ?? NOTHING_RECORDED}
                    </span>
                    {deed.record.docNo ? (
                      <span className="block font-mono text-[11px] text-ink-3">
                        {deed.record.docNo}
                      </span>
                    ) : null}
                  </Td>
                  <Td>
                    {sellers.text}
                    {sellers.othersCount > 0 ? ` & ${sellers.othersCount} more` : ""}
                    <span aria-hidden="true" className="text-ink-3">
                      {" → "}
                    </span>
                    {buyers.text}
                    {buyers.othersCount > 0 ? ` & ${buyers.othersCount} more` : ""}
                  </Td>
                  <Td>
                    {property.length > 0 ? property : NOTHING_RECORDED}
                    <span className="block text-[11px] text-ink-3">
                      {deed.record.property.extentText ?? NOTHING_RECORDED}
                    </span>
                  </Td>
                  <Td>{deed.record.considerationText ?? NOTHING_RECORDED}</Td>
                  <Td>
                    {link === null ? (
                      <StatusBadge tone="neutral">{ORIGIN_LABEL}</StatusBadge>
                    ) : (
                      <StatusBadge tone={readLinkVerdictTone(link.verdict)}>
                        {readContinuity(link.verdict)}
                      </StatusBadge>
                    )}
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/**
 * A cell has room for a few words, so a rupture is named by what it is rather
 * than by the sentence the timeline uses.
 */
function readContinuity(verdict: string): string {
  const rupture = readRuptureHeading(verdict);
  if (rupture === null) {
    return readJoinLabel(verdict);
  }
  return verdict === "broken" ? "broken" : "gap";
}

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th scope="col" className="px-2 py-1.5 font-semibold">
      {children}
    </th>
  );
}

function Td({ children }: { children: React.ReactNode }) {
  return <td className="px-2 py-1.5 text-ink-2">{children}</td>;
}

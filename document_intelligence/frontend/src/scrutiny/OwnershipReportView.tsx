
import { FileText, KeyRound, Table2 } from "lucide-react";

import type {
  AttentionItem,
  AuthorityDocument,
  ChainFinding,
  DocumentRoleRow,
  DocumentState,
  JourneyEntry,
  OwnershipReport,
  ReportStats,
  RiskAssessment,
  TitleRole,
} from "@/api/contracts";
import { StatusBadge } from "@/components/ui/statusBadge";
import {
  readReportVerdictTone,
  readRiskTone,
  readSeverityTone,
} from "./chainVocabulary";
import { ChronologyTable } from "./ChronologyTable";
import { OwnershipTimeline } from "./OwnershipTimeline";

interface OwnershipReportViewProps {
  report: OwnershipReport;
  /** The read of each deed, which the timeline and ledger join the chain against. */
  documentsById: Record<string, DocumentState>;
}

/**
 * The chain of title, once every deed in a bundle has been read: who owns the
 * land now, how ownership reached them, and what a human still has to chase.
 *
 * Verdicts arrive as words; the tone (colour) and the icon are chosen here. The
 * risk score is shown but never drives the verdict — it summarises the signals, it
 * does not decide, so it sits to the side rather than at the top.
 *
 * A hand-off that failed is rendered as a block of its own, not as another row
 * wearing a different colour: whether ownership carried over is the question the
 * report exists to answer, and it has to be legible without reading every line.
 */
export function OwnershipReportView({
  report,
  documentsById,
}: OwnershipReportViewProps) {
  const verdictTone = readReportVerdictTone(report.verdict.level);
  return (
    <section
      aria-label="Chain of title"
      className="flex flex-col gap-3 rounded-[var(--radius-l)] border border-line bg-surface p-3"
    >
      <div className="flex flex-wrap items-start gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <StatusBadge tone={verdictTone}>{report.verdict.headline}</StatusBadge>
          </div>
          <p className="mt-1.5 text-[13px] text-ink-2">{report.verdict.plain}</p>
        </div>
        {report.risk !== null ? <RiskChip risk={report.risk} /> : null}
      </div>

      <ChainStats stats={report.stats} />

      {report.attention.length > 0 ? (
        <ul role="list" className="flex flex-col gap-1.5">
          {report.attention.map((item, index) => (
            <AttentionRow key={`${item.title}-${index}`} item={item} />
          ))}
        </ul>
      ) : null}

      <CurrentOwner journey={report.journey} />

      <OwnershipTimeline chain={report.chain} documentsById={documentsById} />

      <ChronologyTable chain={report.chain} documentsById={documentsById} />

      <Findings findings={report.chain.findings} />

      <DocumentsByRole
        documentsByRole={report.documentsByRole}
        authority={report.authority}
      />
    </section>
  );
}

/**
 * Who owns the land now, in one line, above the history.
 *
 * The timeline below runs oldest-first, which is the right way to follow how title
 * travelled but buries the answer to the question actually being asked. So the
 * answer is stated first and the working shown after.
 */
function CurrentOwner({ journey }: { journey: JourneyEntry[] }) {
  const owner = journey.find((entry) => entry.kind === "owner" && entry.isCurrent);
  if (owner === undefined || owner.party === null) {
    return null;
  }
  return (
    <div className="flex flex-wrap items-center gap-2 text-[13px]">
      {owner.badge ? <StatusBadge tone="pass">{owner.badge}</StatusBadge> : null}
      <span className="font-semibold text-ink">{owner.party.name}</span>
      {owner.role ? <span className="text-ink-3">{owner.role}</span> : null}
      {owner.meta ? <span className="text-ink-3">· {owner.meta}</span> : null}
    </div>
  );
}

/**
 * What the engine concluded, graded. Distinct from the attention list above: that
 * says what to do next, this says what was found.
 */
function Findings({ findings }: { findings: ChainFinding[] }) {
  if (findings.length === 0) {
    return null;
  }
  return (
    <div>
      <h4 className="text-[13px] font-semibold text-ink">Findings</h4>
      <ul role="list" aria-label="Findings" className="mt-1.5 flex flex-col gap-1">
        {findings.map((finding, index) => (
          <li key={`${finding.title}-${index}`} className="text-[12px]">
            <div className="flex flex-wrap items-center gap-2">
              <StatusBadge tone={readSeverityTone(finding.severity)}>
                {finding.severity.toUpperCase()}
              </StatusBadge>
              <span className="font-semibold text-ink">{finding.title}</span>
            </div>
            <p className="mt-0.5 text-ink-2">{finding.detail}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ChainStats({ stats }: { stats: ReportStats }) {
  const span =
    stats.spanFrom !== null && stats.spanTo !== null
      ? `${stats.spanFrom} → ${stats.spanTo}`
      : null;
  return (
    <dl className="flex flex-wrap gap-x-5 gap-y-1 text-[12px]">
      <Stat label="Title deeds" value={String(stats.titleDeedCount)} />
      {span ? <Stat label="Span" value={span} /> : null}
      <Stat label="Need checking" value={String(stats.needReview)} />
      <Stat label="Breaks" value={String(stats.breaks)} />
    </dl>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline gap-1.5">
      <dt className="text-ink-3">{label}</dt>
      <dd className="font-semibold text-ink">{value}</dd>
    </div>
  );
}

function RiskChip({ risk }: { risk: RiskAssessment }) {
  return (
    <div className="flex flex-col items-end">
      <StatusBadge tone={readRiskTone(risk.level)}>
        Risk {risk.level} · {risk.score}
      </StatusBadge>
      <span className="mt-0.5 text-[11px] text-ink-3">
        {risk.signals.length === 0
          ? "nothing flagged"
          : `${risk.signals.length} signal${risk.signals.length === 1 ? "" : "s"}`}
      </span>
    </div>
  );
}

function AttentionRow({ item }: { item: AttentionItem }) {
  return (
    <li className="rounded-[var(--radius-m)] bg-warn-soft px-2.5 py-2 text-[13px]">
      <div className="flex items-center gap-2">
        <StatusBadge tone={readSeverityTone(item.severity)}>{item.verb}</StatusBadge>
        <span className="font-semibold text-ink">{item.title}</span>
      </div>
      <p className="mt-1 text-ink-2">{item.detail}</p>
      <p className="mt-1 text-ink-2">{item.action}</p>
    </li>
  );
}
const ROLE_CAPTIONS: { role: TitleRole; title: string; note: string; icon: typeof FileText }[] =
  [
    {
      role: "title",
      title: "Title chain",
      note: "these conveyances carry ownership",
      icon: FileText,
    },
    {
      role: "authority",
      title: "Authority and supporting",
      note: "these do NOT convey title",
      icon: KeyRound,
    },
    { role: "metadata", title: "Metadata", note: "not a deed", icon: Table2 },
  ];

/**
 * Which documents actually carry ownership, and which only look as though they
 * do. A general power of attorney reads like a title document to anyone who has
 * not been told otherwise, so the distinction is captioned rather than implied.
 */
function DocumentsByRole({
  documentsByRole,
  authority,
}: {
  documentsByRole: Partial<Record<TitleRole, DocumentRoleRow[]>>;
  authority: AuthorityDocument[];
}) {
  const groups = ROLE_CAPTIONS.filter(
    ({ role }) => (documentsByRole[role]?.length ?? 0) > 0,
  );
  if (groups.length === 0) {
    return null;
  }
  return (
    <div className="flex flex-col gap-2">
      {authority.map((instrument) => (
        <AuthorityCallout key={instrument.documentId} instrument={instrument} />
      ))}
      <div className="flex flex-col gap-2">
        {groups.map(({ role, title, note, icon: Icon }) => (
          <div key={role}>
            <div className="flex items-center gap-1.5 text-[12px]">
              <Icon aria-hidden="true" className="size-3.5 text-ink-3" />
              <span className="font-semibold text-ink">{title}</span>
              <span className="text-ink-3">— {note}</span>
            </div>
            <ul
              aria-label={title}
              className="mt-0.5 flex flex-col gap-0.5 pl-5 text-[12px] text-ink-2"
            >
              {(documentsByRole[role] ?? []).map((row) => (
                <li key={row.documentId} className="flex flex-wrap gap-2">
                  <span>{row.deedType ?? "Deed"}</span>
                  {row.docNo ? (
                    <span className="font-mono text-ink-3">{row.docNo}</span>
                  ) : null}
                  {row.date ? <span className="text-ink-3">{row.date}</span> : null}
                  {row.isRoot ? (
                    <StatusBadge tone="neutral">root</StatusBadge>
                  ) : null}
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
}

function AuthorityCallout({ instrument }: { instrument: AuthorityDocument }) {
  return (
    <p className="rounded-[var(--radius-m)] bg-surface-3 px-2.5 py-2 text-[12px] text-ink-2">
      <span className="font-semibold text-ink">
        {instrument.deedType ?? "This instrument"} does not transfer ownership.
      </span>{" "}
      The land is owned by{" "}
      <span className="font-semibold text-ink">{instrument.owner}</span>;{" "}
      <span className="font-semibold text-ink">{instrument.holder}</span> only holds
      authority to act on the owner's behalf.
    </p>
  );
}

import type { DeedRecord, Party } from "@/api/contracts";

interface DeedRecordPanelProps {
  deedRecord: DeedRecord;
}

/**
 * What the deed conveys, read from the structured record the chain reasons over.
 * This is the deed as a transfer — who sold, who bought, what land, and the deeds
 * it says its title came through — rather than the flat field list on the Details
 * tab, which is where the officer corrects a misread value.
 */
export function DeedRecordPanel({ deedRecord }: DeedRecordPanelProps) {
  return (
    <div className="mt-3 flex flex-col gap-3 rounded-[var(--radius-m)] border border-line bg-canvas p-3">
      <div className="flex flex-wrap gap-x-6 gap-y-2">
        <PartyColumn label="Vendor" parties={deedRecord.sellers} />
        <PartyColumn label="Purchaser" parties={deedRecord.buyers} />
      </div>

      <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-[13px]">
        <Fact label="Document" value={deedRecord.docNo} />
        <Fact label="Registered" value={deedRecord.registrationDate} />
        <Fact label="Survey" value={deedRecord.property.surveyNo} />
        <Fact label="Plot" value={deedRecord.property.plotNo} />
        <Fact label="Extent" value={deedRecord.property.extentText} />
        <Fact label="Village" value={deedRecord.property.locality} />
        <Fact label="Consideration" value={deedRecord.considerationText} />
      </dl>

      {deedRecord.priorDeedRefs.length > 0 ? (
        <p className="text-[12px] text-ink-2">
          Traces title through{" "}
          <span className="font-mono text-ink">
            {deedRecord.priorDeedRefs.join(", ")}
          </span>
          .
        </p>
      ) : (
        <p className="text-[12px] text-ink-3">
          Cites no prior deed — the root of the chain in this bundle.
        </p>
      )}
    </div>
  );
}

function PartyColumn({ label, parties }: { label: string; parties: Party[] }) {
  const first = parties[0];
  return (
    <div className="min-w-0 flex-1">
      <span className="block text-[12px] text-ink-3">{label}</span>
      <span className="block truncate text-[13px] font-semibold text-ink">
        {first ? first.name : "Not read"}
      </span>
      {first?.relation && first.relativeName ? (
        <span className="block truncate text-[12px] text-ink-2">
          {first.relation} {first.relativeName}
        </span>
      ) : null}
      {parties.length > 1 ? (
        <span className="block text-[12px] text-ink-3">
          and {parties.length - 1} other{parties.length > 2 ? "s" : ""}
        </span>
      ) : null}
    </div>
  );
}

function Fact({ label, value }: { label: string; value: string | null }) {
  if (!value) {
    return null;
  }
  return (
    <div className="flex gap-2">
      <dt className="text-ink-3">{label}</dt>
      <dd className="min-w-0 truncate font-mono text-ink">{value}</dd>
    </div>
  );
}

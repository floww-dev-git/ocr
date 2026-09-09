import type { DocumentState } from "@/api/contracts";
import { StatusBadge } from "@/components/ui/statusBadge";
import { formatFileSize, readFieldLabel } from "./documentDisplay";

interface PreviewTabProps {
  document: DocumentState;
}

/** Identity documents the prototype draws as a card. */
const CARD_TYPES = new Set(["aadhaar", "pan", "dl"]);
/** Registered instruments the prototype draws as a stamped page. */
const DEED_TYPES = new Set(["sale_deed", "link_doc"]);

const CARD_TITLES: Record<string, [string, string]> = {
  aadhaar: ["Unique Identification Authority", "Aadhaar"],
  pan: ["Income Tax Department", "Permanent Account Number"],
  dl: ["Transport Department", "Driving licence"],
};

/** The wide identifier row each card ends with, and the rows above it. */
const CARD_LAYOUTS: Record<string, { rows: string[]; idKey: string; idLabel: string }> =
  {
    aadhaar: {
      rows: ["name", "dob", "gender"],
      idKey: "aadhaarNo",
      idLabel: "Aadhaar number",
    },
    pan: {
      rows: ["name", "parentName", "dob"],
      idKey: "pan",
      idLabel: "Permanent Account Number",
    },
    dl: {
      rows: ["name", "dob", "validUpto", "bloodGroup"],
      idKey: "dlNo",
      idLabel: "Licence number",
    },
  };

/**
 * What the document looks like, drawn from what was read off it.
 *
 * A scan is not always kept — in mock mode there is no image at all — so rather
 * than telling the officer there is nothing to see, the workspace redraws the
 * document from its own reading: the values in the places they sit on the paper.
 * Seeing "Kondapur Village, Serilingampally Mandal" printed in the village box is
 * how an officer notices the whole postal hierarchy was read into one field.
 *
 * A real page image, when one is held, is always preferred over the drawing.
 */
export function PreviewTab({ document }: PreviewTabProps) {
  return (
    <div className="preview flex flex-col gap-3">
      <dl className="grid grid-cols-2 gap-2 text-[13px]">
        <Fact label="File" value={document.filename} mono />
        <Fact label="Format" value={document.fileFormat} />
        <Fact label="Size" value={formatFileSize(document.fileSizeBytes)} />
        <Fact
          label="Pages"
          value={document.pageCount === 0 ? "Not read yet" : String(document.pageCount)}
        />
      </dl>

      <SecurityFeatures document={document} />

      <section>
        <h3 className="mb-1.5 text-[12px] font-semibold tracking-wide text-ink-3 uppercase">
          Document
        </h3>
        <Drawing document={document} />
      </section>
    </div>
  );
}

function Drawing({ document }: { document: DocumentState }) {
  // A held scan beats any redrawing of it.
  if (document.pageImageUrls.length > 0) {
    return (
      <ul role="list" className="flex flex-wrap gap-2">
        {document.pageImageUrls.map((url, index) => (
          <li key={url}>
            <img
              src={url}
              alt={`${document.filename}, page ${index + 1}`}
              className="pv-img"
            />
          </li>
        ))}
      </ul>
    );
  }
  const typeId = document.documentTypeId;
  if (typeId !== null && CARD_TYPES.has(typeId) && document.fieldValues.length > 0) {
    return <CardDrawing document={document} typeId={typeId} />;
  }
  if (typeId !== null && DEED_TYPES.has(typeId) && document.fieldValues.length > 0) {
    return <DeedDrawing document={document} typeId={typeId} />;
  }
  if (document.fieldValues.length > 0) {
    return <LetterDrawing document={document} />;
  }
  return <Placeholder document={document} />;
}

function CardDrawing({
  document,
  typeId,
}: {
  document: DocumentState;
  typeId: string;
}) {
  const [issuer, title] = CARD_TITLES[typeId] ?? ["Issuing authority", document.documentTypeLabel];
  const layout = CARD_LAYOUTS[typeId];
  const read = readValues(document);
  const rows = layout?.rows ?? document.fieldValues.map((field) => field.key);

  return (
    <div className={`pv-card pv-card-${typeId}`}>
      <div className="pv-band" />
      <div className="pv-card-head">
        <div className="pv-emblem" aria-hidden="true" />
        <div>
          <div className="pv-card-issuer">{issuer}</div>
          <div className="pv-card-title">{title}</div>
        </div>
      </div>

      <div className="pv-card-body">
        {isFound(document, "photo") ? (
          <div className="pv-photo" aria-hidden="true" />
        ) : null}
        <div className="pv-grid">
          {rows
            .filter((key) => read[key] !== undefined && key !== "address")
            .map((key) => (
              <Box key={key} fieldKey={key} value={read[key]} />
            ))}
          {layout !== undefined && read[layout.idKey] !== undefined ? (
            <div className="pv-row pv-row-wide">
              <span className="pv-label">{layout.idLabel}</span>
              <div className="pv-value pv-bigid" data-hl={layout.idKey}>
                {read[layout.idKey]}
              </div>
            </div>
          ) : null}
        </div>
      </div>

      {read.address !== undefined ? (
        <div className="pv-card-address">
          <span className="pv-label">{readFieldLabel("address")}</span>
          <span data-hl="address">{read.address}</span>
        </div>
      ) : null}

      <div className="pv-card-foot">
        {isFound(document, "qr") ? <div className="pv-qr" aria-hidden="true" /> : null}
        {isFound(document, "signature") ? (
          <div className="pv-signature-line">Signature</div>
        ) : null}
        {isFound(document, "hologram") ? (
          <div className="pv-hologram" aria-hidden="true" />
        ) : null}
      </div>
    </div>
  );
}

function DeedDrawing({
  document,
  typeId,
}: {
  document: DocumentState;
  typeId: string;
}) {
  const read = readValues(document);
  return (
    <div className="pv-page pv-deed">
      <div className="pv-stamp-strip">Non-judicial stamp paper</div>
      <h3 className="pv-title">
        {typeId === "link_doc" ? "LINK DOCUMENT" : "SALE DEED"}
      </h3>

      <div className="pv-ref-row">
        {read.docNo !== undefined ? (
          <div>
            <span className="pv-label">Document no.</span>
            <span className="id" data-hl="docNo">
              {read.docNo}
            </span>
          </div>
        ) : null}
        {read.sro !== undefined ? (
          <div>
            <span className="pv-label">Registered at</span>
            <span data-hl="sro">{read.sro}</span>
          </div>
        ) : null}
      </div>

      <p className="pv-para">
        This deed of sale is executed on <Value read={read} k="regDate" /> at{" "}
        <Value read={read} k="sro" /> by <Value read={read} k="vendor" /> (hereinafter
        the Vendor) in favour of <Value read={read} k="purchaser" /> (hereinafter the
        Purchaser).
      </p>

      {read.consideration !== undefined ? (
        <p className="pv-para">
          Whereas the Vendor is the absolute owner of the schedule property and has
          agreed to sell the same for a total consideration of{" "}
          <Value read={read} k="consideration" />, the receipt of which the Vendor
          hereby acknowledges, the Vendor conveys the schedule property to the
          Purchaser free from all encumbrances.
        </p>
      ) : (
        <p className="pv-para">
          Whereas the Vendor is the absolute owner of the schedule property, the
          Vendor hereby conveys the schedule property to the Purchaser free from all
          encumbrances.
        </p>
      )}

      <div className="pv-schedule">
        <div className="pv-schedule-title">Schedule of property</div>
        <p className="pv-para pv-para-tight">
          All that plot of land bearing plot no. <Value read={read} k="plotNo" /> in
          survey no. <Value read={read} k="surveyNo" /> admeasuring{" "}
          <Value read={read} k="extent" /> situated at <Value read={read} k="village" />{" "}
          village, within the registration sub-district of <Value read={read} k="sro" />.
        </p>
        {read.boundaries !== undefined ? (
          <p className="pv-para pv-para-tight">
            Bounded by: <Value read={read} k="boundaries" />
          </p>
        ) : null}
      </div>

      {isFound(document, "witnesses") ? (
        <div className="pv-witnesses">
          <div>Witness 1 ______________________</div>
          <div>Witness 2 ______________________</div>
        </div>
      ) : null}

      {isFound(document, "registration_endorsement") ||
      isFound(document, "registration") ? (
        <div className="pv-endorsement">
          <div className="pv-endorsement-title">Registered</div>
          <p className="pv-para pv-para-tight">
            Document no. <Value read={read} k="docNo" /> registered on{" "}
            <Value read={read} k="regDate" /> at <Value read={read} k="sro" />.
          </p>
          {isFound(document, "stamp_endorsement") || isFound(document, "stamp") ? (
            <div className="pv-endorsement-note">Stamp duty paid in full</div>
          ) : null}
        </div>
      ) : null}

      <div className="pv-footer">Page 1 of {Math.max(document.pageCount, 1)}</div>
    </div>
  );
}

/** Permits, NOCs, certificates and receipts: an official letter. */
function LetterDrawing({ document }: { document: DocumentState }) {
  const read = readValues(document);
  const reference = read.nocNo ?? read.docNo ?? null;
  return (
    <div className="pv-page pv-letter">
      <h3 className="pv-title">{document.documentTypeLabel.toUpperCase()}</h3>

      <div className="pv-ref-row">
        {read.issuedBy !== undefined ? (
          <div>
            <span className="pv-label">Issued by</span>
            <span data-hl="issuedBy">{read.issuedBy}</span>
          </div>
        ) : null}
        {reference !== null ? (
          <div>
            <span className="pv-label">Reference</span>
            <span className="id">{reference}</span>
          </div>
        ) : null}
        {read.issueDate !== undefined ? (
          <div>
            <span className="pv-label">Date</span>
            <span data-hl="issueDate">{read.issueDate}</span>
          </div>
        ) : null}
      </div>

      <dl className="pv-grid">
        {document.fieldValues
          .filter(
            (field) =>
              !["issuedBy", "issueDate", "nocNo", "docNo"].includes(field.key),
          )
          .map((field) => (
            <Box key={field.key} fieldKey={field.key} value={field.value} />
          ))}
      </dl>

      <div className="mt-3 flex justify-end">
        <div className="pv-seal-wrap">
          <div className={isFound(document, "seal") ? "pv-seal" : "pv-seal missing"}>
            {isFound(document, "seal") ? (
              <span className="pv-seal-text">Seal</span>
            ) : null}
          </div>
          {isFound(document, "seal") ? null : (
            <div className="pv-seal-caption">seal not detected</div>
          )}
        </div>
      </div>

      <div className="pv-footer">Page 1 of {Math.max(document.pageCount, 1)}</div>
    </div>
  );
}

function Placeholder({ document }: { document: DocumentState }) {
  return (
    <div className="pv-page pv-placeholder">
      <div className="pv-placeholder-icon" aria-hidden="true" />
      <div className="pv-placeholder-name">{document.filename}</div>
      <div className="pv-placeholder-meta">
        {document.fileFormat} · {formatFileSize(document.fileSizeBytes)}
      </div>
      <p className="pv-placeholder-meta max-w-[300px]">
        Nothing has been read off this document yet, and no page image is held for
        it.
      </p>
    </div>
  );
}

function Box({ fieldKey, value }: { fieldKey: string; value: string }) {
  return (
    <div className="pv-row">
      <span className="pv-label">{readFieldLabel(fieldKey)}</span>
      <div className="pv-value" data-hl={fieldKey}>
        {value}
      </div>
    </div>
  );
}

/** A read value inline in a sentence, marked so it can be traced to its field. */
function Value({ read, k }: { read: Record<string, string>; k: string }) {
  if (read[k] === undefined) {
    return <span className="text-ink-3">—</span>;
  }
  return <span data-hl={k}>{read[k]}</span>;
}

function SecurityFeatures({ document }: { document: DocumentState }) {
  const findings = Object.entries(document.structureFindings);
  return (
    <section>
      <h3 className="mb-1.5 text-[12px] font-semibold tracking-wide text-ink-3 uppercase">
        Security features
      </h3>
      {findings.length === 0 ? (
        <p className="text-[13px] text-ink-3">Not looked at yet.</p>
      ) : (
        <ul role="list" className="flex flex-wrap gap-1.5">
          {findings.map(([key, present]) => (
            <li key={key}>
              <StatusBadge tone={present ? "pass" : "warn"}>
                {present ? `${key} present` : `${key} not found`}
              </StatusBadge>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function Fact({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex flex-col">
      <dt className="text-[12px] text-ink-3">{label}</dt>
      <dd className={mono ? "font-mono break-all text-ink" : "text-ink"}>{value}</dd>
    </div>
  );
}

function readValues(document: DocumentState): Record<string, string> {
  const read: Record<string, string> = {};
  for (const field of document.fieldValues) {
    if (field.value !== "") {
      read[field.key] = field.value;
    }
  }
  return read;
}

/**
 * Whether the read positively found a template element. A finding that is absent
 * from the map was not applicable to this document, so it is not drawn either way.
 */
function isFound(document: DocumentState, key: string): boolean {
  return document.structureFindings[key] === true;
}

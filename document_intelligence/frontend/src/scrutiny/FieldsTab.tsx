import { Check as CheckIcon, Pencil, X } from "lucide-react";
import { useState } from "react";

import type { DocumentState, FieldValue } from "@/api/contracts";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { StatusBadge } from "@/components/ui/statusBadge";
import {
  formatConfidence,
  isLowConfidence,
  readFieldLabel,
} from "./documentDisplay";

interface FieldsTabProps {
  document: DocumentState;
  busy: boolean;
  onEditField: (fieldKey: string, value: string) => void;
  onConfirmFields: () => void;
}

export function FieldsTab({
  document,
  busy,
  onEditField,
  onConfirmFields,
}: FieldsTabProps) {
  if (document.fieldValues.length === 0) {
    return (
      <p className="text-[13px] text-ink-3">
        Nothing has been read from this document yet.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      <ul role="list" className="flex flex-col divide-y divide-line">
        {document.fieldValues.map((field) => (
          <FieldRow
            key={field.key}
            field={field}
            busy={busy}
            onSave={(value) => onEditField(field.key, value)}
          />
        ))}
      </ul>

      <div className="flex items-center gap-2 pt-1">
        <Button
          variant={document.confirmed ? "secondary" : "primary"}
          size="sm"
          onClick={onConfirmFields}
          disabled={busy || document.confirmed}
        >
          <CheckIcon />
          {document.confirmed ? "Signed off" : "These values are right"}
        </Button>
        {document.confirmed ? null : (
          <span className="text-[12px] text-ink-3">
            Sign off once you have checked the values against the original.
          </span>
        )}
      </div>
    </div>
  );
}

function FieldRow({
  field,
  busy,
  onSave,
}: {
  field: FieldValue;
  busy: boolean;
  onSave: (value: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(field.value);

  const beginEditing = () => {
    setDraft(field.value);
    setEditing(true);
  };

  const save = () => {
    setEditing(false);
    if (draft !== field.value) {
      onSave(draft);
    }
  };

  return (
    <li className="flex items-center gap-3 py-2">
      <span className="w-32 shrink-0 text-[12px] text-ink-3">
        {readFieldLabel(field.key)}
      </span>

      {editing ? (
        <>
          <Input
            autoFocus
            value={draft}
            aria-label={`${readFieldLabel(field.key)} value`}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") {
                save();
              }
              if (event.key === "Escape") {
                setEditing(false);
              }
            }}
            className="h-8 flex-1"
          />
          <Button variant="primary" size="sm" onClick={save} disabled={busy}>
            Save
          </Button>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setEditing(false)}
            aria-label="Cancel"
          >
            <X />
          </Button>
        </>
      ) : (
        <>
          <span className="flex-1 font-mono text-[13px] break-words text-ink">
            {field.value || <span className="text-ink-3">(cleared)</span>}
          </span>
          {field.edited ? (
            <StatusBadge tone="ai">Corrected</StatusBadge>
          ) : isLowConfidence(field) ? (
            <StatusBadge tone="warn">
              Read at {formatConfidence(field.confidence)}
            </StatusBadge>
          ) : null}
          <Button
            variant="ghost"
            size="icon"
            onClick={beginEditing}
            disabled={busy}
            aria-label={`Correct ${readFieldLabel(field.key)}`}
          >
            <Pencil />
          </Button>
        </>
      )}
    </li>
  );
}

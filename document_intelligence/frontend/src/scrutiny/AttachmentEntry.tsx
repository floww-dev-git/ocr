import { FileText } from "lucide-react";

import { readFileFormat } from "./stagedFiles";

interface AttachmentEntryProps {
  filenames: string[];
}

/**
 * What the officer put in, kept as its own record and distinct from what the
 * system made of it. Sits on the right, as the prototype puts the officer's own
 * entries.
 */
export function AttachmentEntryView({ filenames }: AttachmentEntryProps) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[80%] rounded-[var(--radius-l)] bg-user-bubble px-3 py-2.5">
        <p className="mb-1.5 text-[13px] text-ink-2">
          {filenames.length === 1
            ? "Verify this against the application"
            : "Verify these against the application"}
        </p>
        <ul role="list" className="flex flex-col gap-1">
          {filenames.map((filename, index) => (
            <li
              // Two files can legitimately share a name in one batch.
              key={`${filename}-${index}`}
              className="flex items-center gap-1.5 text-[13px]"
            >
              <FileText aria-hidden="true" className="size-4 shrink-0 text-ink-3" />
              <span className="truncate font-mono text-ink">{filename}</span>
              <span className="shrink-0 text-[12px] text-ink-3">
                {readFileFormat(filename)}
              </span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
